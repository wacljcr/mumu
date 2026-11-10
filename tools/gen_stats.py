#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_stats.py — 生成下载量汇总页 stats.html。

读 downloads.json（{包名: 下载次数}，由 tools/fetch_downloads.py 产出），
插件显示名从 debs/ 的 control 里取，按下载量从高到低排，生成一个单文件网页。
浏览器打开就能看到「哪个插件被下了多少次」，也可挂在源首页当排行榜。

用法：python3 tools/gen_stats.py
"""
import os
import sys
import json
import html

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import gen_packages as gp

DEBS_DIR = os.path.join(ROOT, 'debs')
DOWNLOADS = os.path.join(ROOT, 'downloads.json')
OUT = os.path.join(ROOT, 'stats.html')
REPO_URL = 'https://github.com/wacljcr/mumu'


def plugin_names():
    """{包名: 显示名} —— 取每个包最新版 deb 的 Name。"""
    best = {}
    for fn in os.listdir(DEBS_DIR):
        if not fn.endswith('.deb'):
            continue
        try:
            _d, info = gp.get_deb_info(os.path.join(DEBS_DIR, fn))
        except Exception:
            continue
        pkg, ver = info.get('Package'), info.get('Version')
        if not pkg or not ver:
            continue
        if pkg not in best or gp.ver_key(ver) > gp.ver_key(best[pkg][0]):
            best[pkg] = (ver, info.get('Name') or pkg)
    return {pkg: name for pkg, (_v, name) in best.items()}


def tweak_packages():
    """只统计「你自己的 Tweaks 插件」，排除依赖组件和旧 Release。

    判定：debs/ 里 Section == 'Tweaks' 的包名集合。
    这样 Frida / PreferenceLoader / ElleKit / libmagic1 这些「越狱后必备」的
    第三方底层组件，以及仓库里遗留的旧 Release（devenv-v1、rime 等），
    都不会混进插件排行。
    """
    pkgs = set()
    for fn in os.listdir(DEBS_DIR):
        if not fn.endswith('.deb'):
            continue
        try:
            _d, info = gp.get_deb_info(os.path.join(DEBS_DIR, fn))
        except Exception:
            continue
        pkg = info.get('Package')
        if pkg and info.get('Section') == 'Tweaks':
            pkgs.add(pkg)
    return pkgs


def main():
    if not os.path.exists(DOWNLOADS):
        # 缺数据不报错中止（CI 里 fetch 失败时不应卡住出包流程），只提示后跳过
        print('· 跳过 stats.html：没有 downloads.json（先跑 tools/fetch_downloads.py）')
        return
    with open(DOWNLOADS, encoding='utf-8') as f:
        counts = json.load(f)
    if not counts:
        print('· 跳过 stats.html：downloads.json 为空')
        return
    names = plugin_names()
    # 只保留 Tweaks 插件的计数，过滤掉依赖组件 + 非插件旧 Release
    tweaks = tweak_packages()
    counts = {p: c for p, c in counts.items() if p in tweaks}

    rows = sorted(counts.items(), key=lambda x: -x[1])
    total = sum(counts.values())
    maxc = rows[0][1] if rows else 0

    lis = []
    for i, (pkg, c) in enumerate(rows, 1):
        name = names.get(pkg, pkg)
        pct = (c / maxc * 100) if maxc else 0
        medal = {1: '🥇', 2: '🥈', 3: '🥉'}.get(i, f'{i}')
        lis.append(
            f'<li><span class="rk">{medal}</span>'
            f'<span class="nm">{html.escape(name)}</span>'
            f'<span class="bar"><i style="width:{pct:.1f}%"></i></span>'
            f'<span class="ct">{c:,}</span></li>'
        )

    doc = f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>下载排行 · 我爱吃辣椒炒肉</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font:15px/1.6 -apple-system,"PingFang SC",sans-serif;margin:0;
         padding:24px 18px 60px;background:#fff;color:#1c1c1e; }}
  .wrap {{ max-width:640px;margin:0 auto; }}
  h1 {{ font-size:22px;margin:0 0 4px; }}
  .sub {{ color:#8e8e93;font-size:13px;margin-bottom:20px; }}
  .cards {{ display:flex;gap:10px;margin-bottom:22px; }}
  .card {{ flex:1;background:rgba(120,120,128,.10);border-radius:12px;padding:12px; }}
  .card .n {{ font-size:22px;font-weight:700; }}
  .card .t {{ font-size:12px;color:#8e8e93; }}
  ol {{ list-style:none;margin:0;padding:0; }}
  li {{ display:flex;align-items:center;gap:10px;padding:8px 0;
       border-bottom:1px solid rgba(120,120,128,.18); }}
  .rk {{ width:28px;text-align:center;font-size:13px;color:#8e8e93;flex:none; }}
  .nm {{ flex:1;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap; }}
  .bar {{ width:110px;height:6px;background:rgba(120,120,128,.20);
         border-radius:3px;overflow:hidden;flex:none; }}
  .bar i {{ display:block;height:100%;background:#E8483F;border-radius:3px; }}
  .ct {{ width:58px;text-align:right;font-variant-numeric:tabular-nums;
        font-weight:600;flex:none; }}
  a {{ color:#E8483F; }}
  @media (prefers-color-scheme: dark) {{
    body {{ background:#000;color:#f2f2f7; }}
    .card {{ background:rgba(120,120,128,.18); }}
    li {{ border-bottom-color:rgba(120,120,128,.28); }}
  }}
</style></head><body><div class="wrap">
<h1>📥 下载排行</h1>
<div class="sub">我爱吃辣椒炒肉 · 数据来自 GitHub Releases，定时刷新</div>
<div class="cards">
  <div class="card"><div class="n">{total:,}</div><div class="t">总下载次数</div></div>
  <div class="card"><div class="n">{len(rows)}</div><div class="t">插件数量</div></div>
</div>
<ol>
{chr(10).join(lis)}
</ol>
<p style="margin-top:28px"><a href="{REPO_URL}">← 源仓库</a></p>
</div></body></html>
'''
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(doc)
    print(f'已生成 {os.path.basename(OUT)}：{len(rows)} 个插件，总下载 {total} 次')


if __name__ == '__main__':
    main()
