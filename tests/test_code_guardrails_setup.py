from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from setup_fixture import git, put


SCRIPT = Path(__file__).resolve().parents[1] / 'skills/setup-solo-workflow/scripts/comment_guard.py'


class CodeGuardrailsSetupTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        git(self.root, 'init', '-q', '-b', 'main')
        git(self.root, 'config', 'user.name', 'Fixture')
        git(self.root, 'config', 'user.email', 'fixture@example.invalid')

    def guard(self, *args, code=0):
        result = subprocess.run(
            [sys.executable, '-B', '-X', 'utf8', str(SCRIPT), *args],
            cwd=self.root, capture_output=True, encoding='utf-8', check=False,
        )
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result.stdout

    def test_python_tokenizer_allows_strings_directives_and_external_constraints(self):
        put(self.root, 'probe.py', '''#!/usr/bin/env python3
# coding: utf-8
"""A docstring containing # and https://example.invalid#docs."""
value = "https://example.invalid#docs"  # noqa: F841
other = value  # type: str
# coupling-ignore: example protocol token
# external-constraint: API requires NFC input.
''')
        self.guard('--files', 'probe.py')
        put(self.root, 'probe.py', 'value = 1  # Assign 1 to value.\n')
        self.assertIn('probe.py:1: COMMENT', self.guard('--files', 'probe.py', code=1))

    def test_script_literals_jsx_and_directives_do_not_trigger_comments(self):
        put(self.root, 'probe.tsx', r'''
const literal = "https://example.invalid//path";
const escaped = 'http://example.invalid/\'still a string';
const template = `https://example.invalid/${literal}/* This is text */`;
const matcher = /https?:\/\/example[/*]\.invalid/;
function afterBrace() { return 1; }
/https?:\/\//.test("https://example.invalid");
if (false) afterBrace();
else /https?:\/\//.test("https://example.invalid");
const page = <>https://example.invalid <a href="https://example.invalid/#docs">{literal}</a></>;
const asText = "as unknown as";
// @ts-expect-error fixture for upstream issue
callLegacy();
/** @returns {string} A value for the API. */
function value() { return literal; }
/* external-constraint: upstream API requires a trailing slash. */
const field = template;
''')
        put(self.root, 'probe.js', 'const url = "https://example.invalid";\n')
        self.guard('--files', 'probe.tsx', 'probe.js')
        put(self.root, 'probe.js', 'const url = "https://example.invalid"; // Set the URL.\n')
        self.assertIn('probe.js:1: COMMENT', self.guard('--files', 'probe.js', code=1))
        put(self.root, 'probe.tsx', 'const page = <a>{/* Assign a URL. */ url}</a>;\n')
        self.assertIn('probe.tsx:1: COMMENT', self.guard('--files', 'probe.tsx', code=1))

    def test_staged_and_diff_read_different_versions_and_ignore_untouched_comments(self):
        path = 'sp ace 验证.py'
        baseline = 'first = 1\n# Legacy comment\nsecond = 2\n'
        put(self.root, path, baseline)
        git(self.root, 'add', path)
        git(self.root, 'commit', '-qm', 'Fixture baseline')
        put(self.root, path, baseline + 'third = 3  # Set third to 3.\n')
        git(self.root, 'add', path)
        put(self.root, path, baseline + 'third = 3\n')
        output = self.guard('--staged', code=1)
        self.assertIn(f'{path}:4: COMMENT', output)
        self.assertNotIn(':2: COMMENT', output)
        self.guard('--diff')
        git(self.root, 'add', path)
        put(self.root, path, baseline + 'third = 3  # Set third to 3.\n')
        self.guard('--staged')
        self.assertIn(f'{path}:4: COMMENT', self.guard('--diff', code=1))

    def test_diff_includes_untracked_and_detects_changed_middle_of_block_comment(self):
        put(self.root, 'multiline.mjs', '/*\nFirst line\n*/\n')
        git(self.root, 'add', 'multiline.mjs')
        git(self.root, 'commit', '-qm', 'Fixture baseline')
        put(self.root, 'multiline.mjs', '/*\nRewritten line\n*/\n')
        put(self.root, 'untracked.mts', 'const x = 1; // Set x.\n')
        output = self.guard('--diff', 'HEAD', code=1)
        self.assertIn('multiline.mjs:1: COMMENT', output)
        self.assertIn('untracked.mts:1: COMMENT', output)
        git(self.root, 'add', 'multiline.mjs')
        self.assertNotIn('untracked.mts', self.guard('--staged', code=1))

    def test_assertion_mode_checks_tracked_typescript_tokens_across_lines(self):
        put(self.root, 'probe.ts', 'const text = "as unknown as";\nconst narrowed = source as unknown\n as Target;\n')
        put(self.root, 'probe.py', '# Redundant comment outside the assertion mode.\n')
        git(self.root, 'add', '.')
        output = self.guard('--tracked', '--assertions', code=1)
        self.assertIn('probe.ts:2: DOUBLE_ASSERTION', output)
        self.assertNotIn('COMMENT', output)
        put(self.root, 'probe.ts', 'const narrowed = validate(source);\n')
        self.guard('--tracked', '--assertions')
