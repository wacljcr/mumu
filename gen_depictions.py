#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为每个插件生成「专属详情页」：Sileo 原生 depiction + 网页 depiction。

为什么要有这个脚本
------------------
以前更新记录只写在一个 `更新日记.md` 里，用户在 Sileo 里点开插件根本看不到，
必须回仓库翻文件。Sileo 的标准做法是给每个包一个 depiction：
  Packages 索引里加 `SileoDepiction: <json url>`（Sileo 原生，内嵌在详情页）
  以及 `Depiction: <html url>`（Cydia / Zebra / 旧版 Sileo 用）
这样「更新记录」就长在插件自己的详情页里，点开就能看到。

数据来源
--------
  changelogs/<Package>.md     该插件的更新记录（人工维护，新版本写在最上面）
  debs/<Package>_<Ver>.deb    取最新版的 Name / Description / Author / Firmware / 打包时间

产物
----
  depictions/<Package>.json   SileoDepiction（含「详情」「更新记录」两个 tab）
  depictions/<Package>.html   Depiction（网页版，给 Cydia / Zebra）

没写 changelogs/<Package>.md 的包不会生成 depiction，Sileo 里就还是用 control 的
Description —— 也就是说「没生成」不会让页面变丑，只是没有更新记录 tab。
"""
import os
import re
import json
import html
import time

import gen_packages as gp

HERE = os.path.dirname(os.path.abspath(__file__))
DEBS_DIR = os.path.join(HERE, 'debs')
CHANGELOG_DIR = os.path.join(HERE, 'changelogs')
OUT_DIR = os.path.join(HERE, 'depictions')
BASE = 'https://wacljcr.github.io/mumu'
TINT = '#E8483F'


def ver_key(v):
    """2.3.9 < 2.3.50 这类比较：把版本里的数字段抽出来当元组比。"""
    v = v.split('-')[0].split('+')[0]
    parts = [int(x) for x in re.findall(r'\d+', v)]
    return tuple(parts) if parts else (0,)


def latest_debs():
    """{Package: (Version, deb_path)} —— 每个包只留版本号最大的那个。"""
    best = {}
    if not os.path.isdir(DEBS_DIR):
        return best
    for fn in os.listdir(DEBS_DIR):
        if not fn.endswith('.deb'):
            continue
        path = os.path.join(DEBS_DIR, fn)
        try:
            _data, info = gp.get_deb_info(path)
        except Exception as e:
            print(f'  ! 解析失败 {fn}: {e}')
            continue
        pkg, ver = info.get('Package'), info.get('Version')
        if not pkg or not ver:
            continue
        if pkg not in best or ver_key(ver) > ver_key(best[pkg][0]):
            best[pkg] = (ver, path, info)
    return best


def clean_desc(desc):
    """control 里的 Description 是按行硬折行的（还被用 '.' 当段落分隔），
    直接照搬会在详情页里变成一堆碎段落。这里还原成正常 markdown：
      - 同一段内的续行直接拼接（中文不需要空格）
      - 单独的 '.' 视为段落分隔
      - '- ' 开头的行保持为列表项，连续的合成一个列表
    """
    if not desc:
        return ''
    blocks, cur = [], []
    first_line = True
    for line in desc.split('\n'):
        s = line.strip()
        if not s:
            continue
        if s == '.':
            if cur:
                blocks.append(''.join(cur))
                cur = []
            continue
        if s.startswith('- '):
            if cur:
                blocks.append(''.join(cur))
                cur = []
            blocks.append(s)
        else:
            cur.append(s)
            # 第一行在 control 里通常就是摘要，单独成段；
            # 以句末标点结尾的行也自然结束本段（否则会跟下一句粘成一行）
            if first_line or s.endswith(('。', '！', '？', '）', '》')):
                blocks.append(''.join(cur))
                cur = []
        first_line = False
    if cur:
        blocks.append(''.join(cur))

    out = ''
    for i, b in enumerate(blocks):
        if i:
            prev = blocks[i - 1]
            same_list = b.startswith('- ') and prev.startswith('- ')
            out += '\n' if same_list else '\n\n'
        out += b
    return out


def fw_text(fw):
    """'>= 14.0' → 'iOS 14.0 及以上'"""
    if not fw:
        return ''
    m = re.search(r'([\d.]+)', fw)
    return f'iOS {m.group(1)} 及以上' if m else fw


def build_json(name, desc, meta_md, changelog_md):
    details_views = []
    if desc:
        details_views.append({'class': 'DepictionMarkdownView', 'markdown': desc})
    details_views.append({'class': 'DepictionSeparatorView'})
    details_views.append({'class': 'DepictionSubheaderView', 'title': '版本信息'})
    details_views.append({'class': 'DepictionMarkdownView', 'markdown': meta_md})

    return {
        'class': 'DepictionTabView',
        'minVersion': '0.4',
        'tintColor': TINT,
        'tabs': [
            {
                'class': 'DepictionStackView',
                'tabname': '详情',
                'views': details_views,
            },
            {
                'class': 'DepictionStackView',
                'tabname': '更新记录',
                'views': [
                    {'class': 'DepictionMarkdownView', 'markdown': changelog_md},
                ],
            },
        ],
    }


def build_html(name, version, desc, meta_md, changelog_md):
    """给 Cydia / Zebra 的网页版。用最保守的内联样式，深色浅色都读得清。"""
    def md_to_html(md):
        out = []
        for block in md.split('\n'):
            s = block.rstrip()
            if not s.strip():
                continue
            if s.startswith('### '):
                out.append(f'<h3>{esc(s[4:])}</h3>')
            elif s.startswith('## '):
                out.append(f'<h2>{esc(s[3:])}</h2>')
            elif s.lstrip().startswith('- '):
                indent = ' style="margin-left:18px"' if s.startswith('  ') else ''
                out.append(f'<li{indent}>{inline(s.lstrip()[2:])}</li>')
            else:
                out.append(f'<p>{inline(s)}</p>')
        # 把连续的 li 包进 ul
        res, buf = [], []
        for x in out:
            if x.startswith('<li'):
                buf.append(x)
            else:
                if buf:
                    res.append('<ul>' + ''.join(buf) + '</ul>')
                    buf = []
                res.append(x)
        if buf:
            res.append('<ul>' + ''.join(buf) + '</ul>')
        return '\n'.join(res)

    def esc(t):
        return html.escape(t, quote=False)

    def inline(t):
        t = esc(t)
        t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
        t = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', t)
        return t

    return f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(name)}</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font: 15px/1.65 -apple-system,"PingFang SC",sans-serif; margin:0; padding:16px 18px 40px;
         background:#fff; color:#1c1c1e; }}
  h1 {{ font-size:22px; margin:0 0 4px; }}
  h2 {{ font-size:17px; margin:22px 0 8px; }}
  h3 {{ font-size:15px; margin:18px 0 6px; color:{TINT}; }}
  p {{ margin:6px 0; }}
  ul {{ margin:6px 0 6px 18px; padding:0; }}
  li {{ margin:4px 0; }}
  code {{ font-family:ui-monospace,Menlo,monospace; font-size:13px;
          background:rgba(120,120,128,.16); padding:1px 5px; border-radius:4px; }}
  hr {{ border:0; border-top:1px solid rgba(120,120,128,.25); margin:18px 0; }}
  .sub {{ color:#8e8e93; font-size:13px; }}
  @media (prefers-color-scheme: dark) {{
    body {{ background:#000; color:#f2f2f7; }}
    code {{ background:rgba(120,120,128,.32); }}
  }}
</style></head><body>
<h1>{esc(name)}</h1>
<div class="sub">v{esc(version)}</div>
{md_to_html(desc)}
<hr>
{md_to_html(meta_md)}
<hr>
<h2>更新记录</h2>
{md_to_html(changelog_md)}
</body></html>
'''


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(CHANGELOG_DIR, exist_ok=True)
    best = latest_debs()
    made = []
    for pkg, (ver, path, info) in sorted(best.items()):
        md_path = os.path.join(CHANGELOG_DIR, pkg + '.md')
        if not os.path.exists(md_path):
            continue
        with open(md_path, encoding='utf-8') as f:
            changelog_md = f.read().strip()
        if not changelog_md:
            continue

        name = info.get('Name') or pkg
        desc = clean_desc(info.get('Description', ''))
        meta_lines = [f'- 当前版本：**{ver}**',
                      f'- 更新日期：{time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(path)))}']
        fw = fw_text(info.get('Firmware', ''))
        if fw:
            meta_lines.append(f'- 支持系统：{fw}')
        author = info.get('Author') or info.get('Maintainer')
        if author:
            meta_lines.append(f'- 开发者：{author}')
        meta_md = '\n'.join(meta_lines)

        data = build_json(name, desc, meta_md, changelog_md)
        with open(os.path.join(OUT_DIR, pkg + '.json'), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=1)

        # 网页版（Cydia / Zebra / 旧版 Sileo）
        with open(os.path.join(OUT_DIR, pkg + '.html'), 'w', encoding='utf-8') as f:
            f.write(build_html(name, ver, desc, meta_md, changelog_md))
        made.append(f'{pkg}  v{ver}')

    print(f'生成 {len(made)} 个插件的详情页：')
    for m in made:
        print('  ' + m)
    if not made:
        print('  （没有 changelogs/*.md，跳过）')


if __name__ == '__main__':
    main()
