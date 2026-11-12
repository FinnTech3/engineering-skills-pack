from __future__ import annotations

from pathlib import Path

import pytest
from conftest import VALID_SKILL, codes, skill_text

from skillcheck.rules import (
    BANNED_PHRASES,
    MAX_DESCRIPTION_LENGTH,
    MAX_NAME_LENGTH,
    MAX_PURPOSE_LINE,
    MAX_REFERENCE_LINES,
    RULES,
    Problem,
    is_valid_name,
    validate_skill,
    validate_skills,
)
from skillcheck.skill import load_skill


def check(directory: Path, **kwargs) -> list[Problem]:
    return validate_skill(load_skill(directory), **kwargs)


def with_body(text: str, old: str, new: str) -> str:
    assert old in text, f"fixture does not contain {old!r}"
    return text.replace(old, new, 1)


class TestBaseline:
    def test_valid_skill_has_no_problems(self, make_skill):
        assert check(make_skill()) == []

    def test_problem_string_with_and_without_line(self):
        assert str(Problem("a/SKILL.md", 3, "banned-phrase", "msg")) == (
            "a/SKILL.md:3: banned-phrase: msg"
        )
        assert str(Problem("a", None, "no-skills", "msg")) == "a: no-skills: msg"

    def test_problem_to_dict(self):
        assert Problem("p", 2, "banned-phrase", "m").to_dict() == {
            "path": "p",
            "line": 2,
            "code": "banned-phrase",
            "message": "m",
        }

    def test_unknown_problem_code_is_rejected(self):
        with pytest.raises(ValueError, match="unknown problem code"):
            Problem("p", 1, "made-up-code", "m")

    def test_every_rule_is_described(self):
        assert RULES
        assert all(text and not text.endswith(".") for text in RULES.values())

    def test_skill_without_skill_file(self, root):
        (root / "empty").mkdir()
        problems = check(root / "empty")
        assert codes(problems) == ["skill-file-missing"]

    def test_unreadable_encoding(self, make_skill):
        directory = make_skill()
        (directory / "SKILL.md").write_bytes(b"---\nname: demo-skill\n---\n\xff\xfe\n")
        assert codes(check(directory)) == ["read-error"]


class TestFrontmatterRules:
    def test_missing_frontmatter(self, make_skill):
        directory = make_skill(text="# No frontmatter\n")
        problems = check(directory)
        assert codes(problems)[0] == "frontmatter-invalid"
        assert problems[0].line == 1

    def test_unclosed_frontmatter(self, make_skill):
        directory = make_skill(text="---\nname: demo-skill\n")
        assert "frontmatter-invalid" in codes(check(directory))

    def test_frontmatter_error_reports_line(self, make_skill):
        text = skill_text().replace("name: demo-skill", "name: demo-skill\nname: again")
        problems = check(make_skill(text=text))
        bad = next(p for p in problems if p.code == "frontmatter-invalid")
        assert bad.line == 3

    def test_name_missing(self, make_skill):
        text = skill_text().replace("name: demo-skill\n", "")
        assert "name-missing" in codes(check(make_skill(text=text, folder="demo-skill")))

    def test_name_empty(self, make_skill):
        text = skill_text().replace("name: demo-skill", "name:")
        assert "name-missing" in codes(check(make_skill(text=text, folder="demo-skill")))

    def test_description_missing(self, make_skill):
        start = VALID_SKILL.index("description:")
        end = VALID_SKILL.index("---\n\n# Demo")
        text = VALID_SKILL[:start] + VALID_SKILL[end:]
        assert "description-missing" in codes(check(make_skill(text=text)))

    def test_description_empty(self, make_skill):
        start = VALID_SKILL.index("description:")
        end = VALID_SKILL.index("---\n\n# Demo")
        text = VALID_SKILL[:start] + "description:\n" + VALID_SKILL[end:]
        assert "description-missing" in codes(check(make_skill(text=text)))

    @pytest.mark.parametrize("key", ["name", "description"])
    def test_non_string_value(self, make_skill, key):
        text = skill_text()
        if key == "name":
            text = text.replace("name: demo-skill", "name: [demo-skill]")
        else:
            text = text.replace("description: >", "description: [a, b]\nunused: >")
        problems = check(make_skill(text=text, folder="demo-skill"))
        assert any(p.code == "frontmatter-invalid" and key in p.message for p in problems)

    @pytest.mark.parametrize(
        "bad",
        ["Demo-Skill", "demo_skill", "demo--skill", "-demo", "demo-", "demo skill", "démo"],
    )
    def test_name_not_kebab(self, make_skill, bad):
        text = skill_text().replace("name: demo-skill", f'name: "{bad}"')
        problems = check(make_skill(text=text, folder="demo-skill"))
        assert "name-not-kebab" in codes(problems)

    def test_name_with_digits_is_fine(self, make_skill):
        assert check(make_skill("step-2-review")) == []

    def test_name_too_long(self, make_skill):
        long_name = "a" * (MAX_NAME_LENGTH + 1)
        assert "name-too-long" in codes(check(make_skill(long_name)))

    def test_name_at_limit_is_fine(self, make_skill):
        assert check(make_skill("a" * MAX_NAME_LENGTH)) == []

    def test_name_must_match_folder(self, make_skill):
        problems = check(make_skill("other-name", folder="demo-skill"))
        assert codes(problems) == ["name-mismatch"]
        assert "demo-skill" in problems[0].message

    def test_extra_frontmatter_keys_are_allowed(self, make_skill):
        text = skill_text().replace(
            "---\n\n# Demo", "license: MIT\nmetadata:\n  owner: team\ntags: [a]\n---\n\n# Demo", 1
        )
        assert check(make_skill(text=text)) == []

    def test_is_valid_name(self):
        assert is_valid_name("a-b-c")
        assert not is_valid_name("A")
        assert not is_valid_name("a" * 65)
        assert not is_valid_name("")


