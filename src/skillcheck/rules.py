"""Validation rules. Each problem has a stable ``code`` so it can be searched and tested."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from urllib.parse import unquote

from .skill import (
    SKILL_FILE,
    MarkdownFile,
    Skill,
    normalize_heading,
    read_markdown,
)

MAX_SKILL_LINES = 120
MAX_REFERENCE_LINES = 200
MAX_NAME_LENGTH = 64
MIN_DESCRIPTION_LENGTH = 60
MAX_DESCRIPTION_LENGTH = 500
MAX_PURPOSE_LINE = 120
MIN_STEPS = 3

REQUIRED_SECTIONS = (
    "Purpose",
    "Inputs needed",
    "Steps",
    "Output",
    "Exit criteria",
    "Failure modes",
    "When to stop and ask",
)

LIST_SECTIONS = ("exit criteria", "failure modes", "when to stop and ask")

# Filler that adds no information. Matching is case-insensitive, on whole words, outside code.
BANNED_PHRASES = (
    "best practice",
    "best practices",
    "as appropriate",
    "as needed",
    "as necessary",
    "and so on",
    "and so forth",
    "etc.",
    "simply",
    "just",
    "obviously",
    "of course",
    "clearly",
    "basically",
    "really",
    "very",
    "easily",
    "robust",
    "seamless",
    "seamlessly",
    "leverage",
    "synergy",
    "cutting-edge",
    "state-of-the-art",
    "world-class",
    "properly",
    "appropriately",
    "make sure",
    "be sure to",
    "it is important to",
    "it's important to",
    "feel free",
    "good enough",
    "various",
    "numerous",
    "a number of",
    "stuff",
)

# Every problem code the validator can emit, with a one-line description.
RULES: dict[str, str] = {
    "no-skills": "no skill folders were found under the path",
    "skill-file-missing": "a folder under the skills root has no SKILL.md",
    "read-error": "a Markdown file cannot be read as UTF-8",
    "frontmatter-invalid": "frontmatter is missing, unclosed, malformed or has a non-string key",
    "name-missing": "frontmatter has no name, or it is empty",
    "name-not-kebab": "name is not lower-case words joined by single hyphens",
    "name-too-long": f"name is longer than {MAX_NAME_LENGTH} characters",
    "name-mismatch": "name differs from the folder name",
    "duplicate-name": "two skills use the same name",
    "description-missing": "frontmatter has no description, or it is empty",
    "description-too-short": f"description is under {MIN_DESCRIPTION_LENGTH} characters",
    "description-too-long": f"description is over {MAX_DESCRIPTION_LENGTH} characters",
    "description-multiline": "description contains line breaks (use a folded `>` scalar)",
    "description-no-trigger": 'description does not say when to use the skill ("Use when ...")',
    "description-no-exclusion": 'description does not say when not to use it ("Do not use ...")',
    "section-missing": "a required section is absent",
    "section-order": "required sections are not in the standard order",
    "section-empty": "a required section has no content",
    "steps-not-numbered": f"Steps has fewer than {MIN_STEPS} numbered items",
    "section-no-list": "Exit criteria, Failure modes or When to stop and ask has no list items",
    "purpose-too-long": f"the first line of Purpose is over {MAX_PURPOSE_LINE} characters",
    "line-limit": (
        f"SKILL.md is over {MAX_SKILL_LINES} lines, or a reference file is over "
        f"{MAX_REFERENCE_LINES}"
    ),
    "broken-link": "a relative link points to a file that does not exist",
    "link-escapes-skill": "a relative link points outside the skill folder",
    "orphan-reference": "a Markdown file in the skill folder is not linked from SKILL.md",
    "banned-phrase": "vague filler from the banned list appears outside code",
    "todo-placeholder": "a TODO, FIXME or TBD marker is left in the text",
    "trailing-whitespace": "a line ends with spaces or tabs",
}

KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_TRIGGER_RE = re.compile(r"\buse\s+(?:this\s+skill\s+)?when\b", re.IGNORECASE)
_EXCLUSION_RE = re.compile(
    r"\b(?:do\s+not\s+use|don't\s+use|never\s+use|not\s+for|skip\s+(?:this\s+skill\s+)?when)\b",
    re.IGNORECASE,
)
_PLACEHOLDER_RE = re.compile(r"\b(?:TODO|FIXME|TBD)\b")
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
_INLINE_LINK_RE = re.compile(
    r"\[[^\]\n]{0,300}\]\(\s*<?([^)\s>]+)>?(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)"
)
_REF_LINK_RE = re.compile(r"^\s{0,3}\[[^\]\n]+\]:\s*<?(\S+?)>?(?:\s|$)")
_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def _banned_regex(phrase: str) -> re.Pattern[str]:
    body = r"\s+".join(re.escape(part) for part in phrase.split())
    return re.compile(rf"(?<![\w/-]){body}(?![\w-])", re.IGNORECASE)


_BANNED_RES = tuple((phrase, _banned_regex(phrase)) for phrase in BANNED_PHRASES)


@dataclass(frozen=True)
class Problem:
    """One finding. ``line`` is 1-based, or None when it applies to the whole file."""

    path: str
    line: int | None
    code: str
    message: str

    def __post_init__(self) -> None:
        if self.code not in RULES:
            raise ValueError(f"unknown problem code {self.code!r}; add it to RULES")

    def sort_key(self) -> tuple[str, int, str, str]:
        return (self.path, self.line or 0, self.code, self.message)

    def to_dict(self) -> dict[str, object]:
        return {"path": self.path, "line": self.line, "code": self.code, "message": self.message}

    def __str__(self) -> str:
        where = f"{self.path}:{self.line}" if self.line else self.path
        return f"{where}: {self.code}: {self.message}"


def is_kebab(name: str) -> bool:
    return bool(KEBAB_RE.match(name))


def is_valid_name(name: str) -> bool:
    """True when ``name`` is kebab-case and short enough to be a skill name."""
    return len(name) <= MAX_NAME_LENGTH and is_kebab(name)


# ---------------------------------------------------------------------------
# Per-skill checks
# ---------------------------------------------------------------------------


def validate_skill(skill: Skill, max_lines: int = MAX_SKILL_LINES) -> list[Problem]:
    """Run every check that needs only this skill folder."""
    problems: list[Problem] = []
    shown = str(skill.path)

    if not skill.exists:
        problems.append(
            Problem(str(skill.directory), None, "skill-file-missing", f"no {SKILL_FILE} in folder")
        )
        return problems
    if skill.read_error:
        problems.append(Problem(shown, None, "read-error", skill.read_error))
        return problems

    assert skill.file is not None
    if skill.frontmatter_error is not None:
        err = skill.frontmatter_error
        problems.append(Problem(shown, err.line, "frontmatter-invalid", err.message))
    else:
        problems.extend(_check_frontmatter(skill))
        problems.extend(_check_sections(skill))
    if skill.line_count > max_lines:
        problems.append(
            Problem(
                shown,
                max_lines + 1,
                "line-limit",
                f"{skill.line_count} lines; the limit is {max_lines}",
            )
        )
    problems.extend(_check_markdown(skill.file, skill.directory))
    problems.extend(_check_references(skill))
    return problems


def _check_frontmatter(skill: Skill) -> list[Problem]:
    assert skill.frontmatter is not None
    shown = str(skill.path)
    fm = skill.frontmatter
    problems: list[Problem] = []

    def where(key: str) -> int | None:
        return fm.key_lines.get(key, 1)

    for key in ("name", "description"):
        value = fm.data.get(key)
        if key not in fm.data:
            problems.append(Problem(shown, 1, f"{key}-missing", f"frontmatter has no '{key}'"))
        elif not isinstance(value, str):
            problems.append(
                Problem(shown, where(key), "frontmatter-invalid", f"'{key}' must be a string")
            )
        elif not value.strip():
            problems.append(Problem(shown, where(key), f"{key}-missing", f"'{key}' is empty"))

    name = skill.name
    if name:
        if len(name) > MAX_NAME_LENGTH:
            problems.append(
                Problem(
                    shown,
                    where("name"),
                    "name-too-long",
                    f"name is {len(name)} characters; the limit is {MAX_NAME_LENGTH}",
                )
            )
        if not is_kebab(name):
            problems.append(
                Problem(
                    shown,
                    where("name"),
                    "name-not-kebab",
                    f"name {name!r} must be lower-case letters and digits separated by single "
                    "hyphens",
                )
            )
        if name != skill.folder_name:
            problems.append(
                Problem(
                    shown,
                    where("name"),
                    "name-mismatch",
                    f"name {name!r} does not match folder {skill.folder_name!r}",
                )
            )

    desc = skill.description
    if desc:
        line = where("description")
        if len(desc) < MIN_DESCRIPTION_LENGTH:
            problems.append(
                Problem(
                    shown,
                    line,
                    "description-too-short",
                    f"description is {len(desc)} characters; the minimum is "
                    f"{MIN_DESCRIPTION_LENGTH}",
                )
            )
        if len(desc) > MAX_DESCRIPTION_LENGTH:
            problems.append(
                Problem(
                    shown,
                    line,
                    "description-too-long",
                    f"description is {len(desc)} characters; the limit is {MAX_DESCRIPTION_LENGTH}",
                )
            )
        if "\n" in desc:
            problems.append(
                Problem(
                    shown,
                    line,
                    "description-multiline",
                    "description contains line breaks; use a '>' folded scalar",
                )
            )
        if not _TRIGGER_RE.search(desc):
            problems.append(
                Problem(
                    shown,
                    line,
                    "description-no-trigger",
                    "description must say when to use the skill, for example 'Use when ...'",
                )
            )
        if not _EXCLUSION_RE.search(desc):
            problems.append(
                Problem(
                    shown,
                    line,
                    "description-no-exclusion",
                    "description must say when not to use the skill, for example "
                    "'Do not use when ...' or 'Not for ...'",
                )
            )
    return problems


def _check_sections(skill: Skill) -> list[Problem]:
    shown = str(skill.path)
    problems: list[Problem] = []
    by_key = {s.key: s for s in reversed(skill.sections)}  # first occurrence wins
    wanted = [normalize_heading(r) for r in REQUIRED_SECTIONS]

    for title, key in zip(REQUIRED_SECTIONS, wanted, strict=True):
        if key not in by_key:
            problems.append(
                Problem(shown, None, "section-missing", f"missing section '## {title}'")
            )

    present = [by_key[k] for k in wanted if k in by_key]
    if [s.line for s in present] != sorted(s.line for s in present):
        order = ", ".join(REQUIRED_SECTIONS)
        first_wrong = next((b for a, b in pairwise(present) if b.line < a.line), present[0])
        problems.append(
            Problem(
                shown,
                first_wrong.line,
                "section-order",
                f"required sections must appear in this order: {order}",
            )
        )

    for key in wanted:
        section = by_key.get(key)
        if section is None:
            continue
        if section.is_blank():
            problems.append(
                Problem(shown, section.line, "section-empty", f"section '{section.title}' is empty")
            )
            continue
        if key == "steps":
            count = len(section.numbered_items())
            if count < MIN_STEPS:
                problems.append(
                    Problem(
                        shown,
                        section.line,
                        "steps-not-numbered",
                        f"'Steps' needs at least {MIN_STEPS} numbered items; found {count}",
                    )
                )
        elif key in LIST_SECTIONS and not section.list_items():
            problems.append(
                Problem(
                    shown,
                    section.line,
                    "section-no-list",
                    f"'{section.title}' must be a list of items",
                )
            )

    purpose = by_key.get("purpose")
    if purpose is not None and purpose.content():
        n, text = purpose.content()[0]
        if len(text.strip()) > MAX_PURPOSE_LINE:
            problems.append(
                Problem(
                    shown,
                    n,
                    "purpose-too-long",
                    f"first line of 'Purpose' is {len(text.strip())} characters; it is used as "
                    f"the one-line summary, so keep it under {MAX_PURPOSE_LINE}",
                )
            )
    return problems


# ---------------------------------------------------------------------------
# Checks that apply to every Markdown file in a skill folder
# ---------------------------------------------------------------------------


def markdown_files(directory: Path) -> list[Path]:
    """Every ``*.md`` file under ``directory``, skipping hidden folders, sorted."""
    found = []
    for p in directory.rglob("*.md"):
        rel = p.relative_to(directory)
        if any(part.startswith(".") for part in rel.parts[:-1]):
            continue
        if p.is_file():
            found.append(p)
    return sorted(found)


def _strip_inline_code(line: str) -> str:
    return _INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), line)


def _check_markdown(md: MarkdownFile, skill_dir: Path) -> list[Problem]:
    """Trailing whitespace, banned phrases, placeholders and links for one file."""
    shown = str(md.path)
    problems: list[Problem] = []
    root = skill_dir.resolve()
    for i, line in enumerate(md.lines):
        n = i + 1
        if line != line.rstrip():
            problems.append(Problem(shown, n, "trailing-whitespace", "line ends with whitespace"))
        if md.mask[i]:
            continue
        prose = _strip_inline_code(line)
        for phrase, regex in _BANNED_RES:
            if regex.search(prose):
                problems.append(
                    Problem(
                        shown,
                        n,
                        "banned-phrase",
                        f"'{phrase}' is vague filler; state the concrete thing instead",
                    )
                )
        if _PLACEHOLDER_RE.search(prose):
            problems.append(
                Problem(shown, n, "todo-placeholder", "placeholder marker left in the text")
            )
        for target in _link_targets(prose):
            problem = _check_link(md.path, root, target, n)
            if problem:
                problems.append(problem)
    return problems


def _link_targets(prose: str) -> list[str]:
    targets = _INLINE_LINK_RE.findall(prose)
    ref = _REF_LINK_RE.match(prose)
    if ref:
        targets.append(ref.group(1))
    return targets


def _local_path(target: str) -> str | None:
    """The file part of a link target, or None for anchors, URLs and empty targets."""
    if not target or target.startswith("#") or _SCHEME_RE.match(target):
        return None
    clean = unquote(target.split("#", 1)[0].split("?", 1)[0])
    return clean or None


def _check_link(source: Path, skill_root: Path, target: str, line: int) -> Problem | None:
    clean = _local_path(target)
    if clean is None:
        return None
    resolved = (source.parent / clean).resolve()
    if not resolved.is_relative_to(skill_root):
        return Problem(
            str(source),
            line,
            "link-escapes-skill",
            f"link {target!r} points outside the skill folder, so it breaks when the folder "
            "is copied on its own",
        )
    if not resolved.exists():
        return Problem(str(source), line, "broken-link", f"link target {target!r} does not exist")
    return None


def _check_references(skill: Skill) -> list[Problem]:
    """Check every other Markdown file in the folder, and that SKILL.md links to each."""
    assert skill.file is not None
    problems: list[Problem] = []
    root = skill.directory.resolve()
    linked: set[Path] = set()
    for i, line in enumerate(skill.file.lines):
        if skill.file.mask[i]:
            continue
        for target in _link_targets(_strip_inline_code(line)):
            clean = _local_path(target)
            if clean is not None:
                linked.add((skill.path.parent / clean).resolve())
    for path in markdown_files(skill.directory):
        if path.resolve() == skill.path.resolve():
            continue
        try:
            md = read_markdown(path)
        except (OSError, UnicodeDecodeError) as exc:
            problems.append(Problem(str(path), None, "read-error", f"cannot read file: {exc}"))
            continue
        problems.extend(_check_markdown(md, skill.directory))
        if len(md.lines) - (1 if md.lines[-1] == "" else 0) > MAX_REFERENCE_LINES:
            problems.append(
                Problem(
                    str(path),
                    MAX_REFERENCE_LINES + 1,
                    "line-limit",
                    f"reference file is over {MAX_REFERENCE_LINES} lines",
                )
            )
        if path.resolve() not in linked and path.resolve().is_relative_to(root):
            problems.append(
                Problem(
                    str(path),
                    None,
                    "orphan-reference",
                    f"{SKILL_FILE} does not link to this file",
                )
            )
    return problems


# ---------------------------------------------------------------------------
# Whole-tree checks
# ---------------------------------------------------------------------------


def validate_skills(
    skills: list[Skill], max_lines: int = MAX_SKILL_LINES, root: str = "."
) -> list[Problem]:
    """Validate every skill and the cross-skill rules. The result is sorted."""
    problems: list[Problem] = []
    if not skills:
        problems.append(Problem(root, None, "no-skills", "no skill folders found"))
    for skill in skills:
        problems.extend(validate_skill(skill, max_lines))
    problems.extend(_check_duplicates(skills))
    return sorted(problems, key=Problem.sort_key)


def _check_duplicates(skills: list[Skill]) -> list[Problem]:
    seen: dict[str, list[Skill]] = defaultdict(list)
    for skill in skills:
        if skill.name:
            seen[skill.name.lower()].append(skill)
    problems = []
    for group in seen.values():
        first, *rest = group
        for dup in rest:
            line = dup.frontmatter.key_lines.get("name") if dup.frontmatter else None
            problems.append(
                Problem(
                    str(dup.path),
                    line,
                    "duplicate-name",
                    f"name {dup.name!r} is already used by {first.path}",
                )
            )
    return problems
