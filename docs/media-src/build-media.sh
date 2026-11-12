#!/usr/bin/env bash
# Regenerate every image in docs/ and agensi/media/screenshot-*.png from this repository's real output.
# Needs on PATH: skillcheck (pip install -e .), python3 with Pillow, node with playwright (NODE_PATH can
# point at it), ffmpeg. Nothing is typed by hand: the clip runs the real validator and the grid is read
# from the real SKILL.md files.
set -euo pipefail
cd "$(dirname "$0")/../.."
src=docs/media-src
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# 1. The validator clip (gif and mp4).
python3 $src/record.py $src/validator.spec.json "$tmp/validator.cast.json"
node $src/termcast.mjs "$tmp/validator.cast.json" docs/demo.gif docs/demo.mp4

# 2. The skill grid, read from the SKILL.md frontmatter.
python3 $src/grid.py "$tmp/grid.html"
node $src/shot.mjs "$tmp/grid.html" "$tmp/grid.png" 1100 0 2
python3 $src/squash.py "$tmp/grid.png" docs/skills-grid.png 128

# 3. The worked example, trimmed to four sections.
node $src/md_shot.mjs agensi/engineering-workflow-skills/examples/debug-from-evidence-worked-example.md \
  "$tmp/worked.png" "debug-from-evidence on a flaky test (trimmed)" \
  "Symptom,Hypotheses,Root cause,Fix and regression test"
python3 $src/squash.py "$tmp/worked.png" docs/worked-example.png 128

# 4. The GitHub social preview (upload it by hand in the repository settings).
node $src/shot.mjs $src/social.html "$tmp/social.png" 1280 640 1
python3 $src/squash.py "$tmp/social.png" docs/social-preview.png 200

# 5. The marketplace screenshots (logo.png is kept as it is). The pack sold there holds the skills and not
#    the validator, so the screenshots show the skills: the grid, a worked example, and one skill's own text.
cp docs/skills-grid.png agensi/media/screenshot-1.png
cp docs/worked-example.png agensi/media/screenshot-2.png
node $src/md_shot.mjs skills/debug-from-evidence/SKILL.md "$tmp/excerpt.png" \
  "skills/debug-from-evidence/SKILL.md (excerpt: Purpose, Exit criteria, When to stop and ask)" \
  "Purpose,Exit criteria,When to stop and ask"
python3 $src/squash.py "$tmp/excerpt.png" agensi/media/screenshot-3.png 128
