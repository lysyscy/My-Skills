#!/usr/bin/env python3
"""Read-only checks for a skill source and Skills Manager installations.

Git publishes the source; Skills Manager owns updates and deployment.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
import hashlib
from html import unescape
from io import StringIO
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tokenize
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen


FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", re.S)
SKILL_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
SKILL_FIELDS = {
    "name", "description", "license", "allowed-tools", "metadata", "compatibility",
    "disable-model-invocation", "user-invocable", "argument-hint",
}
QUOTED = r"""(?:"(?:[^"\\]|\\.)*"|'(?:[^']|'')*')"""
MAPPING_ENTRY = re.compile(rf"({QUOTED}|[^\s'\"#][^:#]*?)\s*:(?:[ \t]+(.*)|$)")
SEQUENCE_ENTRY = re.compile(r"-(?:[ \t]+(.*)|$)")
BLOCK_SCALAR = re.compile(r"([|>])([+-][1-9]?|[1-9][+-]?)?")
FENCE = re.compile(r"^[ \t]*(?:(?:[-+*]|\d+[.)])[ \t]+)?(`{3,}|~{3,})(.*)$")
YAML_ESCAPES = {
    "0": "\0", "a": "\a", "b": "\b", "t": "\t", "\t": "\t", "n": "\n", "v": "\v",
    "f": "\f", "r": "\r", "e": "\x1b", " ": " ", '"': '"', "/": "/", "\\": "\\",
    "N": "\x85", "_": "\xa0", "L": "\u2028", "P": "\u2029",
}


COUPLING_CONTRACT_DOCUMENTS = (
    "**/AGENTS.md", "docs/agents/**/*.md", "skills/**/SKILL.md", "skills/**/references/**/*.md",
    "skills/**/templates/**/*.md", "agent-skills/**/SKILL.md", "agent-skills/**/references/**/*.md",
)
COUPLING_LINK_DOCUMENTS = (
    *COUPLING_CONTRACT_DOCUMENTS, "CONTRIBUTING.md", "CODING_STANDARDS.md", "README.md",
    "docs/guides/**/*.md", "docs/reference/**/*.md", "docs/adr/**/*.md",
    "docs/architecture/**/*.md", "docs/architecture*.md", "docs/requirements.md",
)
COUPLING_TOOL_SUFFIXES = {".py", ".js", ".mjs", ".cjs", ".ps1"}
COUPLING_IGNORED_DIRECTORIES = {
    ".artifacts", ".cache", ".git", ".mypy_cache", ".nox", ".pytest_cache",
    ".ruff_cache", ".scratch", ".tox", ".venv", ".worktrees",
    "__pycache__", "build", "dist", "node_modules", "venv",
}
# These paths document concrete adapters, installed software, or historical evidence.
COUPLING_PATH_OWNERS = {
    "docs/t3-*.md": "workstation host configuration",
    "docs/archive/**": "project archive",
    "docs/receipts/**": "release evidence",
    "docs/agents/host-adapters.md": "Magpie migration snapshot",
    "tools/host_instructions.py": "Magpie migration comparison",
    "skills/project-handoff/hooks/**": "project-handoff host hooks",
    "skills/project-handoff/references/compaction-reminder.md": "project-handoff host hooks",
    "skills/project-handoff/references/handoff.md": "project-handoff host continuation",
    "skills/software-updates/SKILL.md": "workstation software maintenance",
    "skills/software-updates/references/services.md": "workstation service configuration",
    "skills/software-updates/references/status.md": "workstation installation evidence",
    "skills/software-updates/references/targets.md": "workstation update targets",
    "skills/software-updates/references/unigetui.md": "workstation package manager",
}
# ASCII boundaries keep a Chinese suffix such as 的 from hiding an identifier.
COUPLING_RULES = {
    rule_id: (re.compile(rf"(?<![A-Za-z0-9_])(?:{pattern})(?![A-Za-z0-9_])", re.ASCII | re.IGNORECASE), message)
    for rule_id, pattern, message in (
        ("pstack-package", r"t3-pstack",  # coupling-ignore: pstack-package Defines the package name this rule detects.
         "Name the workflow pstack and resolve its implementation through the active host."),
        ("pstack-qualified", r"(?<!-)pstack:(?:[a-z0-9][a-z0-9_-]*|\*)",
         "Resolve the unqualified skill name through the active host."),
        ("t3-runtime", r"T3[ \t-]*Code|T3_ACP_MCP_CALL|T3CODE_[a-z0-9_]*",  # coupling-ignore: t3-runtime Defines the runtime names this rule detects.
         "Put runtime-specific setup in its host adapter."),
        ("host-tool",
         r"mcp__t3_code(?:_direct)?__[a-z0-9_]+"
         r"|t3_(?:attachment|environment|pending_request|preview|project|queue|submit_output|theme|thread|workflow|worktree)[a-z0-9_]*"
         r"|delegate_task|spawn_agent|task_status|task_cancel|orchestrator_capabilities|create_threads"  # coupling-ignore: host-tool Defines the orchestration tools this rule detects.
         r"|preview_(?:act|close|dialog|evaluate|list|navigate|open|recording_(?:start|stop)|resize"
         r"|set_appearance|snapshot|status|wait_for|\*)|device_(?:close|list|open|screenshot)|html_(?:preview|render)",
         "Use the active host's tool entry or put the concrete call in its adapter."),
        ("host-config",
         r"models\.md|hooks\.json|CODEX_HOME|CODEX_CLI_PATH|codex-runtimes|CLAUDE_(?:HOME|CONFIG_DIR)"  # coupling-ignore: host-config Defines the configuration names this rule detects.
         r"""|(?:[a-z]:[\\/]+|(?<![\w./\\:-])[\\/]+)(?:[^\\/\n"'`<>|?*:]+[\\/]+)*"""
         r"AppData[\\/]+app[\\/]+codex(?![\w.-])",
         "Put the concrete configuration name or cache path in its host adapter."),
    )
}