def with_description(text: str, description: str) -> str:
    start = text.index("description: >")
    end = text.index("---\n\n# Demo")
    return text[:start] + "description: >\n  " + description + "\n" + text[end:]


class TestDescriptionRules:
    def test_too_short(self, make_skill):
        text = with_description(VALID_SKILL, "Use when x. Not for y.")
        assert "description-too-short" in codes(check(make_skill(text=text)))

    def test_too_long(self, make_skill):
        filler = " ".join(["word"] * 120)
        text = with_description(VALID_SKILL, f"Use when {filler}. Do not use when done.")
        problems = check(make_skill(text=text))
        assert "description-too-long" in codes(problems)
        assert str(MAX_DESCRIPTION_LENGTH) in next(
            p.message for p in problems if p.code == "description-too-long"
        )

    def test_length_boundaries(self, make_skill):
        base = "Use when a. Do not use when b. "
        ok_min = base + "x" * (60 - len(base))
        assert check(make_skill(text=with_description(VALID_SKILL, ok_min))) == []
        ok_max = base + "x" * (MAX_DESCRIPTION_LENGTH - len(base))
        assert check(make_skill(text=with_description(VALID_SKILL, ok_max))) == []

    def test_missing_trigger_wording(self, make_skill):
        text = with_description(
            VALID_SKILL, "A demonstration skill for the validator tests. Not for real work."
        )
        assert codes(check(make_skill(text=text))) == ["description-no-trigger"]

    def test_missing_exclusion_wording(self, make_skill):
        text = with_description(
            VALID_SKILL, "Use when a demonstration skill is needed for the validator tests."
        )
        assert codes(check(make_skill(text=text))) == ["description-no-exclusion"]

    @pytest.mark.parametrize("phrase", ["Use when", "use this skill when", "USE WHEN"])
    def test_trigger_variants(self, make_skill, phrase):
        text = with_description(
            VALID_SKILL, f"{phrase} a demonstration is needed in tests. Do not use for real work."
        )
        assert check(make_skill(text=text)) == []

    @pytest.mark.parametrize("phrase", ["Do not use", "Don't use", "Not for", "Skip when"])
    def test_exclusion_variants(self, make_skill, phrase):
        text = with_description(
            VALID_SKILL, f"Use when a demonstration is needed in tests. {phrase} real work."
        )
        assert check(make_skill(text=text)) == []

    def test_literal_block_description_is_multiline(self, make_skill):
        text = VALID_SKILL.replace("description: >", "description: |")
        assert "description-multiline" in codes(check(make_skill(text=text)))

    def test_folded_description_is_single_line(self, make_skill):
        assert "description-multiline" not in codes(check(make_skill()))

    def test_description_line_is_reported(self, make_skill):
        text = with_description(VALID_SKILL, "short")
        problem = next(p for p in check(make_skill(text=text)) if p.code == "description-too-short")
        assert problem.line == 3


