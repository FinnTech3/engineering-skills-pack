"""The template written by ``skillcheck new``."""

from __future__ import annotations

from pathlib import Path

from .rules import is_valid_name
from .skill import SKILL_FILE

# Every TODO below is reported by `skillcheck validate` until it is replaced, so a scaffold
# cannot be committed by accident. The text around the markers already satisfies the
# structural rules (section names, order, numbered steps, list items).
TEMPLATE = """\
---
name: {name}
description: >
  Use when TODO: describe the exact situation that should trigger this skill.
  Do not use when TODO: describe the nearest case that looks similar but is not a fit.
---

# {title}

## Purpose

TODO: one sentence saying what this skill produces.

## Inputs needed

- TODO: what the agent must have before starting.

## Steps

1. TODO: first concrete action, with the command or artifact it produces.
2. TODO: second action.
3. TODO: third action.

## Output

TODO: what the agent hands back, and in which order.

## Exit criteria

- [ ] TODO: a result that can be checked by command, number or file.

## Failure modes

- **TODO: symptom.** TODO: why it happens and how to avoid it.

## When to stop and ask

- TODO: a condition under which the agent must stop and ask a person.
"""


def render(name: str) -> str:
    return TEMPLATE.format(name=name, title=name.replace("-", " ").capitalize())


def create(root: Path, name: str) -> Path:
    """Create ``root/name/SKILL.md`` from the template and return its path.

    Raises ``ValueError`` for an invalid name and ``FileExistsError`` if the folder exists.
    """
    if not is_valid_name(name):
        raise ValueError(
            f"invalid skill name {name!r}: use lower-case letters and digits separated by "
            "single hyphens, at most 64 characters"
        )
    target = root / name
    if target.exists():
        raise FileExistsError(f"already exists: {target}")
    target.mkdir(parents=True)
    path = target / SKILL_FILE
    path.write_text(render(name), encoding="utf-8", newline="\n")
    return path