MARKDOWN_LABEL = r"\[(?:\\.|[^\[\]\\\n]|\[[^\[\]\n]*\])*\]"
MARKDOWN_DESTINATION = r"<[^<>\n]+>|(?:\\.|[^\s()<>\\]|\((?:\\.|[^\s()<>\\])*\))+"
MARKDOWN_TITLE = r"""(?:"[^"\n]*"|'[^'\n]*'|\([^)\n]*\))"""
MARKDOWN_LINK = re.compile(
    rf"(?<!\\)(?P<label>{MARKDOWN_LABEL})\([ \t\n]*(?P<inline>{MARKDOWN_DESTINATION})"
    rf"(?:[ \t\n]+{MARKDOWN_TITLE})?[ \t\n]*\)"
    rf"|^ {{0,3}}{MARKDOWN_LABEL}:[ \t]*(?:\n[ \t]*)?(?P<reference>{MARKDOWN_DESTINATION})"
    rf"(?=[ \t]*$|[ \t]+{MARKDOWN_TITLE}[ \t]*$)",
    re.MULTILINE,
)
MARKDOWN_INLINE_CODE = re.compile(r"(?<!`)(`+)(?!`)(?:[^\n]|\n(?![ \t]*\n))*?(?<!`)\1(?!`)")
MARKDOWN_ATX = re.compile(r"^ {0,3}#{1,6}(?:[ \t]+|$)(.*?)(?:[ \t]+#+)?[ \t]*$")
MARKDOWN_SETEXT = re.compile(r"^ {0,3}(?:=+|-+)[ \t]*$")
MARKDOWN_HTML_ANCHOR = re.compile(r"""<[a-z][^>\n]*?\s(?:id|name)=["']([^"']+)["']""", re.IGNORECASE)
MARKDOWN_ABSOLUTE = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|[/\\]|~/)", re.ASCII | re.IGNORECASE)
MARKDOWN_COMMENT = re.compile(r"<!--(?P<comment>.*?)-->", re.DOTALL)
MARKDOWN_COMMENT_TOKENS = re.compile(rf"{MARKDOWN_INLINE_CODE.pattern}|(?<!\\){MARKDOWN_COMMENT.pattern}", re.DOTALL)
JAVASCRIPT_COMMENT_TOKENS = re.compile(
    r"//(?P<comment>[^\n]*)|/\*.*?\*/"
    r"""|"(?:\\[\s\S]|[^"\\\n])*"|'(?:\\[\s\S]|[^'\\\n])*'|`(?:\\[\s\S]|[^`\\])*`"""
    r"|(?:^|(?<=[(=,:!?{\[;|&])|(?<==>)|\b(?:return|case|throw|yield)\b)[ \t]*"
    r"/(?![*/])(?:\\[^\n]|\[(?:\\[^\n]|[^\]\\\n])*\]|[^/\\[\n])+/[a-z]*",
    re.DOTALL | re.MULTILINE,
)
POWERSHELL_COMMENT_TOKENS = re.compile(
    r"""(?<![^\s'"(){}\[\],;=|&])#(?P<comment>[^\n]*)|<#.*?#>"""
    r"""|@"[ \t]*\n.*?^"@|@'[ \t]*\n.*?^'@"""
    r"""|"(?:`[\s\S]|""|[^"`])*"|'(?:''|[^'])*'|`[\s\S]""",
    re.DOTALL | re.MULTILINE,
)
COUPLING_IGNORE_MARKER = "coupling-ignore:"


class PackageError(RuntimeError):
    pass


def yaml_scalar(value):
    if value.startswith(("'", '"')):
        match = re.fullmatch(rf"({QUOTED})(?:[ \t]+#.*)?", value)
        if not match:
            raise ValueError("malformed quoted scalar")
        quoted = match[1]
        if quoted.startswith("'"):
            return quoted[1:-1].replace("''", "'")

        def unescape(escape):
            character = escape[1]
            if character[0] in "xuU" and len(character) > 1:
                codepoint = int(character[1:], 16)
                if 0xD800 <= codepoint <= 0xDFFF:
                    raise ValueError("quoted scalar contains an invalid Unicode escape")
                return chr(codepoint)
            if character in YAML_ESCAPES:
                return YAML_ESCAPES[character]
            raise ValueError(f"invalid escape in quoted scalar: {escape[0]}")

        return re.sub(r"\\(x[\da-fA-F]{2}|u[\da-fA-F]{4}|U[\da-fA-F]{8}|.)", unescape, quoted[1:-1])
    if value in {"true", "false"}:
        return value == "true"
    if value in {"True", "TRUE", "False", "FALSE"}:
        raise ValueError("use lowercase true or false for booleans")
    if value in {"", "null", "Null", "NULL", "~"}:
        return None
    if value == "{}":
        return {}
    if value == "[]":
        return []
    if re.fullmatch(r"0o[0-7]+|0x[0-9a-fA-F]+", value):
        return int(value, 0)
    if re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", value):
        return float(value)
    if re.fullmatch(r"[+-]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN)", value):
        return float(value.replace(".", ""))
    if value[0] in "&*![]{}|>@`%," or re.search(r":(?:[ \t]|$)|^[-?:](?:[ \t]|$)", value):
        raise ValueError("unsupported or malformed plain scalar")
    return value


