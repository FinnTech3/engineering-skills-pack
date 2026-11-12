"""Shared helpers: build small skill trees on disk and run the CLI in-process."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from skillcheck.cli import main

VALID_SKILL = """\
---
name: demo-skill
description: >
  Use when a demonstration skill is needed to test the validator. Do not use
  when real engineering work is being done.
---

# Demo skill

## Purpose

Show the smallest skill that passes every check.
Extra explanation can follow on later lines.

## Inputs needed

- A repository to inspect.

## Steps

1. Read the request.
2. Do the work.
3. Report the result.

## Output

Return the report as a short list.

## Exit criteria

- [ ] The report exists.
- [ ] The work was checked.

## Failure modes

- **Skipped check.** The work was reported without being checked.

## When to stop and ask

- The request is ambiguous.
"""


def skill_text(name: str = "demo-skill") -> str:
    return VALID_SKILL.replace("demo-skill", name)


def codes(problems: list) -> list[str]:
    return [p.code for p in problems]


@pytest.fixture
def make_skill(tmp_path: Path) -> Callable[..., Path]:
    """Create ``tmp_path/skills/<name>/SKILL.md`` and return the skill directory."""

    def _make(name: str = "demo-skill", text: str | None = None, folder: str | None = None) -> Path:
        directory = tmp_path / "skills" / (folder or name)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "SKILL.md").write_text(
            skill_text(name) if text is None else text, encoding="utf-8"
        )
        return directory

    return _make


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """The skills root used by ``make_skill``."""
    path = tmp_path / "skills"
    path.mkdir(exist_ok=True)
    return path


@pytest.fixture
def run(capsys: pytest.CaptureFixture[str]) -> Callable[..., tuple[int, str, str]]:
    """Run the CLI in-process: ``code, out, err = run("validate", path)``."""

    def _run(*argv: str | Path) -> tuple[int, str, str]:
        code = main([str(a) for a in argv])
        captured = capsys.readouterr()
        return code, captured.out, captured.err

    return _run
