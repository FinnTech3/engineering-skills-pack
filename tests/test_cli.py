from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import VALID_SKILL, skill_text

from skillcheck import __version__

SRC = Path(__file__).resolve().parents[1] / "src"


class TestValidate:
    def test_ok(self, make_skill, root, run):
        make_skill("alpha-one")
        make_skill("beta-two")
        code, out, err = run("validate", root)
        assert code == 0
        assert out.strip() == "OK: 2 skills checked, 0 problems"
        assert err == ""

    def test_singular(self, make_skill, run):
        code, out, _ = run("validate", make_skill())
        assert code == 0
        assert out.strip() == "OK: 1 skill checked, 0 problems"

    def test_problems_exit_1(self, make_skill, root, run):
        make_skill(text=VALID_SKILL.replace("1. Read the request.", "1. Read it.  "))
        code, out, _ = run("validate", root)
        assert code == 1
        assert "trailing-whitespace" in out
        assert "SKILL.md:" in out
        assert out.strip().endswith("FAILED: 1 skill checked, 1 problem")

    def test_plural_problems(self, make_skill, root, run):
        make_skill(text=VALID_SKILL.replace("2. Do the work.", "2. Just do the work.  "))
        code, out, _ = run("validate", root)
        assert code == 1
        assert "2 problems" in out

    def test_json_ok(self, make_skill, root, run):
        make_skill()
        code, out, _ = run("validate", root, "--json")
        assert code == 0
        assert json.loads(out) == {"ok": True, "skills_checked": 1, "problems": []}

    def test_json_problems(self, make_skill, root, run):
        make_skill(text=VALID_SKILL.replace("2. Do the work.", "2. Just do the work."))
        code, out, _ = run("validate", root, "--json")
        payload = json.loads(out)
        assert code == 1
        assert payload["ok"] is False
        assert payload["skills_checked"] == 1
        (problem,) = payload["problems"]
        assert problem["code"] == "banned-phrase"
        assert problem["path"].replace("\\", "/").endswith("demo-skill/SKILL.md")
        assert isinstance(problem["line"], int)
        assert set(problem) == {"path", "line", "code", "message"}

    def test_json_null_line_for_file_level_problems(self, root, run):
        (root / "empty-folder").mkdir()
        code, out, _ = run("validate", root, "--json")
        assert code == 1
        assert json.loads(out)["problems"][0]["line"] is None

    def test_json_is_stable_across_runs(self, make_skill, root, run):
        make_skill(text=VALID_SKILL + "x  \n")
        first = run("validate", root, "--json")[1]
        second = run("validate", root, "--json")[1]
        assert first == second

    def test_single_skill_folder_and_file(self, make_skill, run):
        directory = make_skill()
        assert run("validate", directory)[0] == 0
        assert run("validate", directory / "SKILL.md")[0] == 0

    def test_folder_without_skill_file(self, root, run):
        (root / "oops").mkdir()
        code, out, _ = run("validate", root)
        assert code == 1
        assert "skill-file-missing" in out

    def test_empty_root_is_a_problem(self, root, run):
        code, out, _ = run("validate", root)
        assert code == 1
        assert "no-skills" in out

    def test_duplicate_names_across_folders(self, make_skill, root, run):
        make_skill("one-skill", folder="aaa-one")
        make_skill("one-skill", folder="one-skill")
        code, out, _ = run("validate", root)
        assert code == 1
        assert "duplicate-name" in out

    def test_max_lines_option(self, make_skill, root, run):
        make_skill()
        assert run("validate", root, "--max-lines", "200")[0] == 0
        code, out, _ = run("validate", root, "--max-lines", "10")
        assert code == 1
        assert "line-limit" in out

    @pytest.mark.parametrize("value", ["0", "-3", "abc", "1.5"])
    def test_bad_max_lines_is_usage_error(self, make_skill, root, run, value):
        make_skill()
        code, _, err = run("validate", root, "--max-lines", value)
        assert code == 2
        assert "max-lines" in err

    def test_missing_path_is_usage_error(self, tmp_path, run):
        code, out, err = run("validate", tmp_path / "nope")
        assert code == 2
        assert "does not exist" in err
        assert out == ""

    def test_missing_default_path_says_where_to_run_it(self, tmp_path, run, monkeypatch):
        monkeypatch.chdir(tmp_path)
        code, out, err = run("validate")
        assert code == 2
        assert "path does not exist: skills" in err
        assert "run this from the folder that holds skills/" in err
        assert out == ""

    def test_missing_explicit_path_gets_no_hint(self, tmp_path, run, monkeypatch):
        monkeypatch.chdir(tmp_path)
        code, _, err = run("validate", "elsewhere")
        assert code == 2
        assert "run this from" not in err

    def test_file_that_is_not_skill_md_is_usage_error(self, tmp_path, run):
        other = tmp_path / "README.md"
        other.write_text("x")
        code, _, err = run("validate", other)
        assert code == 2
        assert "SKILL.md" in err

    def test_default_path_is_skills_in_cwd(self, make_skill, tmp_path, run, monkeypatch):
        make_skill()
        monkeypatch.chdir(tmp_path)
        assert run("validate")[0] == 0

    def test_default_path_missing_is_usage_error(self, tmp_path, run, monkeypatch):
        monkeypatch.chdir(tmp_path)
        code, _, err = run("validate")
        assert code == 2
        assert "skills" in err


