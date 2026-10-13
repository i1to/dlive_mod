#!/usr/bin/env bash
# 在自己的终端运行：bash ~/dlive-mod/publish_repo.sh
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
repo_remote='git@github.com:i1to/dlive_mod.git'

git init -b main
root_branch=$(git symbolic-ref --short HEAD)
if [[ "$root_branch" != main ]]; then
    printf '当前根仓库分支为 %s，请先确认分支再上传。\n' "$root_branch" >&2
    exit 1
fi

# 保留子仓库历史；移出源码目录后，父仓库可收录全部文件。
backup_root=".git-backups/$(date +%Y%m%d-%H%M%S)-$$"
for project_dir in blive-vod blive-vod-fork DouyinLiveWebFetcher; do
    if [[ -e "$project_dir/.git" ]]; then
        mkdir -p -- "$backup_root"
        mv -- "$project_dir/.git" "$backup_root/$project_dir.git"
    fi
done

if git remote get-url origin >/dev/null 2>&1; then
    git remote set-url origin "$repo_remote"
else
    git remote add origin "$repo_remote"
fi

git add .
git diff --cached --stat
if ! git diff --cached --quiet; then
    git commit -m 'Import workspace with Douyin live song request integration'
fi
# 不强推；如果远端已有不同历史，Git 会拒绝，保留远端代码。
git push -u origin main
