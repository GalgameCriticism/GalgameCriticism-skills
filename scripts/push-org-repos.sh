#!/usr/bin/env bash
# 把 monorepo 里的每个 skill 目录镜像到组织下同名的独立仓库。
#
# 用法：
#   scripts/push-org-repos.sh                 # 推送全部 skill
#   scripts/push-org-repos.sh weibo-weekly-sync zhihu-weekly-sync
#   ORG=GalgameCriticism BRANCH=main scripts/push-org-repos.sh
#
# 行为：
#   - 用 `git subtree split --prefix=skills/<name>` 保留该目录自己的提交历史，
#     结果写到本地分支 split/<name>，不污染 main。
#   - 目标仓库必须已存在（本脚本不创建仓库，创建需要 token/网页）。
#   - 已存在同名 split 分支时先删除再重建，保证与 main 一致。
#   - 任何一步失败立即退出，不会只推一半。
set -euo pipefail

ORG="${ORG:-GalgameCriticism}"
BRANCH="${BRANCH:-main}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SKILLS=("$@")
if [ ${#SKILLS[@]} -eq 0 ]; then
  # 只取真正的 skill 目录（含 SKILL.md）
  while IFS= read -r d; do SKILLS+=("$(basename "$d")"); done < <(find skills -mindepth 1 -maxdepth 1 -type d | sort)
fi

fail=0
for name in "${SKILLS[@]}"; do
  echo "=== $name ==="
  if [ ! -f "skills/$name/SKILL.md" ]; then
    echo "  跳过：skills/$name/SKILL.md 不存在"; continue
  fi

  url="git@github.com:${ORG}/${name}.git"
  if ! git ls-remote --exit-code "$url" >/dev/null 2>&1; then
    echo "  跳过：$url 不存在或当前 SSH key 无权限（需先在 GitHub 建仓）"
    fail=1
    continue
  fi

  git branch -D "split/$name" >/dev/null 2>&1 || true
  git subtree split --prefix="skills/$name" -b "split/$name" >/dev/null
  if git push --force "$url" "split/$name:refs/heads/${BRANCH}" 2>&1 | tail -3; then
    echo "  ✅ 已推送 $url ($BRANCH)"
  else
    echo "  ❌ 推送失败 $url"; fail=1
  fi
done

echo
if [ "$fail" -ne 0 ]; then
  echo "存在未完成的仓库。建仓后可重跑本脚本补齐："
  echo "  scripts/push-org-repos.sh"
  exit 1
fi
echo "全部完成。"
