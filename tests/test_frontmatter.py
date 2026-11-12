from __future__ import annotations

import pytest

from skillcheck.frontmatter import FrontmatterError, parse, split_lines


def fm(*lines: str) -> str:
    return "\n".join(["---", *lines, "---", "body", ""])


def data(*lines: str) -> dict:
    return parse(fm(*lines)).data


class TestScalars:
    def test_plain(self):
        assert data("name: demo", "description: hello world") == {
            "name": "demo",
            "description": "hello world",
        }

    def test_empty_value(self):
        assert data("name:", "other: x") == {"name": "", "other": "x"}

    def test_plain_keeps_inner_hash_and_colon_without_space(self):
        assert data("a: v#1", "b: http://x.y/z")["b"] == "http://x.y/z"
        assert data("a: v#1")["a"] == "v#1"

    def test_inline_comment_is_stripped(self):
        assert data("name: demo  # the name") == {"name": "demo"}

    def test_comment_only_value_is_empty(self):
        assert data("name: # nothing here") == {"name": ""}

    def test_full_line_comments_and_blank_lines_are_skipped(self):
        assert data("# top", "", "name: demo", "  # indented comment", "") == {"name": "demo"}

    def test_values_are_never_coerced(self):
        assert data("a: 12", "b: true", "c: null") == {"a": "12", "b": "true", "c": "null"}

    def test_dotted_and_dashed_keys(self):
        assert data("allowed-tools: x", "meta.v: y") == {"allowed-tools": "x", "meta.v": "y"}


class TestQuoted:
    def test_single_quotes_with_escape(self):
        assert data("a: 'it''s fine'")["a"] == "it's fine"

    def test_double_quotes_with_escapes(self):
        assert data(r'a: "tab\there \"q\" \\ \n end"')["a"] == 'tab\there "q" \\ \n end'

    def test_unicode_and_hex_escapes(self):
        assert data(r'a: "é\x41"')["a"] == "éA"

    def test_quoted_value_may_contain_colon_space(self):
        assert data('a: "Use when: x"')["a"] == "Use when: x"

    def test_quoted_value_with_trailing_comment(self):
        assert data('a: "x" # note')["a"] == "x"

    def test_multi_line_double_quoted_is_folded(self):
        assert data('a: "one', "  two", '  three"')["a"] == "one two three"

    def test_multi_line_single_quoted_blank_line_is_newline(self):
        assert data("a: 'one", "", "  two'")["a"] == "one\ntwo"

    def test_quoted_followed_by_next_key(self):
        assert data("a: 'x'", "b: y") == {"a": "x", "b": "y"}

    def test_unterminated_quote(self):
        with pytest.raises(FrontmatterError, match="unterminated"):
            parse(fm('a: "never closed'))

    def test_text_after_closing_quote(self):
        with pytest.raises(FrontmatterError, match="after closing quote"):
            parse(fm('a: "x" y'))

    def test_unknown_escape(self):
        with pytest.raises(FrontmatterError, match="unknown escape"):
            parse(fm(r'a: "\q"'))

    def test_bad_unicode_escape(self):
        with pytest.raises(FrontmatterError, match="invalid"):
            parse(fm(r'a: "\u12"'))


