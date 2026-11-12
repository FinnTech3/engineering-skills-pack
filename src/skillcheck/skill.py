"""Loading skills from disk: discovery, frontmatter, Markdown structure."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .frontmatter import Frontmatter, FrontmatterError, parse, split_lines

SKILL_FILE = "SKILL.md"

_H2_RE = re.compile(r"^##[ \t]+(\S.*?)[ \t]*$")
_FENCE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})")
_LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\S")
_NUMBERED_RE = re.compile(r"^\s*\d+[.)]\s+\S")


class PathError(ValueError):
    """Raised when the path given on the command line cannot be used."""


def normalize_heading(text: str) -> str:
    """Lower-case a heading, collapse whitespace and drop a trailing colon."""
    return " ".join(text.lower().split()).rstrip(":").strip()


def fence_mask(lines: list[str]) -> list[bool]:
    """Return one flag per line: True when the line is a code fence or sits inside one."""
    mask: list[bool] = []
    fence_char = ""
    fence_len = 0
    for line in lines:
        m = _FENCE_RE.match(line)
        if not fence_char:
            if m:
                fence_char, fence_len = m.group(1)[0], len(m.group(1))
                mask.append(True)
            else:
                mask.append(False)
            continue
        mask.append(True)
        closes = m and m.group(1)[0] == fence_char and len(m.group(1)) >= fence_len
        if closes and not line.strip().strip(fence_char):
            fence_char = ""
    return mask


@dataclass(frozen=True)
class Section:
    """An H2 section: its heading and the lines below it, up to the next H2."""

    title: str
    key: str
    line: int  # 1-based line of the heading
    body: tuple[tuple[int, str, bool], ...]  # (1-based line, text, inside a code fence)

    def is_blank(self) -> bool:
        """True when nothing but blank lines follows the heading."""
        return not any(t.strip() for _, t, _ in self.body)

    def content(self) -> list[tuple[int, str]]:
        """Non-blank lines outside fenced code."""
        return [(n, t) for n, t, fenced in self.body if t.strip() and not fenced]

    def list_items(self) -> list[tuple[int, str]]:
        return [(n, t) for n, t in self.content() if _LIST_ITEM_RE.match(t)]

    def numbered_items(self) -> list[tuple[int, str]]:
        return [(n, t) for n, t in self.content() if _NUMBERED_RE.match(t)]


def split_sections(lines: list[str], mask: list[bool]) -> list[Section]:
    heads = [
        (i, m.group(1)) for i, line in enumerate(lines) if not mask[i] and (m := _H2_RE.match(line))
    ]
    sections: list[Section] = []
    for pos, (i, title) in enumerate(heads):
        stop = heads[pos + 1][0] if pos + 1 < len(heads) else len(lines)
        body = tuple((n + 1, lines[n], mask[n]) for n in range(i + 1, stop))
        sections.append(Section(title, normalize_heading(title), i + 1, body))
    return sections


@dataclass
class MarkdownFile:
    """A Markdown file inside a skill folder, split into lines with a code-fence mask."""

    path: Path
    text: str
    lines: list[str]
    mask: list[bool]


@dataclass
class Skill:
    """One skill folder, loaded as far as it can be."""

    directory: Path
    path: Path  # the SKILL.md path (may not exist)
    read_error: str | None = None
    file: MarkdownFile | None = None
    frontmatter: Frontmatter | None = None
    frontmatter_error: FrontmatterError | None = None
    sections: list[Section] = field(default_factory=list)

    @property
    def folder_name(self) -> str:
        return self.directory.name

    @property
    def exists(self) -> bool:
        return self.path.is_file()

    def field(self, key: str) -> str | None:
        """Return a frontmatter value if it is a plain string, else None."""
        if self.frontmatter is None:
            return None
        value = self.frontmatter.data.get(key)
        return value if isinstance(value, str) else None

    @property
    def name(self) -> str:
        return (self.field("name") or "").strip()

    @property
    def description(self) -> str:
        return (self.field("description") or "").strip()

    @property
    def line_count(self) -> int:
        if self.file is None:
            return 0
        n = len(self.file.lines)
        return n - 1 if self.file.lines and self.file.lines[-1] == "" else n

    def section(self, key: str) -> Section | None:
        return next((s for s in self.sections if s.key == key), None)

    @property
    def summary(self) -> str:
        """First non-blank line of the Purpose section, used as the one-line summary."""
        purpose = self.section("purpose")
        if purpose is None:
            return ""
        content = purpose.content()
        return content[0][1].strip() if content else ""


def read_markdown(path: Path) -> MarkdownFile:
    """Read a Markdown file; raises OSError or UnicodeDecodeError on failure."""
    text = path.read_bytes().decode("utf-8")
    lines = split_lines(text.removeprefix("﻿"))
    return MarkdownFile(path=path, text=text, lines=lines, mask=fence_mask(lines))


def load_skill(directory: Path) -> Skill:
    """Load ``directory/SKILL.md``. Problems are recorded on the result, never raised."""
    skill = Skill(directory=directory, path=directory / SKILL_FILE)
    if not skill.exists:
        return skill
    try:
        skill.file = read_markdown(skill.path)
    except (OSError, UnicodeDecodeError) as exc:
        skill.read_error = f"cannot read file: {exc}"
        return skill
    try:
        skill.frontmatter = parse(skill.file.text)
    except FrontmatterError as exc:
        skill.frontmatter_error = exc
        return skill
    body_from = skill.frontmatter.body_start - 1
    lines = skill.file.lines
    mask = skill.file.mask
    skill.sections = [s for s in split_sections(lines, mask) if s.line > body_from]
    return skill


def discover(path: Path) -> list[Path]:
    """Return the skill directories under ``path``.

    ``path`` may be a skills root (every non-hidden folder inside it counts as a skill, so a
    folder without SKILL.md is reported), a single skill folder, or a SKILL.md file. Folders
    whose names start with ``.`` or ``_`` are ignored.
    """
    if not path.exists():
        raise PathError(f"path does not exist: {path}")
    if path.is_file():
        if path.name != SKILL_FILE:
            raise PathError(f"expected a directory or a {SKILL_FILE} file, got: {path}")
        return [path.parent]
    if (path / SKILL_FILE).exists():
        return [path]
    return sorted(
        (p for p in path.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))),
        key=lambda p: p.name,
    )


def load_all(path: Path) -> list[Skill]:
    return [load_skill(d) for d in discover(path)]
