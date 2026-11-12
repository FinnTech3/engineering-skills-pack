"""A small, dependency-free parser for the YAML subset used in SKILL.md frontmatter.

Supported at the top level of the block (every scalar is returned as a string):

* plain scalars, including multi-line plain scalars (folded with single spaces)
* single-quoted and double-quoted scalars, including multi-line ones
* block scalars: folded (``>``) and literal (``|``) with the ``-`` and ``+`` chomping indicators
* flow lists such as ``[a, b]`` and block lists (``- a``)
* one level of nested mapping whose values are scalars

Not supported, and reported as errors: anchors, aliases, tags, flow mappings, explicit
indentation indicators, nesting deeper than one level, duplicate keys and tab indentation.
Plain scalars that a strict YAML loader would reject (a ``: `` inside the value, or a leading
indicator character) are reported too, so a file that passes here also loads elsewhere.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

Value = str | list[str] | dict[str, str]
Line = tuple[int, str]  # (1-based line number in the file, text)

_KEY_RE = re.compile(r"^([A-Za-z0-9_][A-Za-z0-9_.-]*)[ ]*:(?:[ ]+(.*))?$")
_BLOCK_INDICATOR_RE = re.compile(r"^([>|])([+-]?)[ ]*(?:#.*)?$")
_PLAIN_FORBIDDEN_START = ",]}#&*!%@`"
_DOUBLE_ESCAPES = {
    "0": "\0",
    "n": "\n",
    "t": "\t",
    "r": "\r",
    '"': '"',
    "\\": "\\",
    "/": "/",
    " ": " ",
}


class FrontmatterError(ValueError):
    """Raised when frontmatter cannot be parsed. ``line`` is 1-based in the file, if known."""

    def __init__(self, message: str, line: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.line = line


@dataclass(frozen=True)
class Frontmatter:
    """Parsed frontmatter plus the position information the validator needs."""

    data: dict[str, Value] = field(default_factory=dict)
    key_lines: dict[str, int] = field(default_factory=dict)
    body_start: int = 1  # 1-based line number of the first line after the closing delimiter


def split_lines(text: str) -> list[str]:
    """Split on ``\\n`` or ``\\r\\n`` only, so that other separators never hide trailing space."""
    return text.replace("\r\n", "\n").split("\n")


def parse(text: str) -> Frontmatter:
    """Parse the frontmatter block at the top of ``text``."""
    lines = split_lines(text.removeprefix("﻿"))
    if lines[0].rstrip() != "---":
        raise FrontmatterError("file must start with a '---' frontmatter delimiter", 1)
    end = next((i for i in range(1, len(lines)) if lines[i].rstrip() in ("---", "...")), None)
    if end is None:
        raise FrontmatterError("frontmatter is not closed with a '---' line", 1)
    data, key_lines = _parse_block(lines[1:end], first_line=2)
    return Frontmatter(data=data, key_lines=key_lines, body_start=end + 2)


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _parse_block(block: list[str], first_line: int) -> tuple[dict[str, Value], dict[str, int]]:
    data: dict[str, Value] = {}
    key_lines: dict[str, int] = {}
    i = 0
    while i < len(block):
        line = block[i]
        lineno = first_line + i
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        if re.match(r" *\t", line):
            raise FrontmatterError("tabs are not allowed for indentation", lineno)
        if line[0] == " ":
            raise FrontmatterError("unexpected indentation (no key above this line)", lineno)
        match = _KEY_RE.match(line.rstrip())
        if not match:
            raise FrontmatterError(f"expected 'key: value', got {stripped!r}", lineno)
        key, rest = match.group(1), (match.group(2) or "").strip()
        if key in data:
            raise FrontmatterError(f"duplicate key {key!r}", lineno)
        key_lines[key] = lineno
        value, i = _parse_value(block, i, rest, first_line)
        data[key] = value
    return data, key_lines


def _children(
    block: list[str], start: int, first_line: int, allow_dash_at_root: bool
) -> tuple[list[Line], int]:
    """Collect the lines that belong to the key above ``block[start]``.

    Returns the lines and the index of the first line that is not consumed.
    """
    out: list[Line] = []
    j = start
    while j < len(block):
        line = block[j]
        is_child = not line.strip() or line[0] == " "
        is_root_item = allow_dash_at_root and (line.startswith("- ") or line.rstrip() == "-")
        if not (is_child or is_root_item):
            break
        out.append((first_line + j, line))
        j += 1
    # Trailing blank lines belong to the gap before the next key, not to this value.
    while out and not out[-1][1].strip():
        out.pop()
        j -= 1
    return out, j


def _parse_value(block: list[str], i: int, rest: str, first_line: int) -> tuple[Value, int]:
    lineno = first_line + i
    if rest.startswith("#"):
        rest = ""
    if rest and rest[0] in ">|":
        return _parse_block_scalar(block, i, rest, first_line)
    if rest[:1] in ('"', "'"):
        return _parse_quoted(block, i, rest, first_line)
    if rest.startswith("["):
        return _parse_flow_list(block, i, rest, first_line)
    if rest.startswith("{"):
        raise FrontmatterError("flow mappings are not supported", lineno)
    if rest and rest[0] in _PLAIN_FORBIDDEN_START:
        raise FrontmatterError(
            f"a plain value cannot start with {rest[0]!r}; quote it or use a '>' block", lineno
        )
    plain = _strip_comment(rest)
    kids, j = _children(block, i + 1, first_line, allow_dash_at_root=not plain)
    kids = [(n, t) for n, t in kids if not t.strip().startswith("#")]
    first = next((t.strip() for _, t in kids if t.strip()), "")
    if not plain and first:
        if first == "-" or first.startswith("- "):
            return _parse_block_list(kids), j
        if _KEY_RE.match(first):
            return _parse_nested_map(kids), j
    if first:
        plain = _fold_plain([plain] + [t.strip() for _, t in kids])
    _check_plain(plain, lineno)
    return plain, j


def _strip_comment(text: str) -> str:
    m = re.search(r"(?:^|\s)#", text)
    return (text[: m.start()] if m else text).strip()


def _check_plain(text: str, lineno: int) -> None:
    if ": " in text or text.endswith(":"):
        raise FrontmatterError(
            "a plain value cannot contain ': '; quote the value or use a '>' block", lineno
        )


def _fold_plain(parts: list[str]) -> str:
    """Fold continuation lines: one space between lines, each blank line becomes a newline."""
    out = ""
    blanks = 0
    for part in parts:
        if not part:
            blanks += 1
            continue
        if not out:
            out = part
        elif blanks:
            out += "\n" * blanks + part
        else:
            out += " " + part
        blanks = 0
    return out


def _parse_block_scalar(block: list[str], i: int, rest: str, first_line: int) -> tuple[str, int]:
    lineno = first_line + i
    m = _BLOCK_INDICATOR_RE.match(rest)
    if not m:
        raise FrontmatterError(
            f"unsupported block scalar header {rest!r} (explicit indentation is not supported)",
            lineno,
        )
    style, chomp = m.group(1), m.group(2)
    raw, j = _children(block, i + 1, first_line, allow_dash_at_root=False)
    trailing = 0
    while j + trailing < len(block) and not block[j + trailing].strip():
        trailing += 1
    lines = [t for _, t in raw]
    indents = [_indent(t) for t in lines if t.strip()]
    if not indents:
        return "", j
    base = min(indents)
    if _indent(next(t for t in lines if t.strip())) != base:
        raise FrontmatterError(
            "the first line of a block scalar must have the smallest indentation", lineno + 1
        )
    body = [t[base:] if t.strip() else "" for t in lines]
    text = _fold_folded(body) if style == ">" else "\n".join(body)
    if chomp == "+":
        text += "\n" * (1 + trailing)
    elif chomp == "":
        text += "\n"
    return text, j


def _fold_folded(body: list[str]) -> str:
    """Fold a ``>`` scalar: lines join with a space, blank lines keep their newlines, and
    more-indented lines keep the line breaks around them."""
    out = ""
    blanks = 0
    prev_indented = False
    seen = False
    for line in body:
        if not line:
            blanks += 1
            continue
        indented = line[0] in " \t"
        if not seen:
            out = "\n" * blanks + line
        elif prev_indented or indented:
            out += "\n" * (blanks + 1) + line
        elif blanks:
            out += "\n" * blanks + line
        else:
            out += " " + line
        seen = True
        prev_indented = indented
        blanks = 0
    return out


def _parse_quoted(block: list[str], i: int, rest: str, first_line: int) -> tuple[str, int]:
    quote = rest[0]
    buf = rest
    j = i
    while True:
        end = _find_closing_quote(buf, quote)
        if end is not None:
            break
        j += 1
        if j >= len(block):
            raise FrontmatterError("unterminated quoted value", first_line + i)
        nxt = block[j].strip()
        if not nxt:
            buf += "\n"
        elif buf.endswith("\n"):
            buf += nxt
        else:
            buf += " " + nxt
    tail = buf[end + 1 :].strip()
    if tail and not tail.startswith("#"):
        raise FrontmatterError(f"unexpected text after closing quote: {tail!r}", first_line + j)
    inner = buf[1:end]
    value = inner.replace("''", "'") if quote == "'" else _decode_double(inner, first_line + i)
    return value, j + 1


def _find_closing_quote(buf: str, quote: str) -> int | None:
    k = 1
    while k < len(buf):
        ch = buf[k]
        if quote == '"' and ch == "\\":
            k += 2
            continue
        if ch == quote:
            if quote == "'" and buf[k + 1 : k + 2] == "'":
                k += 2
                continue
            return k
        k += 1
    return None


def _decode_double(inner: str, lineno: int) -> str:
    out: list[str] = []
    k = 0
    while k < len(inner):
        ch = inner[k]
        if ch != "\\":
            out.append(ch)
            k += 1
            continue
        nxt = inner[k + 1 : k + 2]
        if nxt in _DOUBLE_ESCAPES:
            out.append(_DOUBLE_ESCAPES[nxt])
            k += 2
        elif nxt in ("x", "u"):
            width = 2 if nxt == "x" else 4
            digits = inner[k + 2 : k + 2 + width]
            if len(digits) != width or not re.fullmatch(r"[0-9a-fA-F]+", digits):
                raise FrontmatterError(f"invalid \\{nxt} escape", lineno)
            out.append(chr(int(digits, 16)))
            k += 2 + width
        else:
            raise FrontmatterError(f"unknown escape sequence '\\{nxt}'", lineno)
    return "".join(out)


def _parse_scalar(text: str, lineno: int) -> str:
    """Parse a single-line scalar used inside a list or a nested mapping."""
    text = text.strip()
    if text[:1] in ('"', "'"):
        end = _find_closing_quote(text, text[0])
        if end is None:
            raise FrontmatterError("unterminated quoted value", lineno)
        if text[end + 1 :].strip():
            raise FrontmatterError("unexpected text after closing quote", lineno)
        inner = text[1:end]
        return inner.replace("''", "'") if text[0] == "'" else _decode_double(inner, lineno)
    value = _strip_comment(text)
    _check_plain(value, lineno)
    return value


def _split_flow(text: str, lineno: int) -> list[str]:
    items: list[str] = []
    cur: list[str] = []
    quote = ""
    k = 0
    while k < len(text):
        ch = text[k]
        if quote:
            cur.append(ch)
            if quote == '"' and ch == "\\":
                cur.append(text[k + 1 : k + 2])
                k += 1
            elif ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
            cur.append(ch)
        elif ch == ",":
            items.append("".join(cur))
            cur = []
        elif ch in "[]{}":
            raise FrontmatterError("nested flow collections are not supported", lineno)
        else:
            cur.append(ch)
        k += 1
    items.append("".join(cur))
    return items


def _find_flow_close(buf: str, lineno: int) -> int | None:
    """Index of the ``]`` that closes the list starting at ``buf[0]``, ignoring quoted text."""
    quote = ""
    k = 1
    while k < len(buf):
        ch = buf[k]
        if quote:
            if quote == '"' and ch == "\\":
                k += 1
            elif ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
        elif ch in "[{":
            raise FrontmatterError("nested flow collections are not supported", lineno)
        elif ch == "]":
            return k
        k += 1
    return None


def _parse_flow_list(block: list[str], i: int, rest: str, first_line: int) -> tuple[list[str], int]:
    lineno = first_line + i
    buf = rest
    j = i
    while (close := _find_flow_close(buf, lineno)) is None:
        j += 1
        if j >= len(block):
            raise FrontmatterError("unterminated '[' list", lineno)
        buf += " " + block[j].strip()
    tail = buf[close + 1 :].strip()
    if tail and not tail.startswith("#"):
        raise FrontmatterError(f"unexpected text after ']': {tail!r}", lineno)
    inner = buf[1:close].strip()
    if not inner:
        return [], j + 1
    values = [_parse_scalar(p, lineno) for p in _split_flow(inner, lineno) if p.strip()]
    return values, j + 1


def _parse_block_list(children: list[Line]) -> list[str]:
    items: list[str] = []
    for lineno, raw in children:
        text = raw.strip()
        if not text:
            continue
        if text != "-" and not text.startswith("- "):
            raise FrontmatterError("list items must start with '- '", lineno)
        items.append(_parse_scalar(text[1:], lineno) if text != "-" else "")
    return items


def _parse_nested_map(children: list[Line]) -> dict[str, str]:
    result: dict[str, str] = {}
    base = min(_indent(t) for _, t in children if t.strip())
    for lineno, raw in children:
        if not raw.strip():
            continue
        if _indent(raw) != base:
            raise FrontmatterError("nesting deeper than one level is not supported", lineno)
        m = _KEY_RE.match(raw.strip())
        if not m:
            raise FrontmatterError(f"expected 'key: value', got {raw.strip()!r}", lineno)
        key, val = m.group(1), (m.group(2) or "").strip()
        if key in result:
            raise FrontmatterError(f"duplicate key {key!r}", lineno)
        if val[:1] in ("[", "{", ">", "|"):
            raise FrontmatterError("nested values must be plain or quoted scalars", lineno)
        result[key] = _parse_scalar(val, lineno) if val else ""
    return result
