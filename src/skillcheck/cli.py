"""Command-line interface. Exit codes: 0 ok, 1 problems found, 2 usage error."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .index import render_index, usable
from .rules import MAX_SKILL_LINES, Problem, validate_skills
from .scaffold import create
from .skill import PathError, Skill, load_all

EXIT_OK = 0
EXIT_PROBLEMS = 1
EXIT_USAGE = 2

DEFAULT_PATH = "skills"
DEFAULT_INDEX = "INDEX.md"
DESCRIPTION_WIDTH = 72


def _positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not an integer: {text!r}") from None
    if value < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skillcheck",
        description="Validate, list, index and scaffold Agent Skills folders.",
        epilog="Exit codes: 0 ok, 1 problems found, 2 usage error.",
    )
    parser.add_argument("--version", action="version", version=f"skillcheck {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    p = sub.add_parser("validate", help="check skills against the pack rules")
    p.add_argument(
        "path",
        nargs="?",
        default=DEFAULT_PATH,
        help=f"skills root, a skill folder or a SKILL.md file (default: {DEFAULT_PATH})",
    )
    p.add_argument("--json", action="store_true", help="print the result as JSON")
    p.add_argument(
        "--max-lines",
        type=_positive_int,
        default=MAX_SKILL_LINES,
        metavar="N",
        help=f"line limit for SKILL.md (default: {MAX_SKILL_LINES})",
    )

    p = sub.add_parser("list", help="print a table of skills and their descriptions")
    p.add_argument("path", nargs="?", default=DEFAULT_PATH, help="skills root or a skill folder")
    p.add_argument("--full", action="store_true", help="do not shorten descriptions")

    p = sub.add_parser("new", help="scaffold a new skill from the template")
    p.add_argument("name", help="skill name: lower-case words joined by hyphens")
    p.add_argument(
        "--path",
        default=DEFAULT_PATH,
        help=f"skills root to create the folder in (default: {DEFAULT_PATH})",
    )

    p = sub.add_parser("index", help=f"generate {DEFAULT_INDEX} from the skills")
    p.add_argument("path", nargs="?", default=DEFAULT_PATH, help="skills root")
    p.add_argument(
        "-o",
        "--output",
        default=DEFAULT_INDEX,
        help=f"file to write, or - for stdout (default: {DEFAULT_INDEX})",
    )
    p.add_argument(
        "--check",
        action="store_true",
        help="write nothing; exit 1 if the output file is missing or out of date",
    )
    return parser


def _make_output_safe() -> None:
    """Never crash on a character the terminal encoding cannot show (for example in a name)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="backslashreplace")


def main(argv: list[str] | None = None) -> int:
    _make_output_safe()
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # argparse exits on --help, --version and usage errors
        return exc.code if isinstance(exc.code, int) else EXIT_USAGE
    if args.command is None:
        parser.print_usage(sys.stderr)
        print("skillcheck: error: a command is required", file=sys.stderr)
        return EXIT_USAGE
    handler = {
        "validate": _cmd_validate,
        "list": _cmd_list,
        "new": _cmd_new,
        "index": _cmd_index,
    }[args.command]
    try:
        return handler(args)
    except PathError as exc:
        message = str(exc)
        if getattr(args, "path", None) == DEFAULT_PATH and not Path(DEFAULT_PATH).exists():
            message += f" (run this from the folder that holds {DEFAULT_PATH}/, or pass a path)"
        print(f"skillcheck: error: {message}", file=sys.stderr)
        return EXIT_USAGE


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


def _cmd_validate(args: argparse.Namespace) -> int:
    skills = load_all(Path(args.path))
    problems = validate_skills(skills, max_lines=args.max_lines, root=args.path)
    if args.json:
        payload = {
            "ok": not problems,
            "skills_checked": len(skills),
            "problems": [p.to_dict() for p in problems],
        }
        print(json.dumps(payload, indent=2))
    else:
        _print_problems(problems, len(skills))
    return EXIT_PROBLEMS if problems else EXIT_OK


def _print_problems(problems: list[Problem], checked: int) -> None:
    for problem in problems:
        print(problem)
    noun = "skill" if checked == 1 else "skills"
    if problems:
        count = "1 problem" if len(problems) == 1 else f"{len(problems)} problems"
        print(f"\nFAILED: {checked} {noun} checked, {count}")
    else:
        print(f"OK: {checked} {noun} checked, 0 problems")


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


