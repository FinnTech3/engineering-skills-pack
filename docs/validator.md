# skillcheck reference

`skillcheck` validates, lists, indexes and scaffolds folders of Agent Skills (`SKILL.md` files). It needs Python 3.10
or newer, has no dependencies and does not use the network. Install it from a clone with `pip install -e .`.

## Commands

| Command | What it does |
|---|---|
| `skillcheck validate [PATH] [--json] [--max-lines N]` | Check every skill under `PATH` (default `skills`). `--json` prints `{"ok", "skills_checked", "problems": [{"path", "line", "code", "message"}]}`. |
| `skillcheck list [PATH] [--full]` | Print a table of skills with their line counts and descriptions. `--full` stops shortening descriptions. |
| `skillcheck new NAME [--path DIR]` | Create `DIR/NAME/SKILL.md` (default `DIR` is `skills`) from the template. |
| `skillcheck index [PATH] [-o FILE] [--check]` | Write [INDEX.md](../INDEX.md), or with `-o -` print it. `--check` writes nothing and exits 1 if the file is missing or stale. |

`PATH` may be a skills root, a single skill folder or a `SKILL.md` file. Exit codes: `0` ok, `1` problems found, `2` usage
error (unknown option, bad name, path that does not exist).

A run that finds problems prints one line per problem, then a count:

```console
$ skillcheck validate t
t/test-first-change/SKILL.md:2: name-mismatch: name 'test_first_change' does not match folder 'test-first-change'
t/test-first-change/SKILL.md:2: name-not-kebab: name 'test_first_change' must be lower-case letters and digits separated by single hyphens
t/test-first-change/SKILL.md:30: banned-phrase: 'simply' is vague filler; state the concrete thing instead
t/test-first-change/SKILL.md:76: broken-link: link target 'references/notes.md' does not exist

FAILED: 1 skill checked, 4 problems
```

That is real output from the clip on the README, where a copy of `test-first-change` was edited in a temp folder.

## The 28 rules

The banned phrases are listed in `BANNED_PHRASES` in [`src/skillcheck/rules.py`](../src/skillcheck/rules.py). Matching ignores
case, inline code and fenced code blocks. All Markdown files in a skill folder, including `references/`, are checked for
trailing whitespace, banned phrases, placeholders and links.

| Rule | Fails when |
|---|---|
| `no-skills` | No skill folders were found under the path. |
| `skill-file-missing` | A folder under the skills root has no `SKILL.md`. |
| `read-error` | A Markdown file cannot be read as UTF-8. |
| `frontmatter-invalid` | Frontmatter is missing, unclosed, malformed or has a non-string `name` or `description`. |
| `name-missing` | `name` is absent or empty. |
| `name-not-kebab` | `name` is not lower-case words joined by single hyphens. |
| `name-too-long` | `name` is longer than 64 characters. |
| `name-mismatch` | `name` differs from the folder name. |
| `duplicate-name` | Two skills share a name. |
| `description-missing` | `description` is absent or empty. |
| `description-too-short` | `description` is under 60 characters. |
| `description-too-long` | `description` is over 500 characters. |
| `description-multiline` | `description` contains line breaks; use a folded `>` scalar. |
| `description-no-trigger` | `description` has no "Use when ..." wording. |
| `description-no-exclusion` | `description` has no "Do not use ..." or "Not for ..." wording. |
| `section-missing` | One of the seven required sections is absent. |
| `section-order` | The required sections are not in the standard order. |
| `section-empty` | A required section has no content. |
| `steps-not-numbered` | `Steps` has fewer than 3 numbered items. |
| `section-no-list` | `Exit criteria`, `Failure modes` or `When to stop and ask` has no list items. |
| `purpose-too-long` | The first line of `Purpose` is over 120 characters (it becomes the summary in the tables). |
| `line-limit` | `SKILL.md` is over 120 lines (`--max-lines` changes this), or a reference file is over 200. |
| `broken-link` | A relative link points to a file that does not exist. |
| `link-escapes-skill` | A relative link points outside the skill folder. |
| `orphan-reference` | A Markdown file inside the skill folder is not linked from `SKILL.md`. |
| `banned-phrase` | Vague filler such as "simply", "best practices" or "as needed" appears outside code. |
| `todo-placeholder` | A `TODO`, `FIXME` or `TBD` marker is left in the text. |
| `trailing-whitespace` | A line ends with spaces or tabs. |

## Writing your own skill

```bash
skillcheck new rotate-api-keys      # creates skills/rotate-api-keys/SKILL.md from the template
# replace every TODO in the file; validate fails on each one left behind
skillcheck validate skills
skillcheck index                    # refresh INDEX.md
```

The scaffold already has the right sections in the right order. A skill is worth adding when it can say:

- **A trigger and a non-trigger.** The description names the situation, and the nearest situation where the skill does
  not apply.
- **Steps with an artefact.** Each step produces something you can point at: a command output, a file, a number.
- **Exit criteria you can run.** "Tests pass" is a criterion. "Code is clean" is not.
- **Failure modes from real work.** Each one names a symptom and the fix.
- **Stop conditions.** The cases where continuing without a person would do harm.

## What the parser accepts

The frontmatter parser is written for this tool and accepts a documented subset of YAML: plain, quoted, folded (`>`) and
literal (`|`) scalars, flow and block lists, and one level of nested mapping. It also rejects values that stricter YAML
loaders refuse, such as an unquoted `: ` inside a plain value, so a file that passes here loads elsewhere.
