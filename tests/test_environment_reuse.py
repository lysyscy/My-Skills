"""Opt-in Windows integration: set ENV_REUSE_ROOT to an owned evidence directory.

Uses real managers and network, never modifies existing projects or shared cache
entries. Default package/CI checks skip these machine-specific acceptance tests.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(os.name == "nt" and os.environ.get("ENV_REUSE_ROOT"),
                     "requires explicit Windows fixture/evidence directory")
class EnvironmentReuseTests(unittest.TestCase):
    def setUp(self):
        self.evidence = Path(os.environ["ENV_REUSE_ROOT"]).resolve()
        self.evidence.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="reuse-", dir=self.evidence)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.uv = shutil.which("uv")
        self.pnpm = shutil.which("pnpm.cmd")
        self.assertTrue(self.uv and self.pnpm, "uv and pnpm must already be installed")

    def run_command(self, cwd, args, success=True, env=None):
        result = subprocess.run(list(map(str, args)), cwd=cwd, env=env,
                                capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=120)
        with (self.evidence / "commands.jsonl").open("a", encoding="utf-8") as log:
            log.write(json.dumps(dict(test=self.id(), cwd=str(cwd), args=list(map(str, args)),
                                      exit=result.returncode, stdout=result.stdout,
                                      stderr=result.stderr), ensure_ascii=False) + "\n")
        if success:
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        else:
            self.assertNotEqual(result.returncode, 0, "invalid environment accepted")
        return result

    def python_project(self, name, version="3.1.5", parent=None):
        project = (parent or self.root) / name
        project.mkdir()
        (project / "pyproject.toml").write_text(
            '[project]\nname = "reuse-fixture"\nversion = "0.0.0"\n'
            'requires-python = ">=3.15,<3.16"\n'
            f'dependencies = ["openpyxl=={version}"]\n'
            '[tool.uv]\npackage = false\n', encoding="utf-8")
        (project / ".python-version").write_text("3.15.0\n", encoding="utf-8")
        return project

    def sync(self, project, *args, success=True, env=None):
        return self.run_command(project, [self.uv, "sync", "--no-python-downloads", *args],
                                success, env)

    def python_info(self, project):
        result = self.run_command(project, [project / ".venv/Scripts/python.exe", "-I", "-B", "-c",
            "import sys,json,platform,openpyxl; print(json.dumps(dict(prefix=sys.prefix,"
            "base=sys.base_prefix,version=sys.version,arch=platform.machine(),package=openpyxl.__version__)))"])
        return json.loads(result.stdout)

    def test_python_shared_files_versions_and_repeat(self):
        a, b = self.python_project("a"), self.python_project("b")
        self.sync(a)
        self.sync(b, "--offline")
        ia, ib = self.python_info(a), self.python_info(b)
        self.assertNotEqual(ia["prefix"], ib["prefix"])
        self.assertEqual((ia["base"], ia["version"], ia["arch"]),
                         (ib["base"], ib["version"], ib["arch"]))
        file = Path(".venv/Lib/site-packages/openpyxl/__init__.py")
        self.assertTrue(os.path.samefile(a / file, b / file), "physical sharing not proved")
        self.run_command(a, ["fsutil", "hardlink", "list", a / file])
        lock = (b / "uv.lock").read_bytes()
        self.sync(b, "--locked", "--offline")
        self.sync(b, "--locked", "--check", "--offline")
        self.assertEqual(lock, (b / "uv.lock").read_bytes())
        content = (a / "pyproject.toml").read_text(encoding="utf-8")
        (a / "pyproject.toml").write_text(content.replace("3.1.5", "3.1.4"), encoding="utf-8")
        self.sync(a, "--locked", success=False)
        self.assertEqual(self.python_info(b)["package"], "3.1.5")
        self.sync(a)
        self.assertEqual(self.python_info(a)["package"], "3.1.4")
        self.assertFalse(os.path.samefile(a / file, b / file))
        shutil.rmtree(a)
        self.assertEqual(self.python_info(b)["package"], "3.1.5")

    def node_project(self, name, version="4.0.0"):
        project = self.root / name
        project.mkdir()
        (project / "package.json").write_text(json.dumps(dict(name="reuse-fixture", private=True,
            packageManager="pnpm@11.25.0", dependencies={"is-number": version})), encoding="utf-8")
        return project

    def install(self, project, *args, success=True):
        return self.run_command(project, [self.pnpm, "install", "--ignore-scripts", *args], success)

    def node_check(self, project, version):
        self.run_command(project, ["node", "-e",
            f"require('assert').strictEqual(require('is-number/package.json').version,'{version}');"
            "require('assert').strictEqual(require('is-number')(123),true)"])

    def test_node_shared_files_versions_and_repeat(self):
        a, b = self.node_project("a"), self.node_project("b")
        self.install(a)
        self.install(b, "--offline")
        fa, fb = a / "node_modules/is-number/index.js", b / "node_modules/is-number/index.js"
        self.assertTrue(os.path.samefile(fa, fb), "pnpm physical sharing not proved")
        self.run_command(a, ["fsutil", "hardlink", "list", fa])
        self.run_command(a, [self.pnpm, "store", "path"])
        self.run_command(b, [self.pnpm, "store", "path"])
        lock = (b / "pnpm-lock.yaml").read_bytes()
        self.install(b, "--offline", "--frozen-lockfile")
        self.assertEqual(lock, (b / "pnpm-lock.yaml").read_bytes())
        content = json.loads((a / "package.json").read_text())
        content["dependencies"]["is-number"] = "7.0.0"
        (a / "package.json").write_text(json.dumps(content))
        self.install(a, "--frozen-lockfile", success=False)
        self.node_check(b, "4.0.0")
        self.install(a)
        self.node_check(a, "7.0.0")
        self.assertFalse(os.path.samefile(fa, fb))
        shutil.rmtree(a)
        self.node_check(b, "4.0.0")

    def test_missing_lock_environment_and_unwritable_cache(self):
        a = self.python_project("missing")
        before = set(a.iterdir())
        self.sync(a, "--locked", "--check", "--offline", success=False)
        self.assertEqual(before, set(a.iterdir()), "check wrote project files")
        self.assertFalse((a / ".venv").exists())
        self.sync(a)
        shutil.rmtree(a / ".venv")
        self.sync(a, "--locked", "--check", "--offline", success=False)
        self.assertFalse((a / ".venv").exists())
        cache = self.root / "denied-cache"
        cache.mkdir()
        identity = self.run_command(a, ["whoami"]).stdout.strip()
        self.run_command(a, ["icacls", cache, "/deny", identity + ":(OI)(CI)(W)"])
        try:
            env = dict(os.environ, UV_CACHE_DIR=str(cache))
            self.sync(a, "--locked", env=env, success=False)
        finally:
            self.run_command(a, ["icacls", cache, "/remove:d", identity])
        node = self.node_project("no-node-lock")
        self.install(node, "--frozen-lockfile", success=False)
        self.assertFalse((node / "node_modules").exists())

    def test_cross_volume_python_copy_fallback(self):
        a = self.python_project("same-volume")
        self.sync(a)
        with tempfile.TemporaryDirectory(prefix="reuse-cross-") as other:
            parent = Path(other)
            if parent.drive.lower() == a.drive.lower():
                self.skipTest("system temporary directory is on the same volume")
            b = self.python_project("cross", parent=parent)
            result = self.sync(b, "--offline")
            file = Path(".venv/Lib/site-packages/openpyxl/__init__.py")
            self.assertEqual((a / file).read_bytes(), (b / file).read_bytes())
            self.assertFalse(os.path.samefile(a / file, b / file))
            self.assertIn("copy", result.stderr.lower())
            self.assertEqual(self.python_info(b)["package"], "3.1.5")
            self.run_command(b, ["fsutil", "hardlink", "list", b / file])


if __name__ == "__main__":
    unittest.main()