def _shorten(text: str, width: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= width else text[: width - 3].rstrip() + "..."


def _cmd_list(args: argparse.Namespace) -> int:
    skills = load_all(Path(args.path))
    if not skills:
        print(f"skillcheck: no skills found in {args.path}", file=sys.stderr)
        return EXIT_PROBLEMS
    rows: list[tuple[str, str, str]] = []
    broken = False
    for skill in skills:
        name, desc, lines = _row(skill)
        broken = broken or desc.startswith("! ")
        rows.append((name, lines, desc if args.full else _shorten(desc, DESCRIPTION_WIDTH)))
    width = max(len("NAME"), *(len(r[0]) for r in rows))
    print(f"{'NAME':<{width}}  {'LINES':>5}  DESCRIPTION")
    for name, lines, desc in rows:
        print(f"{name:<{width}}  {lines:>5}  {desc}")
    noun = "skill" if len(rows) == 1 else "skills"
    print(f"\n{len(rows)} {noun}")
    return EXIT_PROBLEMS if broken else EXIT_OK


def _row(skill: Skill) -> tuple[str, str, str]:
    """(name, description, line count) for the table; unreadable skills show the reason."""
    name = skill.name or skill.folder_name
    if not skill.exists:
        return name, "! no SKILL.md in folder", "-"
    if skill.read_error:
        return name, f"! {skill.read_error}", "-"
    if skill.frontmatter_error is not None:
        return name, f"! invalid frontmatter: {skill.frontmatter_error.message}", "-"
    if not skill.description:
        return name, "! no description", str(skill.line_count)
    return name, skill.description, str(skill.line_count)


# ---------------------------------------------------------------------------
# new
# ---------------------------------------------------------------------------


def _cmd_new(args: argparse.Namespace) -> int:
    try:
        path = create(Path(args.path), args.name)
    except ValueError as exc:
        print(f"skillcheck: error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except OSError as exc:  # includes FileExistsError
        print(f"skillcheck: error: {exc}", file=sys.stderr)
        return EXIT_PROBLEMS
    print(f"Created {path}")
    print("Replace every TODO, then run: skillcheck validate")
    return EXIT_OK


# ---------------------------------------------------------------------------
# index
# ---------------------------------------------------------------------------


def _cmd_index(args: argparse.Namespace) -> int:
    to_stdout = args.output == "-"
    if to_stdout and args.check:
        print("skillcheck: error: --check needs a real output file, not -", file=sys.stderr)
        return EXIT_USAGE
    skills = load_all(Path(args.path))
    if not skills:
        print(f"skillcheck: no skills found in {args.path}", file=sys.stderr)
        return EXIT_PROBLEMS
    bad = [s for s in skills if not usable(s)]
    if bad:
        names = ", ".join(s.folder_name for s in bad)
        print(
            f"skillcheck: cannot index, these skills lack a name, description or Purpose: {names}\n"
            "Run `skillcheck validate` for details.",
            file=sys.stderr,
        )
        return EXIT_PROBLEMS
    out_path = Path.cwd() if to_stdout else Path(args.output)
    base = out_path if to_stdout else out_path.resolve().parent
    text = render_index(skills, base)
    if to_stdout:
        sys.stdout.write(text)
        return EXIT_OK
    if args.check:
        return _check_index(out_path, text)
    try:
        out_path.write_text(text, encoding="utf-8", newline="\n")
    except OSError as exc:
        print(f"skillcheck: error: cannot write {out_path}: {exc}", file=sys.stderr)
        return EXIT_PROBLEMS
    noun = "skill" if len(skills) == 1 else "skills"
    print(f"Wrote {out_path} ({len(skills)} {noun})")
    return EXIT_OK


def _check_index(out_path: Path, expected: str) -> int:
    try:
        current = out_path.read_bytes().decode("utf-8").replace("\r\n", "\n")
    except FileNotFoundError:
        print(f"{out_path} is missing; run: skillcheck index", file=sys.stderr)
        return EXIT_PROBLEMS
    except (OSError, UnicodeDecodeError) as exc:
        print(f"skillcheck: error: cannot read {out_path}: {exc}", file=sys.stderr)
        return EXIT_PROBLEMS
    if current != expected:
        print(f"{out_path} is out of date; run: skillcheck index", file=sys.stderr)
        return EXIT_PROBLEMS
    print(f"{out_path} is up to date")
    return EXIT_OK
