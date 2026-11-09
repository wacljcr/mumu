#!/usr/bin/env bash
# 通过 GitHub REST Git Data API 用 gh 重放一次本地提交（本机 python urllib SSL 栈有问题，改用 gh api）。
# 用法: push_via_gh.sh <remote_base_sha> <diff_from> <diff_to> "<message>"
set -euo pipefail

REPO="wacljcr/mumu"
BRANCH="main"
REPO_DIR="$HOME/mumu-repo"

REMOTE_BASE="$1"; DIFF_FROM="$2"; DIFF_TO="$3"; MESSAGE="$4"

echo "远端 base: ${REMOTE_BASE:0:12}"
BASE_TREE=$(gh api "repos/$REPO/git/commits/$REMOTE_BASE" --jq '.tree.sha')
echo "远端 base tree: ${BASE_TREE:0:12}"

# 读取变更列表（A/M/D），路径可能含中文，用 core.quotepath=false
LINES=()
while IFS= read -r line; do
  LINES+=("$line")
done < <(git -C "$REPO_DIR" -c core.quotepath=false diff --name-status "$DIFF_FROM" "$DIFF_TO")
declare -a ENTRIES=()   # 每项 "STATUS<TAB>PATH"
for line in "${LINES[@]}"; do
  [ -z "$line" ] && continue
  st="${line%%$'\t'*}"
  rest="${line#*$'\t'}"
  if [[ "$st" == R* ]]; then
    old="${rest%%$'\t'*}"; new="${rest#*$'\t'}"
    ENTRIES+=("D	$old"); ENTRIES+=("A	$new")
  elif [[ "$st" == "A" || "$st" == "M" || "$st" == "D" ]]; then
    ENTRIES+=("$st	$rest")
  fi
done

ADD=0; MOD=0; DEL=0
for e in "${ENTRIES[@]}"; do
  case "${e%%$'\t'*}" in A) ((ADD++));; M) ((MOD++));; D) ((DEL++));; esac
done
echo "变更：新增 $ADD / 修改 $MOD / 删除 $DEL"

# 构造 tree 数组（JSON 逐条写入临时文件）
TMP=$(mktemp)
echo '[' > "$TMP"
first=1
for e in "${ENTRIES[@]}"; do
  st="${e%%$'\t'*}"; path="${e#*$'\t'}"
  if [[ "$st" == "D" ]]; then
    [ $first -eq 0 ] && echo ',' >> "$TMP"
    printf '{"path":%s,"mode":"100644","type":"blob","sha":null}' "$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$path")" >> "$TMP"
    first=0
    continue
  fi
  full="$REPO_DIR/$path"
  b64=$(base64 < "$full" | tr -d '\n')
  blob_sha=$(gh api "repos/$REPO/git/blobs" -X POST --input - <<< "{\"content\":\"$b64\",\"encoding\":\"base64\"}" --jq '.sha')
  mode="100644"
  ls_out=$(git -C "$REPO_DIR" ls-files -s -- "$path" | head -1)
  if [[ -n "$ls_out" ]]; then
    m=$(echo "$ls_out" | awk '{print $1}')
    [[ "$m" == "100755" || "$m" == "100644" ]] && mode="$m"
  fi
  [ $first -eq 0 ] && echo ',' >> "$TMP"
  printf '{"path":%s,"mode":"%s","type":"blob","sha":"%s"}' "$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$path")" "$mode" "$blob_sha" >> "$TMP"
  first=0
  echo "  [$st] $path"
done
echo ']' >> "$TMP"

# 创建 tree（base_tree = 远端当前 tree）
TREE_JSON=$(python3 -c 'import json,sys;print(json.dumps({"base_tree":sys.argv[1],"tree":json.load(open(sys.argv[2]))}))' "$BASE_TREE" "$TMP")
NEW_TREE=$(gh api "repos/$REPO/git/trees" -X POST --input - <<< "$TREE_JSON" --jq '.sha')
echo "new tree: ${NEW_TREE:0:12}"

# 创建 commit（parent = 远端 base）
COMMIT_JSON=$(python3 -c 'import json,sys;print(json.dumps({"message":sys.argv[1],"tree":sys.argv[2],"parents":[sys.argv[3]]}))' "$MESSAGE" "$NEW_TREE" "$REMOTE_BASE")
NEW_COMMIT=$(gh api "repos/$REPO/git/commits" -X POST --input - <<< "$COMMIT_JSON" --jq '.sha')
echo "new commit: ${NEW_COMMIT:0:12}"

# 更新 ref
gh api "repos/$REPO/git/refs/heads/$BRANCH" -X PATCH --input - <<< "{\"sha\":\"$NEW_COMMIT\",\"force\":false}" > /dev/null
echo "已更新 $BRANCH -> ${NEW_COMMIT:0:12}"
rm -f "$TMP"
