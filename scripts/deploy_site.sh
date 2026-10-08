#!/bin/bash
# Build the site and publish site/dist to github.com/abcdben/tarcalc (GitHub Pages -> tarcalc.com).
# Usage: scripts/deploy_site.sh            (re-export findings first if results changed: .venv/bin/bench export-findings)
set -euo pipefail
cd "$(dirname "$0")/.."
scripts/publish_writeup.sh                # stage the contamination write-up + gallery under site/public/contamination/
cd site
npm run build
cd dist
echo "decider.tarcalc.com" > CNAME
touch .nojekyll
rm -rf .git
git init -q -b main
git add -A
git -c user.name="deploy" -c user.email="deploy@tarcalc.com" commit -q -m "deploy $(date -u +%Y-%m-%dT%H:%MZ)"
git push -q -f https://github.com/abcdben/tarcalc.git main
rm -rf .git
echo "published: https://decider.tarcalc.com  (also https://abcdben.github.io/tarcalc/)"