class TestBlockScalars:
    def test_folded_joins_lines_with_spaces(self):
        d = data("description: >", "  one", "  two", "  three")
        assert d["description"] == "one two three\n"

    def test_folded_strip_drops_final_newline(self):
        assert data("description: >-", "  one", "  two")["description"] == "one two"

    def test_folded_blank_line_makes_a_newline(self):
        d = data("description: >-", "  first", "  line", "", "  second")
        assert d["description"] == "first line\nsecond"

    def test_folded_more_indented_lines_keep_breaks(self):
        d = data("description: >-", "  intro", "    code", "  outro")
        assert d["description"] == "intro\n  code\noutro"

    def test_folded_keep_preserves_trailing_blank_lines(self):
        d = data("description: >+", "  one", "", "", "next: v")
        assert d["description"] == "one\n\n\n"
        assert d["next"] == "v"

    def test_literal_keeps_line_breaks(self):
        d = data("description: |", "  one", "  two")
        assert d["description"] == "one\ntwo\n"

    def test_literal_strip(self):
        assert data("description: |-", "  one", "  two")["description"] == "one\ntwo"

    def test_block_scalar_stops_at_next_key(self):
        d = data("description: >", "  text", "name: demo")
        assert d == {"description": "text\n", "name": "demo"}

    def test_block_scalar_with_comment_after_indicator(self):
        assert data("description: > # note", "  text")["description"] == "text\n"

    def test_empty_block_scalar(self):
        assert data("description: >", "name: x") == {"description": "", "name": "x"}

    def test_inner_colon_and_hash_are_literal_text(self):
        d = data("description: >-", "  Use when: a # not a comment")
        assert d["description"] == "Use when: a # not a comment"

    def test_explicit_indentation_indicator_is_rejected(self):
        with pytest.raises(FrontmatterError, match="explicit indentation"):
            parse(fm("description: >2", "   text"))

    def test_first_line_must_have_smallest_indent(self):
        with pytest.raises(FrontmatterError, match="smallest indentation"):
            parse(fm("description: >", "    deep", "  shallow"))


class TestMultiLinePlain:
    def test_continuation_lines_are_folded(self):
        assert data("description: one", "  two", "  three")["description"] == "one two three"

    def test_value_starting_on_next_line(self):
        assert data("description:", "  one two", "  three")["description"] == "one two three"

    def test_blank_line_inside_becomes_newline(self):
        assert data("description: one", "", "  two")["description"] == "one\ntwo"

    def test_continuation_with_colon_space_is_rejected(self):
        with pytest.raises(FrontmatterError, match="': '"):
            parse(fm("description: one", "  two: three"))


class TestCollections:
    def test_flow_list(self):
        assert data("tags: [a, 'b, c', \"d\"]")["tags"] == ["a", "b, c", "d"]

    def test_empty_flow_list(self):
        assert data("tags: []")["tags"] == []

    def test_multi_line_flow_list(self):
        assert data("tags: [a,", "  b]")["tags"] == ["a", "b"]

    def test_block_list_indented(self):
        assert data("tags:", "  - a", "  - 'b c'")["tags"] == ["a", "b c"]

    def test_block_list_at_key_indent(self):
        assert data("tags:", "- a", "- b", "next: x") == {"tags": ["a", "b"], "next": "x"}

    def test_nested_mapping(self):
        d = data("metadata:", "  owner: team", "  version: '2'")
        assert d["metadata"] == {"owner": "team", "version": "2"}

    def test_nested_mapping_too_deep(self):
        with pytest.raises(FrontmatterError, match="one level"):
            parse(fm("metadata:", "  a: b", "    c: d"))

    def test_nested_duplicate_key(self):
        with pytest.raises(FrontmatterError, match="duplicate"):
            parse(fm("metadata:", "  a: b", "  a: c"))

    def test_nested_collection_value_is_rejected(self):
        with pytest.raises(FrontmatterError, match="plain or quoted"):
            parse(fm("metadata:", "  a: [b]"))

    def test_nested_flow_list_is_rejected(self):
        with pytest.raises(FrontmatterError, match="nested flow"):
            parse(fm("tags: [a, [b]]"))

    def test_unterminated_flow_list(self):
        with pytest.raises(FrontmatterError, match="unterminated"):
            parse(fm("tags: [a, b"))

    def test_text_after_flow_list(self):
        with pytest.raises(FrontmatterError, match="after"):
            parse(fm("tags: [a] b"))

    def test_flow_mapping_is_rejected(self):
        with pytest.raises(FrontmatterError, match="flow mappings"):
            parse(fm("meta: {a: b}"))