def read_yaml_mapping(source, filename, first_line=1):
    """Read the block YAML used by skill metadata, without tags, aliases or implicit merges."""
    lines = source.removesuffix("\n").split("\n")
    index = 0

    def fail(row, message):
        raise ValueError(f"{filename}:{first_line + row}: {message}")

    def peek():
        nonlocal index
        while index < len(lines):
            line = lines[index].lstrip(" ")
            if line.strip() and not line.lstrip(" \t").startswith("#"):
                if line.startswith("\t"):
                    fail(index, "use spaces for YAML indentation")
                return len(lines[index]) - len(line), line.rstrip(" \t")
            index += 1
        return -1, ""

    def block(indent, style, explicit_indent, chomp):
        nonlocal index
        padding = indent + int(explicit_indent) if explicit_indent else None
        content = []
        while index < len(lines):
            line = lines[index]
            spaces = len(line) - len(line.lstrip(" "))
            if line.strip():
                if spaces <= indent:
                    break
                if padding is None:
                    padding = spaces
                if spaces < padding:
                    fail(index, "inconsistent block scalar indentation")
            content.append(line[padding:] if padding is not None else "")
            index += 1

        text = "\n".join(content)
        if style == ">" and content:
            parts = [content[0]]
            previous_nonblank = content[0]
            for before, after in zip(content, content[1:]):
                separator = "\n"
                if (previous_nonblank and after
                        and not previous_nonblank.startswith((" ", "\t"))
                        and not after.startswith((" ", "\t"))):
                    separator = " " if before else ""
                parts.extend((separator, after))
                if after:
                    previous_nonblank = after
            text = "".join(parts)
        if content and (index < len(lines) or source.endswith("\n")):
            text += "\n"
        if chomp == "+":
            return text
        trimmed = text.rstrip("\n")
        if chomp != "-" and trimmed and text.endswith("\n"):
            return trimmed + "\n"
        return trimmed

    def scalar(text, row):
        try:
            return yaml_scalar(text)
        except ValueError as error:
            fail(row, str(error))

    def value(text, indent, row):
        # A '#' inside a quoted scalar is data. A plain comment requires separation.
        text = (text or "").strip(" \t")
        if not text.startswith(("'", '"')):
            text = re.split(r"(?:^|[ \t]+)#", text, maxsplit=1)[0].rstrip(" \t")
        if match := BLOCK_SCALAR.fullmatch(text):
            style, suffix = match[1], match[2] or ""
            return block(indent, style, suffix.strip("+-"), suffix.strip("123456789"))
        if text:
            return scalar(text, row)
        child_indent, child = peek()
        if child_indent > indent:
            if SEQUENCE_ENTRY.fullmatch(child):
                return sequence(child_indent)
            return mapping(child_indent)
        return None

    def mapping(indent, first=None):
        nonlocal index
        data = {}
        while True:
            if first is None:
                column, line = peek()
                if column < indent:
                    return data
                if column != indent:
                    fail(index, "inconsistent mapping indentation")
                row = index
                index += 1
            else:
                line, row = first
                first = None
            match = MAPPING_ENTRY.fullmatch(line)
            if not match:
                fail(row, "expected a YAML mapping entry ('key: value')")
            key = scalar(match[1], row)
            if not isinstance(key, str) or not key or key in data or key == "<<":
                fail(row, f"invalid or duplicate mapping key: {match[1]}")
            data[key] = value(match[2], indent, row)

    def sequence(indent):
        nonlocal index
        data = []
        while True:
            column, line = peek()
            if column < indent:
                return data
            match = SEQUENCE_ENTRY.fullmatch(line)
            if column != indent or not match:
                fail(index, "expected a YAML sequence entry ('- value')")
            row = index
            index += 1
            item = match[1] or ""
            if MAPPING_ENTRY.fullmatch(item):
                data.append(mapping(indent + match.start(1), first=(item, row)))
            else:
                data.append(value(item, indent, row))

    for row, line in enumerate(lines):
        if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f\ufffe\uffff]", line):
            fail(row, "invalid YAML control character")
    data = mapping(0)
    if not data:
        fail(0, "expected a YAML mapping")
    return data


def read_structure_text(path):
    try:
        return path.read_text(encoding="utf-8", newline="").replace("\r\n", "\n")
    except UnicodeDecodeError as error:
        raise ValueError(f"{path.name} must be valid UTF-8") from error


def validate_skill_structure(directory):
    content = read_structure_text(directory / "SKILL.md")
    match = FRONTMATTER.match(content)
    if not match:
        raise ValueError("SKILL.md must start with a complete '---' frontmatter block")
    fields = read_yaml_mapping(match[1] + "\n", "SKILL.md", first_line=2)
    if unexpected := fields.keys() - SKILL_FIELDS:
        raise ValueError(f"Unexpected SKILL.md frontmatter keys: {', '.join(sorted(unexpected))}")

    name = fields.get("name")
    if (not isinstance(name, str) or len(name) > 64
            or not SKILL_NAME.fullmatch(name)):
        raise ValueError("SKILL.md name must be 1–64 lowercase ASCII letters, digits and single interior hyphens")
    if name != directory.name:
        raise ValueError(f"SKILL.md name {name!r} must match the skill folder {directory.name!r}")

    description = fields.get("description")
    if not isinstance(description, str) or not description.strip() or len(description) > 1024:
        raise ValueError("SKILL.md description must be a non-empty string of at most 1024 characters")
    if description.lstrip().startswith("[TODO:") or "<" in description or ">" in description:
        raise ValueError("SKILL.md description cannot contain angle brackets or begin with [TODO:")
    if "compatibility" in fields:
        compatibility = fields["compatibility"]
        if not isinstance(compatibility, str) or len(compatibility) > 500:
            raise ValueError("SKILL.md compatibility must be a string of at most 500 characters")
    for field in ("disable-model-invocation", "user-invocable"):
        if field in fields and not isinstance(fields[field], bool):
            raise ValueError(f"SKILL.md {field} must be a YAML boolean (true or false)")
    if "argument-hint" in fields:
        hint = fields["argument-hint"]
        if not isinstance(hint, str) or not hint.strip():
            raise ValueError("SKILL.md argument-hint must be a non-empty string")

    marker = ""
    for line in content[match.end():].splitlines():
        if fence := FENCE.match(line):
            if not marker:
                marker = fence[1]
            elif fence[1].startswith(marker) and not fence[2].strip():
                marker = ""
    if marker:
        raise ValueError("SKILL.md contains an unclosed fenced code block")

    openai = directory / "agents/openai.yaml"
    if openai.exists() or openai.is_symlink():
        config = read_yaml_mapping(read_structure_text(openai), "agents/openai.yaml")
        for group in ("interface", "dependencies", "policy"):
            if group in config and not isinstance(config[group], dict):
                raise ValueError(f"agents/openai.yaml {group} must be a mapping")
        policy = config.get("policy", {})
        if "allow_implicit_invocation" in policy and not isinstance(policy["allow_implicit_invocation"], bool):
            raise ValueError("agents/openai.yaml policy.allow_implicit_invocation must be a YAML boolean (true or false)")


def process(args, cwd=None, timeout=120):
    return subprocess.run(args, cwd=cwd, capture_output=True, encoding="utf-8",
                          errors="replace", timeout=timeout)


def git(root, *args):
    result = process(["git", "--no-optional-locks", "-C", str(root), *args])
    if result.returncode:
        raise PackageError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def contained(root, relative):
    path = root / relative
    if Path(relative).is_absolute() or not path.resolve().is_relative_to(root.resolve()):
        raise PackageError(f"Path escapes package: {relative}")
    return path


