#!/bin/bash
# Povuče podatke s Wolta i pusha ih na GitHub. Pokreće ga launchd (vidi install-mac.sh) ili ti ručno.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== $(date '+%Y-%m-%d %H:%M:%S') ==="
git pull --rebase --quiet
/usr/bin/python3 scraper/build.py

git add docs/data
if git diff --cached --quiet; then
  echo "Nema promjena."
else
  git commit --quiet -m "Podaci $(date '+%Y-%m-%d %H:%M')"
  git push --quiet
  echo "Pushano."
fi