class TestSectionRules:
    @pytest.mark.parametrize(
        "section",
        [
            "Purpose",
            "Inputs needed",
            "Steps",
            "Output",
            "Exit criteria",
            "Failure modes",
            "When to stop and ask",
        ],
    )
    def test_each_required_section(self, make_skill, section):
        text = VALID_SKILL.replace(f"## {section}\n", f"## Renamed {section}\n")
        problems = check(make_skill(text=text))
        missing = [p for p in problems if p.code == "section-missing"]
        assert [p.message for p in missing] == [f"missing section '## {section}'"]

    def test_heading_match_ignores_case_and_colon(self, make_skill):
        text = VALID_SKILL.replace("## Exit criteria", "## exit   CRITERIA:")
        assert check(make_skill(text=text)) == []

    def test_extra_sections_are_allowed_anywhere(self, make_skill):
        text = VALID_SKILL.replace("## Steps", "## Background\n\nContext.\n\n## Steps")
        text += "\n## Notes\n\nMore.\n"
        assert check(make_skill(text=text)) == []

    def test_sections_out_of_order(self, make_skill):
        a = VALID_SKILL.index("## Exit criteria")
        b = VALID_SKILL.index("## Failure modes")
        c = VALID_SKILL.index("## When to stop")
        swapped = VALID_SKILL[:a] + VALID_SKILL[b:c] + VALID_SKILL[a:b] + VALID_SKILL[c:]
        problems = check(make_skill(text=swapped))
        assert codes(problems) == ["section-order"]

    def test_heading_inside_code_fence_does_not_count(self, make_skill):
        text = VALID_SKILL.replace("## Inputs needed", "```\n## Inputs needed\n```")
        assert "section-missing" in codes(check(make_skill(text=text)))

    def test_h3_is_not_a_section(self, make_skill):
        text = VALID_SKILL.replace("## Inputs needed", "### Inputs needed")
        assert "section-missing" in codes(check(make_skill(text=text)))

    def test_empty_section(self, make_skill):
        text = VALID_SKILL.replace("- A repository to inspect.\n", "")
        problems = check(make_skill(text=text))
        assert codes(problems) == ["section-empty"]

    def test_steps_must_be_numbered(self, make_skill):
        text = VALID_SKILL.replace("1. Read", "- Read").replace("2. Do", "- Do")
        problems = check(make_skill(text=text))
        assert codes(problems) == ["steps-not-numbered"]

    def test_steps_need_three_items(self, make_skill):
        text = VALID_SKILL.replace("3. Report the result.\n", "")
        assert codes(check(make_skill(text=text))) == ["steps-not-numbered"]

    def test_numbered_items_in_code_fence_do_not_count(self, make_skill):
        text = VALID_SKILL.replace(
            "2. Do the work.\n3. Report the result.\n", "```\n2. Do the work.\n3. Report.\n```\n"
        )
        assert codes(check(make_skill(text=text))) == ["steps-not-numbered"]

    def test_numbered_with_parenthesis_counts(self, make_skill):
        text = VALID_SKILL.replace("1. Read", "1) Read")
        assert check(make_skill(text=text)) == []

    @pytest.mark.parametrize(
        ("old", "section"),
        [
            ("- [ ] The report exists.\n- [ ] The work was checked.\n", "Exit criteria"),
            (
                "- **Skipped check.** The work was reported without being checked.\n",
                "Failure modes",
            ),
            ("- The request is ambiguous.\n", "When to stop and ask"),
        ],
    )
    def test_list_sections_need_list_items(self, make_skill, old, section):
        new = old.replace("- [ ] ", "").replace("- ", "")
        text = with_body(VALID_SKILL, old, new)
        problems = check(make_skill(text=text))
        assert codes(problems) == ["section-no-list"]
        assert section in problems[0].message

    def test_purpose_first_line_length(self, make_skill):
        long_line = "x" * (MAX_PURPOSE_LINE + 1)
        text = with_body(VALID_SKILL, "Show the smallest skill that passes every check.", long_line)
        assert codes(check(make_skill(text=text))) == ["purpose-too-long"]

    def test_purpose_later_lines_may_be_long(self, make_skill):
        text = with_body(VALID_SKILL, "Extra explanation", "y" * 300)
        assert check(make_skill(text=text)) == []