class TestCollectionEdges:
    def test_quoted_list_items_may_contain_brackets_commas_and_escapes(self):
        assert data('tags: ["a]", \'b, c\', "d\\"e"]')["tags"] == ["a]", "b, c", 'd"e']

    def test_stray_closing_brace_in_a_list(self):
        with pytest.raises(FrontmatterError, match="nested flow"):
            parse(fm("tags: [a}]"))

    def test_block_list_allows_blank_lines_and_empty_items(self):
        assert data("l:", "  -", "", "  - a")["l"] == ["", "a"]

    def test_block_list_item_without_dash(self):
        with pytest.raises(FrontmatterError, match="must start with '- '") as info:
            parse(fm("l:", "  - a", "  b"))
        assert info.value.line == 4

    def test_block_list_item_with_quotes(self):
        assert data("l:", "  - 'a: b'", '  - "c # d"')["l"] == ["a: b", "c # d"]

    def test_unterminated_quote_in_list_item(self):
        with pytest.raises(FrontmatterError, match="unterminated"):
            parse(fm("l:", "  - 'abc"))

    def test_text_after_quote_in_list_item(self):
        with pytest.raises(FrontmatterError, match="after closing quote"):
            parse(fm("l:", "  - 'a' b"))

    def test_nested_mapping_allows_blank_lines(self):
        assert data("m:", "  a: 1", "", "  b: 2")["m"] == {"a": "1", "b": "2"}

    def test_nested_mapping_line_without_colon(self):
        with pytest.raises(FrontmatterError, match="expected 'key: value'") as info:
            parse(fm("m:", "  a: b", "  just text"))
        assert info.value.line == 4

    def test_nested_mapping_empty_value(self):
        assert data("m:", "  a:", "  b: x")["m"] == {"a": "", "b": "x"}


class TestStructure:
    def test_key_lines_and_body_start(self):
        result = parse("---\nname: a\n\ndescription: b\n---\n# Title\n")
        assert result.key_lines == {"name": 2, "description": 4}
        assert result.body_start == 6

    def test_dots_close_the_block(self):
        assert parse("---\nname: a\n...\nbody\n").data == {"name": "a"}

    def test_crlf_line_endings(self):
        assert parse("---\r\nname: a\r\ndescription: >\r\n  x\r\n  y\r\n---\r\n").data == {
            "name": "a",
            "description": "x y\n",
        }

    def test_byte_order_mark_is_ignored(self):
        assert parse("﻿---\nname: a\n---\n").data == {"name": "a"}

    def test_trailing_space_on_delimiters_is_tolerated(self):
        assert parse("---  \nname: a\n---  \n").data == {"name": "a"}

    def test_empty_block(self):
        assert parse("---\n---\nbody").data == {}

    def test_split_lines_only_splits_on_newlines(self):
        separator = chr(0x2028)
        assert split_lines(f"a\r\nb{separator}c\nd") == ["a", f"b{separator}c", "d"]


class TestErrors:
    @pytest.mark.parametrize(
        ("text", "line", "fragment"),
        [
            ("name: a\n", 1, "must start"),
            ("", 1, "must start"),
            ("---\nname: a\n", 1, "not closed"),
            ("---\nname: a\nname: b\n---\n", 3, "duplicate key 'name'"),
            ("---\nname a\n---\n", 2, "expected 'key: value'"),
            ("---\nname:a\n---\n", 2, "expected 'key: value'"),
            ("---\n  name: a\n---\n", 2, "unexpected indentation"),
            ("---\n\tname: a\n---\n", 2, "tabs"),
            ("---\nname: a\ndescription: Use when: x\n---\n", 3, "': '"),
            ("---\nname: a\ndescription: ends with:\n---\n", 3, "': '"),
            ("---\nname: @home\n---\n", 2, "cannot start with '@'"),
            ("---\nname: `x`\n---\n", 2, "cannot start with"),
            ("---\nname: *alias\n---\n", 2, "cannot start with '*'"),
        ],
    )
    def test_error_line_and_message(self, text, line, fragment):
        with pytest.raises(FrontmatterError) as info:
            parse(text)
        assert info.value.line == line
        assert fragment in info.value.message
