#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过 GitHub REST Git Data API 把本地 mumu-repo 的一次提交推上去。

背景：本机 github.com:443 直连超时（git push 不通），但 api.github.com 正常，
      gh token 具备 repo scope。于是用 API 重放一次 commit：
      blobs → tree(base_tree) → commit → 更新 ref。
安全：最后一步 PATCH ref 之前，远端完全不受影响。

用法：
  push_via_api.py <remote_base_sha> <diff_from> <diff_to> "<message>"
    remote_base_sha  远端当前 head（作为 parent + base_tree）
    diff_from/to     本地取哪一段差异（通常是 base..HEAD）
"""
import base64
import json
import os
import subprocess
import sys
import urllib.request

REPO = "wacljcr/mumu"
BRANCH = "main"
REPO_DIR = os.path.expanduser("~/mumu-repo")
GH = os.path.expanduser("~/bin/gh")

TOKEN = subprocess.check_output([GH, "auth", "token"]).decode().strip()
REMOTE_BASE, DIFF_FROM, DIFF_TO, MESSAGE = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]


def api(path, method="GET", data=None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        "https://api.github.com" + path, method=method, data=body,
        headers={
            "Authorization": "token " + TOKEN,
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "mumu-publish",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read()
        return json.loads(raw) if raw else {}


def git(*args):
    return subprocess.check_output(["git", "-C", REPO_DIR, "-c", "core.quotepath=false"] + list(args)).decode()


print("远端 base:", REMOTE_BASE[:12])
base_commit = api("/repos/%s/git/commits/%s" % (REPO, REMOTE_BASE))
base_tree = base_commit["tree"]["sha"]
print("远端 base tree:", base_tree[:12])

raw = git("diff", "--name-status", DIFF_FROM, DIFF_TO).splitlines()
entries, stats = [], {"add": 0, "mod": 0, "del": 0}
for line in raw:
    if not line.strip():
        continue
    parts = line.split("\t")
    st = parts[0]
    if st.startswith("R"):
        entries.append(("D", parts[1])); stats["del"] += 1
        entries.append(("A", parts[2])); stats["add"] += 1
    elif st == "A":
        entries.append(("A", parts[1])); stats["add"] += 1
    elif st == "M":
        entries.append(("M", parts[1])); stats["mod"] += 1
    elif st == "D":
        entries.append(("D", parts[1])); stats["del"] += 1

print("变更：新增 %(add)d / 修改 %(mod)d / 删除 %(del)d" % stats)

tree = []
for i, (st, path) in enumerate(entries, 1):
    if st == "D":
        tree.append({"path": path, "mode": "100644", "type": "blob", "sha": None})
        continue
    full = os.path.join(REPO_DIR, path)
    with open(full, "rb") as f:
        content = base64.b64encode(f.read()).decode()
    blob = api("/repos/%s/git/blobs" % REPO, "POST", {"content": content, "encoding": "base64"})
    mode = "100644"
    ls = git("ls-files", "-s", "--", path).strip()
    if ls and ls.split()[0] in ("100755", "100644"):
        mode = ls.split()[0]
    tree.append({"path": path, "mode": mode, "type": "blob", "sha": blob["sha"]})
    print("  [%d/%d] %s %s" % (i, len(entries), st, path))

new_tree = api("/repos/%s/git/trees" % REPO, "POST", {"base_tree": base_tree, "tree": tree})
print("new tree:", new_tree["sha"][:12])

new_commit = api("/repos/%s/git/commits" % REPO, "POST",
                 {"message": MESSAGE, "tree": new_tree["sha"], "parents": [REMOTE_BASE]})
print("new commit:", new_commit["sha"][:12])

api("/repos/%s/git/refs/heads/%s" % (REPO, BRANCH), "PATCH",
    {"sha": new_commit["sha"], "force": False})
print("已更新 %s -> %s" % (BRANCH, new_commit["sha"][:12]))