class TestLineLimit:
    def test_over_limit(self, make_skill):
        text = VALID_SKILL + "\n".join(f"- extra {i}" for i in range(130)) + "\n"
        problems = check(make_skill(text=text))
        over = [p for p in problems if p.code == "line-limit"]
        assert len(over) == 1
        assert over[0].line == 121

    def test_exactly_at_limit_passes(self, make_skill):
        base = VALID_SKILL.rstrip("\n").split("\n")
        padding = ["- pad"] * (120 - len(base))
        text = "\n".join(base + padding) + "\n"
        assert text.count("\n") == 120
        assert check(make_skill(text=text)) == []

    def test_custom_limit(self, make_skill):
        directory = make_skill()
        assert "line-limit" in codes(check(directory, max_lines=20))
        assert "line-limit" not in codes(check(directory, max_lines=60))

    def test_final_newline_is_not_counted(self, make_skill):
        text = VALID_SKILL.rstrip("\n") + "\n"
        lines = len(text.splitlines())
        assert "line-limit" not in codes(check(make_skill(text=text), max_lines=lines))
        assert "line-limit" in codes(check(make_skill(text=text), max_lines=lines - 1))


class TestWhitespace:
    def test_trailing_space(self, make_skill):
        text = VALID_SKILL.replace("1. Read the request.", "1. Read the request.  ")
        problems = check(make_skill(text=text))
        assert codes(problems) == ["trailing-whitespace"]
        assert problems[0].line == next(
            i for i, line in enumerate(text.split("\n"), 1) if line.endswith("request.  ")
        )

    def test_trailing_tab(self, make_skill):
        text = VALID_SKILL.replace("# Demo skill", "# Demo skill\t")
        assert codes(check(make_skill(text=text))) == ["trailing-whitespace"]

    def test_trailing_space_inside_code_fence_is_still_reported(self, make_skill):
        text = VALID_SKILL.replace("1. Read", "```\ncode   \n```\n1. Read")
        assert "trailing-whitespace" in codes(check(make_skill(text=text)))

    def test_trailing_space_in_frontmatter(self, make_skill):
        text = VALID_SKILL.replace("name: demo-skill", "name: demo-skill  ")
        assert "trailing-whitespace" in codes(check(make_skill(text=text)))

    def test_crlf_files_are_not_trailing_whitespace(self, make_skill):
        directory = make_skill()
        (directory / "SKILL.md").write_bytes(VALID_SKILL.replace("\n", "\r\n").encode())
        assert check(directory) == []


