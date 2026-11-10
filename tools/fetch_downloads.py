#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_downloads.py — 从 GitHub API 拉每个插件的下载次数，写出 downloads.json。

配合 publish_releases.py 用：插件的 deb 已作为 Release 资源上传后，GitHub 会自动
统计每个资源的 download_count。本脚本按 tag(=包名) 汇总，生成：
  downloads.json  ——  {包名: 累计下载次数}

由 CI 定时（cron）跑，刷新后的数字会被 gen_depictions.py 写进每个插件的详情页，
Sileo 里点开插件就能看到「下载次数」。

用法：
  python3 tools/fetch_downloads.py                 # 匿名（限流 60 次/小时，包少够用）
  GITHUB_TOKEN=xxx python3 tools/fetch_downloads.py  # 带 token（5000 次/小时，推荐）
"""
import os
import sys
import json
import time
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOWNLOADS = os.path.join(ROOT, 'downloads.json')

REPO = os.environ.get('GITHUB_REPOSITORY', 'wacljcr/mumu')
API = f'https://api.github.com/repos/{REPO}'
TOKEN = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN', '')


def api_req(url):
    h = {
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'repo-download-stats',
    }
    if TOKEN:
        h['Authorization'] = f'Bearer {TOKEN}'
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read() or b'null')


def fetch_counts(retries=3):
    """分页拉全部 Release，按 tag 汇总 asset download_count。"""
    counts = {}
    page = 1
    while True:
        rels = None
        for attempt in range(retries):
            try:
                rels = api_req(f'{API}/releases?per_page=100&page={page}')
                break
            except urllib.error.HTTPError as e:
                if e.code == 403 and 'rate limit' in str(e).lower():
                    wait = 60 * (attempt + 1)
                    print(f'  ! 触发限流，等待 {wait}s 后重试...')
                    time.sleep(wait)
                elif e.code == 404:
                    print('  ! 没有任何 Release（先跑 publish_releases.py）')
                    return {}
                else:
                    print(f'  ! HTTP {e.code}，重试 {attempt+1}/{retries}')
                    time.sleep(5 * (attempt + 1))
            except Exception as e:
                print(f'  ! 网络错误 {e}，重试 {attempt+1}/{retries}')
                time.sleep(5 * (attempt + 1))
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
    print(f'拉取 {REPO} 的下载计数...')
    counts = fetch_counts()
    if not counts:
        print('! 未取到任何计数。确认已跑过 publish_releases.py 创建 Release。')
        sys.exit(1)

    # 保留旧数据里「本次没取到」的包（避免某个包临时拉不到就被清零）
    old = {}
    if os.path.exists(DOWNLOADS):
        try:
            old = json.load(open(DOWNLOADS, encoding='utf-8'))
        except Exception:
            old = {}
    for k, v in old.items():
        if k not in counts:
            counts[k] = v

    with open(DOWNLOADS, 'w', encoding='utf-8') as f:
        json.dump(counts, f, ensure_ascii=False, indent=1)

    total = sum(counts.values())
    print(f'已写出 downloads.json：{len(counts)} 个插件，总下载 {total} 次')
    # 按下载量排个序打出来，方便日志里一眼看到热门插件
    for pkg, c in sorted(counts.items(), key=lambda x: -x[1])[:15]:
        print(f'  {c:>6}  {pkg}')


if __name__ == '__main__':
    main()
