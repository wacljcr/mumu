#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publish_releases.py — 把每个插件「最新版」的 deb 上传成 GitHub Release 资源。

为什么需要它
------------
GitHub Pages 是纯静态托管，本身无法记录「某个 deb 被下载了几次」。但 GitHub
Releases 的每个资源（asset）有官方的 download_count —— 只要插件的下载链接指向
Release 资源，Sileo/Cydia 每次拉取都会被 GitHub 自动计数。

本脚本做的事：
  1. 扫描 debs/，按包名(Package)分组，取版本号最大的那(几)个 deb（多架构各一个）
  2. 为每个包创建/复用一个 Release（tag = 包名，标题 = 插件名）
  3. 把该包最新版的 deb 作为 asset 传上去（已存在且大小一致则跳过，避免重复上传）
  4. 写出 release_urls.json：{包名: 下载链接前缀}，供 gen_packages.py 改写 Filename
  5. 顺手拉一次 download_count，写出 downloads.json（首次初始化用）

用法（在仓库根目录）：
  GITHUB_TOKEN=xxx python3 tools/publish_releases.py

只在需要「首次建 Release / deb 有更新」时跑；日常计数刷新由 fetch_downloads.py 负责。
"""
import os
import sys
import json
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEBS_DIR = os.path.join(ROOT, 'debs')
RELEASE_URLS = os.path.join(ROOT, 'release_urls.json')
DOWNLOADS = os.path.join(ROOT, 'downloads.json')

REPO = os.environ.get('GITHUB_REPOSITORY', 'wacljcr/mumu')
API = f'https://api.github.com/repos/{REPO}'
TOKEN = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN', '')
# import gen_packages 里的版本比较 & deb 解析（已在仓库根）
sys.path.insert(0, ROOT)
import gen_packages as gp


def api_req(url, method='GET', data=None, headers=None, raw=False):
    """带 token 的 GitHub API 请求。返回解析后的 JSON（或 raw bytes）。"""
    h = {
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'repo-download-stats',
    }
    if TOKEN:
        h['Authorization'] = f'Bearer {TOKEN}'
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    with urllib.request.urlopen(req) as r:
        body = r.read()
    return body if raw else (json.loads(body) if body else None)


def ver_key(v):
    return gp.ver_key(v) if hasattr(gp, 'ver_key') else tuple(
        int(x) for x in __import__('re').findall(r'\d+', v.split('-')[0]))


def latest_per_pkg():
    """{包名: [该包最新版的 deb 文件名, ...]}（最新版本可能有多架构，全带上）"""
    groups = {}   # pkg -> {ver: [fn, ...]}
    for fn in sorted(os.listdir(DEBS_DIR)):
        if not fn.endswith('.deb'):
            continue
        path = os.path.join(DEBS_DIR, fn)
        try:
            _d, info = gp.get_deb_info(path)
        except Exception as e:
            print(f'  ! 解析失败 {fn}: {e}')
            continue
        pkg, ver = info.get('Package'), info.get('Version')
        if not pkg or not ver:
            continue
        groups.setdefault(pkg, {}).setdefault(ver, []).append(fn)
    latest = {}
    for pkg, vers in groups.items():
        top = max(vers.keys(), key=ver_key)
        latest[pkg] = sorted(vers[top])   # 该包最新版的全部 deb
    return latest


def get_or_create_release(pkg, title):
    """按 tag=pkg 找 Release，没有就建。返回 (release_json, existing_assets)"""
    try:
        rel = api_req(f'{API}/releases/tags/{pkg}')
        return rel, {a['name']: a for a in rel.get('assets', [])}
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
    # 不存在 → 创建
    body = json.dumps({
        'tag_name': pkg,
        'target_commitish': 'main',
        'name': title or pkg,
        'body': f'插件 {pkg} 的最新版安装包。下载次数由 GitHub 自动统计。',
        'draft': False,
        'prerelease': False,
    }).encode()
    rel = api_req(f'{API}/releases', method='POST', data=body,
                  headers={'Content-Type': 'application/json'})
    print(f'  + 创建 Release: {pkg}')
    return rel, {}


def upload_asset(upload_url, fn, path):
    """上传（或替换）一个 asset。upload_url 形如 .../assets{?name,label}"""
    url = upload_url.split('{')[0] + f'?name={fn}'
    data = open(path, 'rb').read()
    try:
        api_req(url, method='POST', data=data,
                headers={'Content-Type': 'application/octet-stream'})
        return True
    except urllib.error.HTTPError as e:
        # 422 = 已存在同名 asset → 删掉重传
        if e.code == 422:
            print(f'    · {fn} 已存在，跳过（如需更新请先删 Release 资源）')
            return False
        print(f'    ! 上传失败 {fn}: HTTP {e.code}')
        return False


def fetch_counts():
    """拉全部 Release 的 asset download_count，按 tag(=包名)汇总。"""
    counts = {}
    page = 1
    while True:
        rels = api_req(f'{API}/releases?per_page=100&page={page}')
        if not rels:
            break
        for r in rels:
            tag = r.get('tag_name')
            if not tag:
                continue
            total = sum(a.get('download_count', 0) for a in r.get('assets', []))
            counts[tag] = counts.get(tag, 0) + total
        if len(rels) < 100:
            break
        page += 1
    return counts


def main():
    if not TOKEN:
        print('! 缺少 GITHUB_TOKEN，无法调用 GitHub API。'
              '请在 CI 里用 secrets.GITHUB_TOKEN，或本地 export GITHUB_TOKEN=xxx')
        sys.exit(1)

    latest = latest_per_pkg()
    print(f'共 {len(latest)} 个插件，开始同步 Release 资源...\n')

    url_map = {}   # pkg -> 下载链接前缀（不含文件名）
    for pkg, files in sorted(latest.items()):
        # 插件显示名：取最新 deb 的 Name
        _d, info = gp.get_deb_info(os.path.join(DEBS_DIR, files[0]))
        title = info.get('Name') or pkg
        rel, _assets = get_or_create_release(pkg, title)
        upload = rel.get('upload_url')
        for fn in files:
            upload_asset(upload, fn, os.path.join(DEBS_DIR, fn))
        url_map[pkg] = f'https://github.com/{REPO}/releases/download/{pkg}'
        print(f'  · {pkg}  ←  {", ".join(files)}')

    with open(RELEASE_URLS, 'w', encoding='utf-8') as f:
        json.dump(url_map, f, ensure_ascii=False, indent=1)
    print(f'\n已写出 {os.path.basename(RELEASE_URLS)}（{len(url_map)} 个包）')

    # 首次顺便拉一次计数
    try:
        counts = fetch_counts()
        with open(DOWNLOADS, 'w', encoding='utf-8') as f:
            json.dump(counts, f, ensure_ascii=False, indent=1)
        print(f'已写出 {os.path.basename(DOWNLOADS)}')
    except Exception as e:
        print(f'  (计数拉取暂跳过: {e})')

    print('Done! 下一步：跑 gen_packages.py 让 Filename 指向 Release。')


if __name__ == '__main__':
    main()