class TestList:
    def test_table(self, make_skill, root, run):
        make_skill("alpha-one")
        make_skill("beta-two-longer-name")
        code, out, _ = run("list", root)
        assert code == 0
        rows = out.splitlines()
        assert rows[0].split() == ["NAME", "LINES", "DESCRIPTION"]
        assert rows[1].startswith("alpha-one")
        assert rows[2].startswith("beta-two-longer-name")
        assert "Use when a demonstration" in rows[1]
        assert out.strip().endswith("2 skills")
        # columns line up on the widest name
        assert rows[1].index("Use when") == rows[2].index("Use when")

    def test_line_count_column(self, make_skill, root, run):
        make_skill()
        rows = run("list", root)[1].splitlines()
        expected = len(VALID_SKILL.splitlines())
        assert rows[1].split()[1] == str(expected)

    def test_long_descriptions_are_shortened(self, make_skill, root, run):
        make_skill()
        out = run("list", root)[1]
        line = out.splitlines()[1]
        assert line.rstrip().endswith("...")
        assert "real engineering work" not in out

    def test_full_option(self, make_skill, root, run):
        make_skill()
        out = run("list", root, "--full")[1]
        assert "Do not use when real engineering work is being done." in out
        assert "..." not in out

    def test_singular(self, make_skill, run):
        out = run("list", make_skill())[1]
        assert out.strip().endswith("1 skill")

    def test_empty_root(self, root, run):
        code, out, err = run("list", root)
        assert code == 1
        assert out == ""
        assert "no skills found" in err

    def test_broken_skills_are_shown_and_fail(self, make_skill, root, run):
        make_skill("good-one")
        make_skill("bad-one", text="no frontmatter\n")
        (root / "empty-one").mkdir()
        code, out, _ = run("list", root)
        assert code == 1
        assert "bad-one" in out
        assert "! invalid frontmatter" in out
        assert "! no SKILL.md in folder" in out
        assert "good-one" in out

    def test_skill_without_description(self, make_skill, root, run):
        make_skill(text="---\nname: demo-skill\n---\n# x\n")
        code, out, _ = run("list", root)
        assert code == 1
        assert "! no description" in out

    def test_unreadable_skill(self, make_skill, root, run):
        directory = make_skill()
        (directory / "SKILL.md").write_bytes(b"\xff\xfe")
        code, out, _ = run("list", root)
        assert code == 1
        assert "! cannot read file" in out

    def test_missing_path(self, tmp_path, run):
        assert run("list", tmp_path / "nope")[0] == 2