def linked(path):
    try:
        return path.is_symlink() or bool(getattr(path.lstat(), "st_file_attributes", 0)
                                         & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    except FileNotFoundError:
        return False


def coupling_files(root):
    def raise_walk_error(error):
        raise error

    for directory, subdirs, files in root.walk(on_error=raise_walk_error):
        subdirs[:] = [name for name in subdirs
                      if name not in COUPLING_IGNORED_DIRECTORIES and not linked(directory / name)]
        for name in files:
            path = directory / name
            relative = PurePosixPath(path.relative_to(root).as_posix())
            if relative.parts[0] == "tools" and relative.suffix.lower() in COUPLING_TOOL_SUFFIXES:
                yield relative, path
            elif relative.suffix == ".md" and any(relative.full_match(pattern) for pattern in COUPLING_LINK_DOCUMENTS):
                yield relative, path


def markdown_body(content, *, strip_comments=True):
    """Mask frontmatter and fenced examples without shifting line numbers."""
    content = content.removeprefix("\ufeff")
    if frontmatter := FRONTMATTER.match(content):
        content = "\n" * frontmatter[0].count("\n") + content[frontmatter.end():]
    marker = ""
    lines = []
    for line in content.split("\n"):
        fence = FENCE.match(line)
        lines.append("" if marker or fence else line)
        if fence:
            if not marker:
                marker = fence[1]
            elif fence[1].startswith(marker) and not fence[2].strip():
                marker = ""
    body = "\n".join(lines)
    if strip_comments:
        body = MARKDOWN_COMMENT.sub(lambda match: "\n" * match[0].count("\n"), body)
    return body


def markdown_links(body):
    body = MARKDOWN_INLINE_CODE.sub(lambda match: re.sub(r"[^\n]", " ", match[0]), body)
    starts = [0, *(match.end() for match in re.finditer("\n", body))]
    for link in MARKDOWN_LINK.finditer(body):
        destination = link["inline"] or link["reference"]
        destination = unescape(re.sub(r"\\([!-\/:-@\[-`{-~])", r"\1", destination.removeprefix("<").removesuffix(">")))
        if not MARKDOWN_ABSOLUTE.match(destination):
            yield bisect_right(starts, link.start()), destination


def markdown_anchors(content):
    names = set()
    headings = set()
    previous = ""
    for line in markdown_body(content).split("\n"):
        names.update(MARKDOWN_HTML_ANCHOR.findall(line))
        if atx := MARKDOWN_ATX.match(line):
            title = atx[1]
        elif MARKDOWN_SETEXT.fullmatch(line):
            title = previous
        else:
            previous = line
            continue
        previous = ""
        if not title:
            continue
        title = MARKDOWN_LINK.sub(lambda match: match["label"][1:-1] if match["label"] else "", title)
        title = unescape(re.sub(r"<[^>]*>", "", title)).strip().lower()
        base = re.sub(r"[^\w -]", "", title).replace(" ", "-")
        slug, suffix = base, 1
        while slug in headings:
            slug = f"{base}-{suffix}"
            suffix += 1
        headings.add(slug)
    return names | headings


def relative_markdown_link_error(root, document, destination, anchors):
    address, _, fragment = destination.partition("#")
    relative = unquote(address.partition("?")[0])
    target = (document.parent / relative).resolve() if relative else document
    if not target.is_relative_to(root):
        return "Relative link points outside the source repository."
    if not target.exists():
        return "Relative link target does not exist."
    if fragment and target.is_file() and target.suffix.lower() == ".md":
        if target not in anchors:
            anchors[target] = markdown_anchors(target.read_text(encoding="utf-8"))
        if unquote(fragment) not in anchors[target]:
            return "Markdown anchor does not exist in the target."
    return None


def coupling_violation(path, rule_id, line, source_line, match, message):
    return {
        "path": path, "rule_id": rule_id, "line": line,
        "line_sha256": hashlib.sha256(source_line.encode("utf-8")).hexdigest(),
        "match": match, "message": message,
    }


def coupling_comments(content, suffix):
    if suffix == ".py":
        try:
            for token in tokenize.generate_tokens(StringIO(content).readline):
                if token.type == tokenize.COMMENT:
                    yield token.start[0], token.start[1], token.end[1], token.string[1:]
        except (tokenize.TokenError, SyntaxError):
            # Incomplete Python source still gets checked for coupling.
            pass
        return

    if suffix == ".md":
        content = markdown_body(content, strip_comments=False)
        tokens = MARKDOWN_COMMENT_TOKENS
    elif suffix == ".ps1":
        tokens = POWERSHELL_COMMENT_TOKENS
    else:
        tokens = JAVASCRIPT_COMMENT_TOKENS
    starts = [0, *(match.end() for match in re.finditer("\n", content))]
    for match in tokens.finditer(content):
        comment = match["comment"]
        if comment is not None and "\n" not in comment:
            number = bisect_right(starts, match.start())
            offset = starts[number - 1]
            yield number, match.start() - offset, match.end() - offset, comment


def coupling_file_violations(root, relative, path, anchors):
    if not path.is_file() or not path.resolve().is_relative_to(root):
        raise PackageError(f"{relative}: expected a readable file within the source repository")
    content = path.read_text(encoding="utf-8-sig")
    lines = content.split("\n")
    name = relative.as_posix()
    suffix = relative.suffix.lower()
    markdown = suffix == ".md"
    contract = not markdown or any(relative.full_match(pattern) for pattern in COUPLING_CONTRACT_DOCUMENTS)
    rules = COUPLING_RULES.items() if contract and not any(
        relative.full_match(pattern) for pattern in COUPLING_PATH_OWNERS
    ) else ()
    directives = {}
    if COUPLING_IGNORE_MARKER in content:
        for number, start, end, comment in coupling_comments(content, suffix):
            if (comment := comment.lstrip()).startswith(COUPLING_IGNORE_MARKER):
                payload = comment.removeprefix(COUPLING_IGNORE_MARKER).strip()
                directives.setdefault(number, []).append((start, end, payload))

    if rules or directives:
        for number, line in enumerate(lines, 1):
            checked_line = line
            ignored_rules = set()
            for start, end, payload in directives.get(number, ()):
                checked_line = checked_line[:start] + " " * (end - start) + checked_line[end:]
                fields = payload.split(maxsplit=1)
                if len(fields) != 2:
                    error = "A coupling ignore requires a rule ID and a reason."
                elif fields[0] not in COUPLING_RULES:
                    error = f"Rule {fields[0]} is unknown or cannot be ignored."
                else:
                    ignored_rules.add(fields[0])
                    continue
                yield coupling_violation(name, "invalid-ignore", number, line, payload, error)
            for rule_id, (pattern, message) in rules:
                if rule_id not in ignored_rules and (match := pattern.search(checked_line)):
                    yield coupling_violation(name, rule_id, number, line, match[0], message)
    if markdown:
        for number, destination in markdown_links(markdown_body(content)):
            if error := relative_markdown_link_error(root, path, destination, anchors):
                yield coupling_violation(name, "broken-relative-link", number, lines[number - 1], destination, error)


def check_coupling(source):
    root = source.resolve()
    if not root.is_dir():
        raise PackageError(f"Coupling source must be a directory: {root}")
    violations, anchors = [], {}
    files = sorted(coupling_files(root))
    for relative, path in files:
        violations.extend(coupling_file_violations(root, relative, path, anchors))
    violations.sort(key=lambda value: (value["path"], value["line"], value["rule_id"]))
    return {
        "status": "validation_failed" if violations else "verified",
        "source": str(root), "files_checked": len(files), "violations": violations,
    }


def resource_bytes(path, content):
    if Path(path).suffix.lower() in {".md", ".yaml", ".yml", ".json", ".txt", ".py", ".toml", ".ps1", ".sh"}:
        if any(byte < 32 and byte not in (9, 10, 13) or byte == 127 for byte in content):
            return content
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            return content
        return content.replace(b"\r\n", b"\n")
    return content


def fingerprint(resources):
    value = hashlib.sha256()
    for relative, content in sorted(resources):
        value.update(relative.encode("utf-8") + b"\0")
        value.update(hashlib.sha256(resource_bytes(relative, content)).digest())
    return value.hexdigest()


def directory_fingerprint(directory):
    if not (directory / "SKILL.md").is_file():
        raise PackageError(f"Skill is missing its entry: {directory}")
    resources = []
    def read_error(error):
        raise error
    for current, folders, filenames in os.walk(directory, followlinks=False, onerror=read_error):
        for name in folders + filenames:
            if linked(Path(current) / name):
                raise PackageError(f"Linked skill resource needs investigation: {Path(current) / name}")
        for name in filenames:
            path = Path(current) / name
            resources.append((path.relative_to(directory).as_posix(), path.read_bytes()))
    return fingerprint(resources)


def skills_manager_cli():
    directory = Path.home() / ".skills-manager" / "bin"
    binary = directory / ("skills-manager-cli.exe" if os.name == "nt" else "skills-manager-cli")
    stamp = directory / ".version"
    if binary.exists() or stamp.exists():
        if not binary.is_file() or not binary.stat().st_size or not stamp.is_file() or not stamp.stat().st_size:
            raise PackageError("Skills Manager bridge is incomplete; open Skills Manager to republish it")
        return str(binary)
    found = shutil.which("skills-manager-cli")
    if not found:
        raise PackageError("Skills Manager CLI is unavailable")
    return found


def manager_json(cli, *args):
    result = process([str(cli), "--json", *args])
    if result.returncode:
        raise PackageError(result.stderr.strip() or result.stdout.strip() or "Skills Manager failed")
    try:
        value = json.loads(result.stdout)
    except ValueError as error:
        raise PackageError("Skills Manager returned invalid JSON") from error
    if isinstance(value, dict) and value.get("ok") is False:
        raise PackageError(value.get("message", "Skills Manager refused the query"))
    return value


def github_runs(remote, revision):
    url = urlsplit(remote.removesuffix('.git'))
    if url.scheme != 'https' or url.netloc != 'github.com' or len(url.path.strip('/').split('/')) != 2:
        raise PackageError('CI receipt requires an HTTPS GitHub source')
    request = Request(f'https://api.github.com/repos{url.path}/actions/runs?head_sha={revision}&per_page=30',
                      headers={'User-Agent': 'My-Skills-release-check'})
    with urlopen(request, timeout=30) as response:
        return json.load(response)['workflow_runs']


class Package:
    def __init__(self, root):
        self.root = Path(git(Path(root).resolve(), "rev-parse", "--show-toplevel"))
        self.policy = read_json(self.root / "skill-package.json")
        for name in self.policy["upstream_skills"]:
            if not name or name in {".", ".."} or "/" in name or "\\" in name:
                raise PackageError("Upstream names must be installed skill directory names")
        self.previous_skill_directories = self.policy.get("previous_skill_directories", {})
        if not isinstance(self.previous_skill_directories, dict):
            raise PackageError("Previous skill directories must map current names to old names")
        previous_names = list(self.previous_skill_directories.values())
        if (any(not isinstance(name, str) or not SKILL_NAME.fullmatch(name)
                for name in [*self.previous_skill_directories, *previous_names])
                or len(set(previous_names)) != len(previous_names)
                or set(previous_names).intersection(self.previous_skill_directories)):
            raise PackageError("Previous skill directories must be distinct skill names")
        self.skills_root = contained(self.root, self.policy["skills_root"])
        if self.skills_root == self.root or self.skills_root.name == ".git":
            raise PackageError("Skills root must be a package subdirectory")
        actual = git(self.root, "remote", "get-url", "origin")
        if actual.rstrip("/").removesuffix(".git") != self.policy["remote"].rstrip("/").removesuffix(".git"):
            raise PackageError("Origin does not match authorized package remote")

    def discover(self, *, check_frontmatter=True):
        skills = []
        for directory in sorted(self.skills_root.iterdir()):
            if not directory.is_dir() or not (directory / "SKILL.md").is_file():
                continue
            if linked(directory) or not directory.resolve().is_relative_to(self.skills_root.resolve()):
                raise PackageError(f"Skill escapes managed root: {directory.name}")
            if directory.name in self.policy["upstream_skills"]:
                raise PackageError(f"Upstream skill cannot become managed: {directory.name}")
            if directory.name in self.previous_skill_directories.values():
                raise PackageError(f"Renamed skill still exists at its previous source directory: {directory.name}")
            if check_frontmatter:
                content = (directory / "SKILL.md").read_text(encoding="utf-8")
                match = FRONTMATTER.match(content)
                if not match or not re.search(r"(?m)^name:\s*[\"']?" + re.escape(directory.name) + r"[\"']?\s*$", match[1]):
                    raise PackageError(f"Skill directory/frontmatter mismatch: {directory.name}")
                if not re.search(r"(?m)^description:\s*\S", match[1]):
                    raise PackageError(f"Skill description missing: {directory.name}")
            skills.append(directory.name)
        if not skills:
            raise PackageError("No skills found in the authorized source")
        return skills

    def structure(self, validator=None, validation_python=None):
        if validator is None:
            result = self.builtin_structure()
        else:
            result = self.external_structure(validator, validation_python)
        if result["status"] == "verified":
            result["coupling"] = check_coupling(self.root)
            result["status"] = result["coupling"]["status"]
        return result

    def external_structure(self, validator, validation_python):
        if validation_python is None:
            raise PackageError("structure needs --validator and --validation-python")
        validator, validation_python = validator.resolve(), validation_python.resolve()
        if not validator.is_file() or not validation_python.is_file():
            raise PackageError(f"Structure check needs existing validator and interpreter: {validator}, {validation_python}")
        probe = process([str(validation_python), "-X", "utf8", "-c", "import yaml"], timeout=30)
        result = {"validator": str(validator), "python": str(validation_python), "checks": []}
        if probe.returncode:
            return dict(result, status="environment_blocked", dependency="yaml", exit_code=probe.returncode,
                        output=(probe.stdout + probe.stderr)[:2000])
        for name in self.discover():
            check = process([str(validation_python), "-X", "utf8", str(validator), str(self.skills_root / name)], timeout=30)
            output = check.stdout + check.stderr
            result["checks"].append({"skill": name, "exit_code": check.returncode,
                                     "output": output[:2000], "output_truncated": len(output) > 2000})
        result["status"] = "verified" if all(check["exit_code"] == 0 for check in result["checks"]) else "validation_failed"
        return result

    def builtin_structure(self):
        result = {"validator": "builtin:cross-host", "checks": []}
        try:
            skills = self.discover(check_frontmatter=False)
        except PackageError as error:
            return dict(result, status="validation_failed", error=str(error))
        for name in skills:
            try:
                validate_skill_structure(self.skills_root / name)
                check = {"exit_code": 0, "output": "Skill structure is valid"}
            except (OSError, ValueError, RecursionError) as error:
                check = {"exit_code": 1, "output": str(error)}
            result["checks"].append({"skill": name, **check})
        result["status"] = "verified" if all(check["exit_code"] == 0 for check in result["checks"]) else "validation_failed"
        return result

    def require_revision(self, revision):
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise PackageError("Use the full verified commit SHA, not a moving branch name")
        if git(self.root, "rev-parse", "--verify", revision + "^{commit}") != revision:
            raise PackageError("Revision must name a commit")
        if git(self.root, "rev-parse", "HEAD") != revision or git(self.root, "status", "--porcelain"):
            raise PackageError("Check installation from the clean source at the verified revision")

    def committed_fingerprint(self, revision, name, root=None):
        prefix = (Path(self.policy["skills_root"]) / name).as_posix() + "/" if root is None else name + "/"
        root = self.root if root is None else root
        tree = git(root, "ls-tree", "-r", "-z", revision, "--", prefix)
        resources = []
        for row in filter(None, tree.split("\0")):
            header, path = row.split("\t", 1)
            mode, kind, object_id = header.split()
            if mode not in {"100644", "100755"} or kind != "blob":
                raise PackageError(f"Linked or unsupported committed skill resource: {path}")
            blob = subprocess.run(["git", "--no-optional-locks", "-C", str(root), "cat-file", "blob", object_id],
                                  capture_output=True, timeout=120)
            if blob.returncode:
                raise PackageError(f"Cannot read committed skill resource: {path}")
            resources.append((path.removeprefix(prefix), blob.stdout))
        return fingerprint(resources)

    def known_skill_version(self, name, actual):
        prefix = (Path(self.policy["skills_root"]) / name).as_posix() + "/"
        return any(self.committed_fingerprint(revision, name) == actual
                   for revision in git(self.root, "rev-list", "HEAD", "--", prefix).splitlines())

    def manager_source(self, record, entry, metadata_root, name):
        if not record or Path(record["path"]).resolve() != entry.resolve() or linked(entry):
            raise PackageError(f"Skills Manager does not own the expected library entry: {name}")
        reference = record.get("source_ref", "").rstrip("/").removesuffix(".git")
        remote = self.policy["remote"].rstrip("/").removesuffix(".git")
        tree_reference = f"{remote}/tree/{self.policy['branch']}/{Path(self.policy['skills_root']).as_posix()}"
        if record.get("source_type") != "git" or reference not in {remote, tree_reference, tree_reference + "/" + name}:
            raise PackageError(f"Skills Manager source differs from the maintenance source: {name}")
        metadata = read_json(contained(metadata_root, record["id"] + ".json"))
        source = metadata.get("source", {})
        if (metadata.get("skill_id") != record["id"] or metadata.get("path") != entry.name
                or source.get("type") != record.get("source_type")
                or source.get("ref") != record.get("source_ref")):
            raise PackageError(f"Skills Manager source metadata disagrees with the registry: {name}")
        if str(source.get("subpath", "")).replace("\\", "/").strip("/") != (Path(self.policy["skills_root"]) / name).as_posix():
            raise PackageError(f"Skills Manager source subpath differs: {name}")
        branch = source.get("branch")
        if branch is None:
            remote_head = git(self.root, "ls-remote", "--symref", self.policy["remote"], "HEAD")
            match = re.search(r"(?m)^ref: refs/heads/(.+)\tHEAD$", remote_head)
            if not match:
                raise PackageError("Cannot verify the default branch used by Skills Manager")
            branch = match[1]
        if branch != self.policy["branch"]:
            raise PackageError(f"Skills Manager source branch differs: {name}")

    def manager_context(self, cli):
        repository = manager_json(cli, "repo", "status")
        library = Path(repository["skills_dir"]).resolve()
        records = {}
        for record in manager_json(cli, "skills", "list"):
            if record["name"] in records:
                raise PackageError(f"Ambiguous library skill: {record['name']}")
            records[record["name"]] = record
        agents = {agent["key"]: agent for agent in manager_json(cli, "agents", "list")}
        return library, Path(repository["metadata_dir"]).resolve() / "skills", records, agents

    def manager_entry(self, records, library, name, *, allow_previous_name=False):
        directories = {name}
        if previous := self.previous_skill_directories.get(name):
            directories.add(previous)
        expected_paths = {(library / directory).resolve() for directory in directories}
        matching = [record for record in records.values()
                    if record["name"] in directories or (isinstance(record.get("path"), str)
                        and Path(record["path"]).resolve() in expected_paths)]
        if len(matching) > 1:
            raise PackageError(f"Ambiguous Manager records for name or directory: {name}")
        record = matching[0] if matching else None
        directory = Path(record["path"]).name if record else name
        if directory not in directories:
            raise PackageError(f"Skills Manager does not own the expected library entry: {name}")
        for unused in directories - ({directory} if record else set()):
            if (library / unused).exists() or linked(library / unused):
                raise PackageError(f"Unmanaged library entry preserved: {unused}")
        if record and record["name"] != name:
            if not allow_previous_name:
                raise PackageError(f"Skills Manager has not registered the new name: {name}")
            if directory != name and record["name"] != directory:
                raise PackageError(f"Unexpected Manager name for previous directory: {directory}")
        return record, library / directory

    @staticmethod
    def selection(record):
        for key in ("tags", "preset_ids", "deployed_to"):
            if not isinstance(record.get(key, []), list) or any(not isinstance(value, str) for value in record.get(key, [])):
                raise PackageError(f"Invalid Manager selection: {key}")
        return {"id": record["id"], **{key: sorted(record.get(key, []))
                for key in ("tags", "preset_ids", "deployed_to")}}

    def deployment(self, agents, key, name, entry):
        if key not in agents or not agents[key].get("skills_dir"):
            raise PackageError(f"Unknown managed deployment agent: {key}")
        agent_root = Path(agents[key]["skills_dir"])
        target = agent_root / entry.name
        if linked(target) and target.resolve() != entry.resolve():
            raise PackageError(f"Foreign managed deployment link preserved: {key}/{name}")
        alternate = name if entry.name != name else self.previous_skill_directories.get(name)
        if alternate and ((agent_root / alternate).exists() or linked(agent_root / alternate)):
            raise PackageError(f"Unmanaged Agent entry preserved: {key}/{alternate}")
        return target

    def preflight(self, cli, revision, allowed_renames=None):
        self.require_revision(revision)
        library, metadata_root, records, agents = self.manager_context(cli)
        allowed_renames = allowed_renames or {}
        selections, renamed_skills, library_aliases = {}, {}, {}
        for name in self.discover():
            record, entry = self.manager_entry(records, library, name, allow_previous_name=True)
            if record is None:
                selections[name] = {"id": None, "tags": [], "preset_ids": [], "deployed_to": []}
                continue
            if record['name'] != name:
                if allowed_renames.get(name) != record['name']:
                    raise PackageError(f"Skill rename needs explicit approval: {record['name']} -> {name}")
                renamed_skills[name] = record['name']
            if entry.name != name:
                library_aliases[name] = entry.name
            source_name = entry.name if record["name"] == entry.name else name
            self.manager_source(record, entry, metadata_root, source_name)
            if not self.known_skill_version(source_name, directory_fingerprint(entry)):
                raise PackageError(f"Unknown library edits preserved: {name}")
            selections[name] = self.selection(record)
            for key in selections[name]["deployed_to"]:
                target = self.deployment(agents, key, name, entry)
                if (target.exists() or linked(target)) and not self.known_skill_version(
                        source_name, directory_fingerprint(target)):
                    raise PackageError(f"Unknown Agent edits preserved: {key}/{name}")
        if set(allowed_renames) != set(renamed_skills):
            raise PackageError('Approved rename does not match the current Manager state')
        return {"status": "preflight_ok", "revision": revision, "source": str(self.root),
                "library": str(library), "skills": selections, "renamed_skills": renamed_skills,
                "library_aliases": library_aliases}

    def confirm_install(self, cli, revision, plan):
        self.require_revision(revision)
        library, metadata_root, records, agents = self.manager_context(cli)
        names = self.discover()
        if (plan.get("status") != "preflight_ok" or plan.get("revision") != revision
                or plan.get("source") != str(self.root) or plan.get("library") != str(library)
                or set(plan.get("skills", {})) != set(names)):
            raise PackageError("Update plan does not match this source, revision, library and skill set")
        library_aliases = plan.get("library_aliases", {})
        if (not isinstance(library_aliases, dict)
                or any(name not in names or directory != self.previous_skill_directories.get(name)
                       for name, directory in library_aliases.items())):
            raise PackageError("Invalid library aliases in update plan")
        deployments = {}
        for name in names:
            record, entry = self.manager_entry(records, library, name)
            if entry.name != library_aliases.get(name, name):
                raise PackageError(f"Manager library directory changed: {name}")
            self.manager_source(record, entry, metadata_root, name)
            previous, current = plan["skills"][name], self.selection(record)
            if (not isinstance(previous, dict) or set(previous) != {"id", "tags", "preset_ids", "deployed_to"}
                    or (previous["id"] is not None and not isinstance(previous["id"], str))):
                raise PackageError(f"Incomplete or invalid update selection: {name}")
            previous = self.selection(previous)
            if any(current[key] != value for key, value in previous.items() if key != "id" or value is not None):
                raise PackageError(f"Identity or deployment choices changed: {name}")
            expected = self.committed_fingerprint(revision, name)
            if directory_fingerprint(entry) != expected:
                raise PackageError(f"Manager library differs from the verified revision: {name}")
            deployments[name] = current["deployed_to"]
            for key in deployments[name]:
                target = self.deployment(agents, key, name, entry)
                if directory_fingerprint(target) != expected:
                    raise PackageError(f"Managed deployment is missing or stale: {key}/{name}")
        return {"status": "installation_verified", "revision": revision, "library": str(library),
                "deployments": deployments, "library_aliases": library_aliases,
                "scope": "local files; host loading and other devices not checked"}

    def confirm_source(self, revision):
        self.require_revision(revision)
        remote = git(self.root, 'ls-remote', '--exit-code', self.policy['remote'],
                     'refs/heads/' + self.policy['branch']).split()
        if not remote or remote[0] != revision:
            raise PackageError('Source remote does not match the verified revision; inspect before installing')
        workflow = self.policy.get('ci_workflow', '.github/workflows/tests.yml')
        runs = [run for run in github_runs(self.policy['remote'], revision)
                if run.get('head_sha') == revision and run.get('path') == workflow and run.get('event') == 'push']
        if not runs or runs[0].get('status') != 'completed' or runs[0].get('conclusion') != 'success':
            raise PackageError('Exact source commit CI has not succeeded; installation remains pending')
        return {'status': 'source_verified', 'source_revision': revision, 'ci_url': runs[0].get('html_url')}

    def confirm_distribution(self, cli, revision, plan):
        source = self.confirm_source(revision)
        installation = self.confirm_install(cli, revision, plan)
        library, metadata, records, _ = self.manager_context(cli)
        portable_revisions = True
        for name in self.discover():
            portable = read_json(metadata / (records[name]['id'] + '.json'))
            if portable.get('source', {}).get('revision') != revision:
                portable_revisions = False
            checks = manager_json(cli, 'skills', 'check', name, '--force')
            if (not isinstance(checks, list) or len(checks) != 1 or checks[0].get('name') != name
                    or checks[0].get('update_status') != 'up_to_date' or checks[0].get('last_check_error')):
                raise PackageError(f'Manager update detection is not healthy: {name}')
        backup = manager_json(cli, 'git', 'status')
        if Path(git(library, 'rev-parse', '--show-toplevel')).resolve() != library:
            raise PackageError('Manager backup must be rooted in the actual central library')
        if git(library, 'status', '--porcelain'):
            raise PackageError('Manager backup contains uncommitted files')
        actual_remote = git(library, 'remote', 'get-url', 'origin')
        if not backup.get('remote_url') or actual_remote != backup['remote_url']:
            raise PackageError('Manager backup remote differs from its registered remote')
        head = git(library, 'rev-parse', 'HEAD')
        remote = git(library, 'ls-remote', '--exit-code', 'origin', 'refs/heads/' + backup['branch']).split()
        if not remote or remote[0] != head:
            raise PackageError('Manager backup remote does not contain the current snapshot')
        for name in self.discover():
            directory = installation['library_aliases'].get(name, name)
            if self.committed_fingerprint(head, directory, library) != self.committed_fingerprint(revision, name):
                raise PackageError(f'Manager backup omits or changes skill resources: {name}')
            relative = (metadata / (records[name]['id'] + '.json')).relative_to(library).as_posix()
            if json.loads(git(library, 'show', f'{head}:{relative}')) != read_json(library / relative):
                raise PackageError(f'Manager backup source metadata differs: {name}')
        return dict(source, status='distribution_verified', backup_revision=head,
                    deployments=installation['deployments'],
                    library_aliases=installation['library_aliases'],
                    cross_device_detection='requires_receiver_verification' if portable_revisions else 'needs_calibration_after_restore',
                    receiver_action='After restore, use official Manager update for affected skills, then check; unknown is not up-to-date',
                    scope='published source CI, local deployments, pushed portable backup; other physical devices not checked')


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=[
        "structure", "coupling", "preflight", "confirm-install", "confirm-source", "confirm-distribution",
    ])
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--json", action="store_true", help="Emit coupling diagnostics as JSON")
    parser.add_argument("--revision", help="Full verified commit SHA for installation checks")
    parser.add_argument("--skills-manager-cli", type=Path)
    parser.add_argument("--plan", type=Path, help="Saved preflight JSON, with any explicitly authorized new deployment choices")
    parser.add_argument("--validator", type=Path, help="Optional external structure validator")
    parser.add_argument("--validation-python", type=Path, help="Interpreter with PyYAML for the external validator")
    parser.add_argument("--allow-rename", action="append", default=[], metavar="OLD=NEW")
    args = parser.parse_args()
    try:
        if args.allow_rename and args.action != 'preflight':
            raise PackageError('Rename approvals are only accepted for preflight')
        if args.json and args.action != "coupling":
            raise PackageError("--json is only accepted for coupling")
        renames = {}
        for value in args.allow_rename:
            old, separator, new = value.partition('=')
            if not separator or not old or not new or old == new or '=' in new or new in renames:
                raise PackageError('Use one distinct OLD=NEW value for each approved rename')
            renames[new] = old
        if args.action == "coupling":
            result = check_coupling(args.source)
        elif args.action == "structure":
            result = Package(args.source).structure(args.validator, args.validation_python)
        else:
            package = Package(args.source)
            if args.revision is None:
                raise PackageError("Installation checks need --revision")
            if args.action == 'confirm-source':
                result = package.confirm_source(args.revision)
            else:
                cli = args.skills_manager_cli or skills_manager_cli()
                if args.action == "preflight":
                    result = package.preflight(cli, args.revision, renames)
                else:
                    if args.plan is None:
                        raise PackageError("confirm-install needs --plan from the update preflight")
                    check = package.confirm_distribution if args.action == 'confirm-distribution' else package.confirm_install
                    result = check(cli, args.revision, read_json(args.plan))
    except (PackageError, OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        result = {"status": "blocked", "error": str(error)}
    if args.action != "coupling" or args.json:
        print(json.dumps(result, ensure_ascii=False))
    elif result["status"] == "blocked":
        print(f"Coupling blocked: {result['error']}", file=sys.stderr)
    else:
        for finding in result["violations"]:
            location = f"{finding['path']}:{finding['line']}"
            print(f"{location} [{finding['rule_id']}] {finding['match']}. {finding['message']}")
        print(f"Coupling: {len(result['violations'])} violation(s) in {result['files_checked']} file(s).")
    return 0 if result["status"] in {
        "verified", "preflight_ok", "installation_verified", "source_verified", "distribution_verified",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
