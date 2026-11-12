"""Checks on this repository itself: the shipped skills, INDEX.md and the README."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from skillcheck.cli import main
from skillcheck.index import render_index
from skillcheck.rules import MAX_SKILL_LINES, RULES, validate_skills
from skillcheck.skill import load_all

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


@pytest.fixture(scope="module")
def skills():
    return load_all(SKILLS)


def test_pack_has_the_expected_number_of_skills(skills):
    assert len(skills) == 14


def test_shipped_skills_pass_validation(skills):
    problems = validate_skills(skills)
    assert [str(p) for p in problems] == []


def test_cli_validates_the_shipped_skills(capsys):
    assert main(["validate", str(SKILLS)]) == 0
    assert capsys.readouterr().out.strip() == "OK: 14 skills checked, 0 problems"


def test_every_skill_is_within_the_line_limit(skills):
    assert all(s.line_count <= MAX_SKILL_LINES for s in skills)


def test_descriptions_state_use_and_non_use(skills):
    for skill in skills:
        assert skill.description.startswith("Use when"), skill.name
        assert re.search(r"\b(?:Do not use|Not for)\b", skill.description), skill.name


def test_skill_names_are_unique(skills):
    names = [s.name for s in skills]
    assert len(names) == len(set(names))


def test_index_file_is_in_sync(skills):
    expected = render_index(skills, ROOT)
    actual = (ROOT / "INDEX.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    assert actual == expected, "INDEX.md is stale: run `skillcheck index`"


def test_index_check_command_passes(capsys, monkeypatch):
    monkeypatch.chdir(ROOT)
    assert main(["index", "--check"]) == 0


def readme_table_rows(text: str) -> dict[str, str]:
    """Map skill name to purpose for rows like ``| stage | [`name`](path) | purpose |``."""
    rows = {}
    for match in re.finditer(
        r"^\|[^|\n]*\| \[`([a-z0-9-]+)`\]\(([^)]+)\) \| (.+?) \|$", text, re.M
    ):
        rows[match.group(1)] = match.group(3)
    return rows


def test_readme_lists_every_skill_with_its_purpose(skills):
    rows = readme_table_rows((ROOT / "README.md").read_text(encoding="utf-8"))
    assert set(rows) == {s.name for s in skills}
    for skill in skills:
        assert rows[skill.name] == skill.summary


def test_readme_skill_links_exist():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    links = re.findall(r"\]\((skills/[^)#]+)\)", text)
    assert links
    for link in links:
        assert (ROOT / link).exists(), link


def test_readme_images_exist_and_have_alt_text():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    tags = re.findall(r"<img [^>]*>", text)
    assert tags
    for tag in tags:
        assert re.search(r'alt="[^"]+"', tag), f"image without alt text: {tag}"
        src = re.search(r'src="([^"]+)"', tag).group(1)
        if not src.startswith("http"):
            assert (ROOT / src).is_file(), src


def test_validator_reference_rule_table_matches_the_validator():
    text = (ROOT / "docs" / "validator.md").read_text(encoding="utf-8")
    documented = set(re.findall(r"^\| `([a-z]+(?:-[a-z]+)+)` \|", text, re.M))
    assert documented == set(RULES)


def test_license_and_notice_basics():
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert license_text.startswith("MIT License")
    assert "Copyright (c) 2026 FinnTech3" in license_text


def test_ci_workflow_runs_the_documented_checks():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for command in ("ruff check .", "pytest -q", "skillcheck validate skills", "index --check"):
        assert command in ci
    for version in ("3.10", "3.11", "3.12", "3.13"):
        assert f'"{version}"' in ci


def test_skills_only_point_to_skills_that_exist(skills):
    names = {s.name for s in skills}
    pattern = re.compile(r"\b(?:see|use|run|first)\s+`([a-z0-9]+(?:-[a-z0-9]+)+)`", re.I)
    found = 0
    for skill in skills:
        text = skill.file.text
        for match in pattern.finditer(text):
            found += 1
            assert match.group(1) in names, f"{skill.name} points to unknown skill {match.group(1)}"
    assert found >= 5  # the cross-references exist, so this check is not vacuous


def test_skill_files_are_plain_ascii(skills):
    for skill in skills:
        assert skill.file.text.isascii(), skill.name
