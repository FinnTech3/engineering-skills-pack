from __future__ import annotations

import pytest
from conftest import skill_text

from skillcheck.skill import (
    PathError,
    discover,
    fence_mask,
    load_all,
    load_skill,
    normalize_heading,
    split_sections,
)


class TestDiscover:
    def test_skills_root_lists_folders_sorted(self, make_skill, root):
        make_skill("zeta-skill")
        make_skill("alpha-skill")
        assert [p.name for p in discover(root)] == ["alpha-skill", "zeta-skill"]

    def test_single_skill_folder(self, make_skill):
        directory = make_skill()
        assert discover(directory) == [directory]

    def test_skill_file(self, make_skill):
        directory = make_skill()
        assert discover(directory / "SKILL.md") == [directory]

    def test_other_file_is_rejected(self, root):
        (root / "README.md").write_text("x")
        with pytest.raises(PathError, match=r"SKILL\.md"):
            discover(root / "README.md")

    def test_missing_path(self, tmp_path):
        with pytest.raises(PathError, match="does not exist"):
            discover(tmp_path / "nope")

    def test_hidden_and_underscore_folders_are_ignored(self, make_skill, root):
        make_skill("real-skill")
        (root / ".git").mkdir()
        (root / "_drafts").mkdir()
        assert [p.name for p in discover(root)] == ["real-skill"]

    def test_plain_files_in_root_are_ignored(self, make_skill, root):
        make_skill("real-skill")
        (root / "notes.txt").write_text("x")
        assert [p.name for p in discover(root)] == ["real-skill"]

    def test_folder_without_skill_file_is_still_returned(self, root):
        (root / "no-skill-here").mkdir()
        assert [p.name for p in discover(root)] == ["no-skill-here"]

    def test_only_one_level_deep(self, make_skill, root):
        nested = root / "group" / "inner-skill"
        nested.mkdir(parents=True)
        (nested / "SKILL.md").write_text(skill_text("inner-skill"))
        assert [p.name for p in discover(root)] == ["group"]

    def test_empty_root(self, root):
        assert discover(root) == []
        assert load_all(root) == []


class TestLoadSkill:
    def test_fields(self, make_skill):
        skill = load_skill(make_skill())
        assert skill.name == "demo-skill"
        assert skill.description.startswith("Use when a demonstration")
        assert skill.summary == "Show the smallest skill that passes every check."
        assert skill.folder_name == "demo-skill"
        assert [s.key for s in skill.sections] == [
            "purpose",
            "inputs needed",
            "steps",
            "output",
            "exit criteria",
            "failure modes",
            "when to stop and ask",
        ]

    def test_line_count_ignores_final_newline(self, make_skill):
        skill = load_skill(make_skill(text="---\nname: a\n---\nx\n"))
        assert skill.line_count == 4

    def test_line_count_without_final_newline(self, make_skill):
        skill = load_skill(make_skill(text="---\nname: a\n---\nx"))
        assert skill.line_count == 4

    def test_missing_file(self, root):
        (root / "x").mkdir()
        skill = load_skill(root / "x")
        assert not skill.exists
        assert skill.name == ""
        assert skill.line_count == 0

    def test_frontmatter_error_is_recorded(self, make_skill):
        skill = load_skill(make_skill(text="no frontmatter\n"))
        assert skill.frontmatter is None
        assert skill.frontmatter_error is not None
        assert skill.sections == []

    def test_unreadable_file_is_recorded(self, make_skill):
        directory = make_skill()
        (directory / "SKILL.md").write_bytes(b"\xff\xfe\x00")
        assert load_skill(directory).read_error

    def test_summary_without_purpose(self, make_skill):
        text = skill_text().replace("## Purpose", "## Aim")
        assert load_skill(make_skill(text=text)).summary == ""

    def test_summary_with_empty_purpose(self, make_skill):
        text = skill_text().replace(
            "Show the smallest skill that passes every check.\n"
            "Extra explanation can follow on later lines.\n",
            "",
        )
        assert load_skill(make_skill(text=text)).summary == ""

    def test_headings_inside_frontmatter_comments_are_not_sections(self, make_skill):
        text = skill_text().replace("---\n\n# Demo", "# ## Purpose\n---\n\n# Demo", 1)
        skill = load_skill(make_skill(text=text))
        assert [s.key for s in skill.sections].count("purpose") == 1


class TestMarkdownHelpers:
    def test_normalize_heading(self):
        assert normalize_heading("  Exit   Criteria: ") == "exit criteria"

    def test_fence_mask_marks_fences_and_content(self):
        lines = ["a", "```py", "b", "```", "c"]
        assert fence_mask(lines) == [False, True, True, True, False]

    def test_fence_mask_unclosed_fence_runs_to_the_end(self):
        assert fence_mask(["a", "```", "b", "c"]) == [False, True, True, True]

    def test_fence_mask_shorter_closer_does_not_close(self):
        assert fence_mask(["````", "x", "```", "y", "````", "z"]) == [True] * 5 + [False]

    def test_fence_mask_different_char_does_not_close(self):
        assert fence_mask(["```", "x", "~~~", "y", "```", "z"]) == [True] * 5 + [False]

    def test_indented_fence_inside_a_list_item(self):
        lines = ["1. step", "    ```", "    code", "    ```", "2. next"]
        assert fence_mask(lines) == [False, True, True, True, False]

    def test_fence_with_info_string_does_not_close_another(self):
        assert fence_mask(["```", "```py", "x", "```", "z"]) == [True, True, True, True, False]

    def test_split_sections_bodies(self):
        lines = ["# T", "## One", "a", "", "## Two", "- x", "1. y"]
        sections = split_sections(lines, fence_mask(lines))
        assert [s.title for s in sections] == ["One", "Two"]
        assert sections[0].line == 2
        assert [t for _, t in sections[0].content()] == ["a"]
        assert [t for _, t in sections[1].list_items()] == ["- x", "1. y"]
        assert [t for _, t in sections[1].numbered_items()] == ["1. y"]