class TestBannedPhrases:
    @pytest.mark.parametrize("phrase", BANNED_PHRASES)
    def test_every_phrase_is_caught(self, make_skill, phrase):
        text = VALID_SKILL.replace("2. Do the work.", f"2. Do the work {phrase} today.")
        problems = [p for p in check(make_skill(text=text)) if p.code == "banned-phrase"]
        assert len(problems) == 1, phrase
        assert phrase in problems[0].message

    def test_case_insensitive(self, make_skill):
        text = VALID_SKILL.replace("2. Do the work.", "2. JUST do the work.")
        assert "banned-phrase" in codes(check(make_skill(text=text)))

    def test_whitespace_between_words_is_flexible(self, make_skill):
        text = VALID_SKILL.replace("2. Do the work.", "2. Do it as    needed.")
        assert "banned-phrase" in codes(check(make_skill(text=text)))

    def test_whole_words_only(self, make_skill):
        text = VALID_SKILL.replace(
            "2. Do the work.", "2. Justify the adjustment; just-in-time builds are not very-fast."
        )
        problems = [p for p in check(make_skill(text=text)) if p.code == "banned-phrase"]
        assert [p.message for p in problems if "'very'" in p.message] == []
        assert [p.message for p in problems if "'just'" in p.message] == []

    def test_paths_are_not_flagged(self, make_skill):
        text = VALID_SKILL.replace("2. Do the work.", "2. Read /etc/hosts for the host list.")
        assert check(make_skill(text=text)) == []

    def test_inline_code_is_ignored(self, make_skill):
        text = VALID_SKILL.replace("2. Do the work.", "2. Reject the word `just` in specs.")
        assert check(make_skill(text=text)) == []

    def test_fenced_code_is_ignored(self, make_skill):
        text = VALID_SKILL.replace("2. Do the work.", "2. Reject it:\n```\nsimply works\n```")
        assert check(make_skill(text=text)) == []

    def test_tilde_fence_is_ignored(self, make_skill):
        text = VALID_SKILL.replace("2. Do the work.", "2. Reject it:\n~~~\nsimply works\n~~~")
        assert check(make_skill(text=text)) == []

    def test_longer_closing_fence(self, make_skill):
        text = VALID_SKILL.replace("2. Do the work.", "2. Bad:\n```\nsimply\n````\n2. Do it.")
        assert check(make_skill(text=text)) == []

    def test_text_after_fence_is_checked_again(self, make_skill):
        text = VALID_SKILL.replace("2. Do the work.", "2. Ok:\n```\nx\n```\nsimply do it.")
        assert "banned-phrase" in codes(check(make_skill(text=text)))

    def test_frontmatter_is_checked(self, make_skill):
        text = VALID_SKILL.replace(
            "Use when a demonstration", "Use when a really good demonstration"
        )
        assert "banned-phrase" in codes(check(make_skill(text=text)))

    def test_reports_correct_line(self, make_skill):
        text = VALID_SKILL.replace("2. Do the work.", "2. Obviously do the work.")
        problem = next(p for p in check(make_skill(text=text)) if p.code == "banned-phrase")
        assert text.split("\n")[problem.line - 1] == "2. Obviously do the work."


class TestPlaceholders:
    @pytest.mark.parametrize("marker", ["TODO", "FIXME", "TBD"])
    def test_markers(self, make_skill, marker):
        text = VALID_SKILL.replace("2. Do the work.", f"2. {marker}: do the work.")
        assert codes(check(make_skill(text=text))) == ["todo-placeholder"]

    def test_lowercase_word_is_fine(self, make_skill):
        text = VALID_SKILL.replace("2. Do the work.", "2. Write the todo list.")
        assert check(make_skill(text=text)) == []

    def test_marker_in_code_is_fine(self, make_skill):
        text = VALID_SKILL.replace("2. Do the work.", "2. Search for `TODO` markers.")
        assert check(make_skill(text=text)) == []


