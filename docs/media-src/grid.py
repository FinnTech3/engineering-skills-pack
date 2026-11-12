#!/usr/bin/env python3
"""Write an HTML grid: one card per skill, with trigger phrases quoted from its real frontmatter.

Usage: python3 docs/media-src/grid.py OUT.html
Then:  node docs/media-src/shot.mjs OUT.html docs/skills-grid.png 1100 0 2

Nothing here is typed by hand except the stage colours. Skill names and trigger phrases come
from each skills/<name>/SKILL.md (parsed with this repository's own frontmatter parser).
The stage of each skill comes from the table in README.md.
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from skillcheck.rules import RULES  # noqa: E402
from skillcheck.skill import load_all  # noqa: E402

STAGE_COLOURS = {
    "Define": "#818cf8",
    "Plan": "#a78bfa",
    "Build": "#60a5fa",
    "Verify": "#2dd4bf",
    "Review": "#fbbf24",
    "Ship": "#4ade80",
    "Operate": "#fb7185",
    "Any stage": "#94a3b8",
}
MAX_PHRASE_CHARS = 78  # trigger phrases shown per card: whole phrases only, never cut in the middle


def stages_from_readme() -> dict[str, str]:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| ([A-Za-z ]+?) \| \[`([a-z0-9-]+)`\]\(", text, re.M)
    return {name: stage for stage, name in rows}


def trigger_phrases(description: str) -> list[str]:
    """Quoted phrases from the 'Use when ...' sentence, in order, as many as fit."""
    use_sentence = description.split("Do not use")[0]
    phrases = re.findall(r'"([^"]+)"', use_sentence)
    chosen: list[str] = []
    for phrase in phrases:
        if len(chosen) == 3 or sum(len(p) for p in [*chosen, phrase]) > MAX_PHRASE_CHARS:
            break
        chosen.append(phrase)
    return chosen


def card(name: str, stage: str, phrases: list[str]) -> str:
    colour = STAGE_COLOURS[stage]
    lines = "".join(f"<li>&ldquo;{html.escape(p)}&rdquo;</li>" for p in phrases)
    return (
        f'<div class="card" style="--c:{colour}"><div class="chip">{html.escape(stage)}</div>'
        f'<div class="name">{html.escape(name)}</div><ul>{lines}</ul></div>'
    )


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    skills = load_all(ROOT / "skills")
    stages = stages_from_readme()
    missing = {s.name for s in skills} - set(stages)
    if missing:
        raise SystemExit(f"README.md has no stage for: {sorted(missing)}")
    order = list(STAGE_COLOURS)
    skills.sort(key=lambda s: (order.index(stages[s.name]), s.name))
    cards = [card(s.name, stages[s.name], trigger_phrases(s.description)) for s in skills]
    cards.append(
        '<div class="card tool" style="--c:#c4b5fd"><div class="chip">Validator</div>'
        '<div class="name">skillcheck</div><ul>'
        f"<li>{len(RULES)} rules, no dependencies</li><li>validate, list, new, index</li>"
        f'<li class="ok">OK: {len(skills)} skills checked, 0 problems</li></ul></div>'
    )
    template = (Path(__file__).parent / "grid.template.html").read_text(encoding="utf-8")
    page = template.replace("{{COUNT}}", str(len(skills))).replace("{{CARDS}}", "\n".join(cards))
    Path(sys.argv[1]).write_text(page, encoding="utf-8")
    print(f"wrote {sys.argv[1]}: {len(skills)} skills")
    return 0


if __name__ == "__main__":
    sys.exit(main())