class TestNew:
    def test_creates_skeleton(self, root, run):
        code, out, _ = run("new", "plan-the-thing", "--path", root)
        target = root / "plan-the-thing" / "SKILL.md"
        assert code == 0
        assert target.is_file()
        assert str(target) in out
        text = target.read_text()
        assert text.startswith("---\nname: plan-the-thing\n")
        assert "# Plan the thing" in text

    def test_default_path_is_skills_in_cwd(self, tmp_path, run, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert run("new", "my-skill")[0] == 0
        assert (tmp_path / "skills" / "my-skill" / "SKILL.md").is_file()

    def test_creates_missing_root(self, tmp_path, run):
        assert run("new", "my-skill", "--path", tmp_path / "deep" / "er")[0] == 0
        assert (tmp_path / "deep" / "er" / "my-skill" / "SKILL.md").is_file()

    @pytest.mark.parametrize(
        "bad", ["Bad-Name", "has_underscore", "two--hyphens", "trail-", "a b", ""]
    )
    def test_invalid_name_is_usage_error(self, root, run, bad):
        code, _, err = run("new", bad, "--path", root)
        assert code == 2
        assert "invalid skill name" in err
        assert list(root.iterdir()) == []

    def test_name_starting_with_hyphen(self, root, run):
        code, _, err = run("new", "--path", root, "--", "-lead")
        assert code == 2
        assert "invalid skill name" in err

    def test_too_long_name(self, root, run):
        assert run("new", "a" * 65, "--path", root)[0] == 2

    def test_existing_folder_is_not_overwritten(self, make_skill, root, run):
        directory = make_skill("taken-name")
        before = (directory / "SKILL.md").read_text()
        code, _, err = run("new", "taken-name", "--path", root)
        assert code == 1
        assert "already exists" in err
        assert (directory / "SKILL.md").read_text() == before

    def test_scaffold_is_structurally_valid_but_fails_on_todos(self, root, run):
        run("new", "fresh-skill", "--path", root)
        code, out, _ = run("validate", root, "--json")
        problems = json.loads(out)["problems"]
        assert code == 1
        assert {p["code"] for p in problems} == {"todo-placeholder"}
        assert len(problems) >= 8

    def test_filled_in_scaffold_passes(self, root, run):
        run("new", "fresh-skill", "--path", root)
        path = root / "fresh-skill" / "SKILL.md"
        text = path.read_text().replace("TODO: ", "").replace("TODO", "Work")
        path.write_text(text)
        code, out, _ = run("validate", root)
        assert code == 0, out

    def test_scaffold_has_no_trailing_whitespace_and_ends_with_newline(self, root, run):
        run("new", "fresh-skill", "--path", root)
        text = (root / "fresh-skill" / "SKILL.md").read_text()
        assert text.endswith("\n")
        assert all(line == line.rstrip() for line in text.split("\n"))

    def test_unwritable_target(self, tmp_path, run):
        blocker = tmp_path / "file-not-dir"
        blocker.write_text("x")
        code, _, err = run("new", "my-skill", "--path", blocker)
        assert code == 1
        assert "error" in err


class TestIndex:
    def test_writes_file(self, make_skill, root, tmp_path, run, monkeypatch):
        make_skill("alpha-one")
        make_skill("beta-two")
        monkeypatch.chdir(tmp_path)
        code, out, _ = run("index", root)
        assert code == 0
        assert "Wrote" in out
        assert "2 skills" in out
        text = (tmp_path / "INDEX.md").read_text()
        assert "| [`alpha-one`](skills/alpha-one/SKILL.md) | Show the smallest skill" in text
        assert text.index("alpha-one") < text.index("beta-two")

    def test_explicit_output_with_relative_links(self, make_skill, root, tmp_path, run):
        make_skill()
        out_file = tmp_path / "docs" / "index.md"
        out_file.parent.mkdir()
        assert run("index", root, "-o", out_file)[0] == 0
        assert "(../skills/demo-skill/SKILL.md)" in out_file.read_text()

    def test_stdout(self, make_skill, root, run, tmp_path, monkeypatch):
        make_skill()
        monkeypatch.chdir(tmp_path)
        code, out, _ = run("index", root, "-o", "-")
        assert code == 0
        assert out.startswith("# Skill index")
        assert not (tmp_path / "INDEX.md").exists()

    def test_check_passes_when_current(self, make_skill, root, tmp_path, run, monkeypatch):
        make_skill()
        monkeypatch.chdir(tmp_path)
        run("index", root)
        code, out, _ = run("index", root, "--check")
        assert code == 0
        assert "up to date" in out

    def test_check_fails_when_stale(self, make_skill, root, tmp_path, run, monkeypatch):
        make_skill()
        monkeypatch.chdir(tmp_path)
        run("index", root)
        make_skill("another-skill")
        code, _, err = run("index", root, "--check")
        assert code == 1
        assert "out of date" in err
        assert "skillcheck index" in err

    def test_check_does_not_write(self, make_skill, root, tmp_path, run, monkeypatch):
        make_skill()
        monkeypatch.chdir(tmp_path)
        (tmp_path / "INDEX.md").write_text("stale\n")
        assert run("index", root, "--check")[0] == 1
        assert (tmp_path / "INDEX.md").read_text() == "stale\n"

    def test_check_fails_when_missing(self, make_skill, root, tmp_path, run, monkeypatch):
        make_skill()
        monkeypatch.chdir(tmp_path)
        code, _, err = run("index", root, "--check")
        assert code == 1
        assert "missing" in err

    def test_check_tolerates_crlf(self, make_skill, root, tmp_path, run, monkeypatch):
        make_skill()
        monkeypatch.chdir(tmp_path)
        run("index", root)
        index = tmp_path / "INDEX.md"
        index.write_bytes(index.read_bytes().replace(b"\n", b"\r\n"))
        assert run("index", root, "--check")[0] == 0

    def test_check_with_stdout_is_usage_error(self, make_skill, root, run):
        make_skill()
        code, _, err = run("index", root, "--check", "-o", "-")
        assert code == 2
        assert "--check" in err

    def test_skills_that_cannot_be_indexed(self, make_skill, root, tmp_path, run, monkeypatch):
        make_skill("good-one")
        make_skill("bad-one", text="---\nname: bad-one\n---\n# x\n")
        monkeypatch.chdir(tmp_path)
        code, _, err = run("index", root)
        assert code == 1
        assert "bad-one" in err
        assert not (tmp_path / "INDEX.md").exists()

    def test_empty_root(self, root, run):
        code, _, err = run("index", root)
        assert code == 1
        assert "no skills found" in err

    def test_missing_path(self, tmp_path, run):
        assert run("index", tmp_path / "nope")[0] == 2

    def test_unwritable_output(self, make_skill, root, tmp_path, run):
        make_skill()
        code, _, err = run("index", root, "-o", tmp_path / "no-such-dir" / "INDEX.md")
        assert code == 1
        assert "cannot write" in err

    def test_unreadable_output_on_check(self, make_skill, root, tmp_path, run, monkeypatch):
        make_skill()
        monkeypatch.chdir(tmp_path)
        (tmp_path / "INDEX.md").write_bytes(b"\xff\xfe")
        code, _, err = run("index", root, "--check")
        assert code == 1
        assert "cannot read" in err


class TestUsage:
    def test_no_command(self, run):
        code, _, err = run()
        assert code == 2
        assert "command is required" in err

    def test_unknown_command(self, run):
        code, _, err = run("frobnicate")
        assert code == 2
        assert "invalid choice" in err

    def test_unknown_option(self, root, run):
        assert run("validate", root, "--nope")[0] == 2

    def test_new_without_name(self, run):
        assert run("new")[0] == 2

    def test_too_many_paths(self, root, run):
        assert run("validate", root, root)[0] == 2

    def test_help_exits_zero(self, run):
        code, out, _ = run("--help")
        assert code == 0
        assert "validate" in out
        assert "index" in out
        assert "Exit codes" in out

    def test_subcommand_help(self, run):
        code, out, _ = run("validate", "--help")
        assert code == 0
        assert "--json" in out

    def test_version(self, run):
        code, out, _ = run("--version")
        assert code == 0
        assert out.strip() == f"skillcheck {__version__}"


class TestProcess:
    """End to end through a real interpreter, to check exit codes and ``python -m``."""

    def run_module(self, *args: str | Path, cwd: Path) -> subprocess.CompletedProcess[str]:
        env = {**os.environ, "PYTHONPATH": str(SRC)}
        return subprocess.run(
            [sys.executable, "-m", "skillcheck", *map(str, args)],
            capture_output=True,
            text=True,
            cwd=cwd,
            env=env,
            check=False,
        )

    def test_exit_codes(self, make_skill, root, tmp_path):
        make_skill()
        assert self.run_module("validate", root, cwd=tmp_path).returncode == 0
        (root / "demo-skill" / "SKILL.md").write_text(skill_text() + "x  \n")
        assert self.run_module("validate", root, cwd=tmp_path).returncode == 1
        assert self.run_module("validate", "--bogus", cwd=tmp_path).returncode == 2
        assert self.run_module("validate", tmp_path / "missing", cwd=tmp_path).returncode == 2

    def test_json_goes_to_stdout_only(self, make_skill, root, tmp_path):
        make_skill()
        result = self.run_module("validate", root, "--json", cwd=tmp_path)
        assert json.loads(result.stdout)["ok"] is True
        assert result.stderr == ""

    def test_non_ascii_names_do_not_crash_on_ascii_terminals(self, make_skill, root, tmp_path):
        make_skill(text=skill_text().replace("name: demo-skill", "name: d\u00e9mo"), folder="demo")
        env = {**os.environ, "PYTHONPATH": str(SRC), "PYTHONIOENCODING": "ascii"}
        result = subprocess.run(
            [sys.executable, "-m", "skillcheck", "validate", str(root)],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            env=env,
            check=False,
        )
        assert result.returncode == 1
        assert "d\\xe9mo" in result.stdout
        assert "Traceback" not in result.stderr