class TestLinks:
    def test_existing_relative_link(self, make_skill):
        directory = make_skill()
        (directory / "references").mkdir()
        (directory / "references" / "notes.md").write_text("# Notes\n")
        text = VALID_SKILL.replace(
            "- A repository", "- See [notes](references/notes.md).\n- A repository"
        )
        (directory / "SKILL.md").write_text(text)
        assert check(directory) == []

    def test_broken_link(self, make_skill):
        text = VALID_SKILL.replace(
            "- A repository", "- See [notes](references/missing.md).\n- A repository"
        )
        problems = check(make_skill(text=text))
        assert codes(problems) == ["broken-link"]
        assert "references/missing.md" in problems[0].message

    def test_link_with_fragment_checks_the_file(self, make_skill):
        directory = make_skill()
        (directory / "extra.md").write_text("# Extra\n")
        text = VALID_SKILL.replace(
            "- A repository", "- [a](extra.md#top) [b](gone.md#top)\n- A repository"
        )
        (directory / "SKILL.md").write_text(text)
        problems = check(directory)
        assert [p.code for p in problems] == ["broken-link"]
        assert "gone.md" in problems[0].message

    def test_percent_encoded_target(self, make_skill):
        directory = make_skill()
        (directory / "my notes.md").write_text("# Notes\n")
        text = VALID_SKILL.replace("- A repository", "- [n](my%20notes.md)\n- A repository")
        (directory / "SKILL.md").write_text(text)
        assert check(directory) == []

    def test_link_to_directory_is_fine(self, make_skill):
        directory = make_skill()
        (directory / "scripts").mkdir()
        text = VALID_SKILL.replace("- A repository", "- [s](scripts/)\n- A repository")
        (directory / "SKILL.md").write_text(text)
        assert check(directory) == []

    @pytest.mark.parametrize(
        "target",
        ["https://example.com/x", "http://example.com", "mailto:a@b.c", "#anchor", "ftp://h/f"],
    )
    def test_external_and_anchor_links_are_ignored(self, make_skill, target):
        text = VALID_SKILL.replace("- A repository", f"- [x]({target})\n- A repository")
        assert check(make_skill(text=text)) == []

    def test_link_escaping_the_skill_folder(self, make_skill, root):
        (root / "shared.md").write_text("# Shared\n")
        text = VALID_SKILL.replace("- A repository", "- [x](../shared.md)\n- A repository")
        problems = check(make_skill(text=text))
        assert codes(problems) == ["link-escapes-skill"]

    def test_escaping_link_that_does_not_exist_reports_escape_once(self, make_skill):
        text = VALID_SKILL.replace("- A repository", "- [x](../../nope.md)\n- A repository")
        assert codes(check(make_skill(text=text))) == ["link-escapes-skill"]

    def test_absolute_path_escapes(self, make_skill):
        text = VALID_SKILL.replace("- A repository", "- [x](/etc/hosts)\n- A repository")
        assert codes(check(make_skill(text=text))) == ["link-escapes-skill"]

    def test_links_in_code_are_ignored(self, make_skill):
        text = VALID_SKILL.replace(
            "- A repository",
            "- Write `[x](nope.md)` like this.\n```\n[y](nope.md)\n```\n- A repository",
        )
        assert check(make_skill(text=text)) == []

    def test_image_link_is_checked(self, make_skill):
        text = VALID_SKILL.replace("- A repository", "- ![d](img/diagram.png)\n- A repository")
        assert codes(check(make_skill(text=text))) == ["broken-link"]

    def test_link_with_title(self, make_skill):
        text = VALID_SKILL.replace("- A repository", '- [x](nope.md "Title")\n- A repository')
        assert codes(check(make_skill(text=text))) == ["broken-link"]

    def test_reference_style_definition(self, make_skill):
        text = VALID_SKILL + "\n[ref]: nope.md\n"
        assert codes(check(make_skill(text=text))) == ["broken-link"]

    def test_two_links_on_one_line(self, make_skill):
        text = VALID_SKILL.replace("- A repository", "- [a](x.md) and [b](y.md)\n- A repository")
        assert codes(check(make_skill(text=text))) == ["broken-link", "broken-link"]

    def test_link_line_number(self, make_skill):
        text = VALID_SKILL.replace("- A repository", "- [a](x.md)\n- A repository")
        problem = check(make_skill(text=text))[0]
        assert text.split("\n")[problem.line - 1] == "- [a](x.md)"


