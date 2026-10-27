# wacljcr 源

Cydia / Sileo 越狱源。

- 源地址（添加这个）：**https://wacljcr.github.io/mumu/**
- 网页首页：https://wacljcr.github.io/mumu/index.html

## 仓库结构

| 路径 | 作用 |
|---|---|
| `debs/` | 所有 deb 包（CI 会全部索引） |
| `icons/<包名>.png` | 源里显示的插件图标 |
| `changelogs/<包名>.md` | 版本历史 → Sileo 插件页「更新记录」tab |
| `descriptions/<包名>.md` | 详情正文 → Sileo 插件页「详情」tab（可选，手写排版） |
| `depictions/<包名>.json\|html` | 生成物，**不要手改** |
| `更新日记.md` | 全站总览，每个新版本加一条 |
| `gen_packages.py` | 生成 `Packages` / `Packages.gz` / `bz2` / `Release` |
| `gen_depictions.py` | 生成详情页（Sileo 原生 JSON + 网页 HTML） |
| `tools/push_via_api.py` | `git push` 不通时的推送通道 |

## 发一个版本

```bash
# 1) 放包
cp <包名>_<版本>_iphoneos-arm64.deb debs/

# 2) 写版本历史（新版本在最上面）
#    changelogs/<包名>.md        ← 「更新记录」tab
#    descriptions/<包名>.md      ← 「详情」tab（分段用独占一行的 ---）
# 3) 总览
#    更新日记.md 顶部加一条

# 4) 重新生成 + 提交
python3 gen_depictions.py && python3 gen_packages.py
git add -A && git commit -m "发布 <插件> <版本>"

# 5) 推送（github.com:443 不通时用 API 通道）
git push
# 或
REMOTE=$(~/bin/gh api repos/wacljcr/mumu/git/refs/heads/main --jq '.object.sha')
python3 tools/push_via_api.py "$REMOTE" "$(git rev-parse HEAD^)" "$(git rev-parse HEAD)" "$(git log -1 --format=%B)"
```

推完 CI（`.github/workflows/gen.yml`）会自动重建索引并部署 Pages，约 1 分钟。
**索引不要手改**，改 `debs/` `changelogs/` `descriptions/` `icons/` 就够了。

## 详细规范

发版细则、详情页排版规范、控制中心模块写法，见工作区文档：
`/Users/muzi/iOSDev/00-交接-新账号从这里开始.md`（第 5、6 节）
