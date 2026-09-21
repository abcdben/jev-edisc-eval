#!/bin/bash
# Build the site and publish site/dist to github.com/abcdben/tarcalc (GitHub Pages -> tarcalc.com).
# Usage: scripts/deploy_site.sh            (re-export findings first if results changed: .venv/bin/bench export-findings)
set -euo pipefail
cd "$(dirname "$0")/../site"
npm run build
cd dist
echo "tarcalc.com" > CNAME
touch .nojekyll
rm -rf .git
git init -q -b main
git add -A
git -c user.name="deploy" -c user.email="deploy@tarcalc.com" commit -q -m "deploy $(date -u +%Y-%m-%dT%H:%MZ)"
git push -q -f https://github.com/abcdben/tarcalc.git main
rm -rf .git
echo "published: https://tarcalc.com  (also https://abcdben.github.io/tarcalc/)"