class TestReferenceFiles:
    def linked(self, directory: Path, name: str = "references/notes.md", body: str = "# Notes\n"):
        target = directory / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body)
        text = (directory / "SKILL.md").read_text()
        text = text.replace("- A repository", f"- See [notes]({name}).\n- A repository")
        (directory / "SKILL.md").write_text(text)
        return target

    def test_linked_reference_passes(self, make_skill):
        directory = make_skill()
        self.linked(directory)
        assert check(directory) == []

    def test_orphan_reference(self, make_skill):
        directory = make_skill()
        (directory / "references").mkdir()
        (directory / "references" / "lonely.md").write_text("# Lonely\n")
        problems = check(directory)
        assert codes(problems) == ["orphan-reference"]
        assert problems[0].path.endswith("lonely.md")

    def test_reference_trailing_whitespace(self, make_skill):
        directory = make_skill()
        self.linked(directory, body="# Notes  \n")
        problems = check(directory)
        assert codes(problems) == ["trailing-whitespace"]
        assert problems[0].path.endswith("notes.md")

    def test_reference_banned_phrase(self, make_skill):
        directory = make_skill()
        self.linked(directory, body="# Notes\n\nIt is simply done.\n")
        assert codes(check(directory)) == ["banned-phrase"]

    def test_reference_broken_link(self, make_skill):
        directory = make_skill()
        self.linked(directory, body="# Notes\n\n[x](missing.md)\n")
        assert codes(check(directory)) == ["broken-link"]

    def test_reference_may_link_to_sibling(self, make_skill):
        directory = make_skill()
        self.linked(directory, body="# Notes\n\n[skill](../SKILL.md)\n")
        assert check(directory) == []

    def test_reference_line_limit(self, make_skill):
        directory = make_skill()
        body = "# Notes\n" + "line\n" * MAX_REFERENCE_LINES
        self.linked(directory, body=body)
        assert codes(check(directory)) == ["line-limit"]

    def test_reference_unreadable(self, make_skill):
        directory = make_skill()
        target = self.linked(directory)
        target.write_bytes(b"\xff\xfe")
        assert codes(check(directory)) == ["read-error"]

    def test_hidden_directories_are_skipped(self, make_skill):
        directory = make_skill()
        (directory / ".cache").mkdir()
        (directory / ".cache" / "junk.md").write_text("simply  \n")
        assert check(directory) == []

    def test_non_markdown_files_are_ignored(self, make_skill):
        directory = make_skill()
        (directory / "script.sh").write_text("echo simply  \n")
        assert check(directory) == []


class TestTree:
    def test_empty_tree(self):
        problems = validate_skills([], root="skills")
        assert codes(problems) == ["no-skills"]
        assert problems[0].path == "skills"

    def test_duplicate_names(self, make_skill, root):
        make_skill("shared-name", folder="aaa")
        make_skill("shared-name", folder="shared-name")
        skills = [load_skill(root / "aaa"), load_skill(root / "shared-name")]
        problems = validate_skills(skills)
        dup = [p for p in problems if p.code == "duplicate-name"]
        assert len(dup) == 1
        assert dup[0].path.replace("\\", "/").endswith("shared-name/SKILL.md")
        assert "aaa" in dup[0].message
        assert dup[0].line == 2

    def test_duplicate_names_are_case_insensitive(self, make_skill, root):
        make_skill("demo-skill", folder="aaa")
        make_skill("Demo-Skill", folder="bbb")
        problems = validate_skills([load_skill(root / "aaa"), load_skill(root / "bbb")])
        assert "duplicate-name" in codes(problems)

    def test_distinct_names_pass(self, make_skill, root):
        make_skill("alpha-one")
        make_skill("beta-two")
        assert (
            validate_skills([load_skill(root / "alpha-one"), load_skill(root / "beta-two")]) == []
        )

    def test_problems_are_sorted_by_path_then_line(self, make_skill, root):
        make_skill("beta-two", text=VALID_SKILL.replace("demo-skill", "beta-two") + "x  \n")
        make_skill("alpha-one", text=VALID_SKILL.replace("demo-skill", "alpha-one") + "y  \n")
        problems = validate_skills([load_skill(root / "beta-two"), load_skill(root / "alpha-one")])
        assert [Path(p.path).parent.name for p in problems] == ["alpha-one", "beta-two"]

    def test_max_lines_is_passed_through(self, make_skill, root):
        make_skill("alpha-one")
        problems = validate_skills([load_skill(root / "alpha-one")], max_lines=10)
        assert "line-limit" in codes(problems)


def test_a_line_of_unclosed_brackets_cannot_stall_the_link_check(make_skill):
    import time

    text = skill_text() + "\n" + "[" * 60_000 + "\n"
    directory = make_skill(text=text)
    start = time.monotonic()
    check(directory)
    assert time.monotonic() - start < 5
