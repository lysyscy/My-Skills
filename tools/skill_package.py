#!/usr/bin/env python3
"""Personal skill package transactions. Python standard library; Git required.

JSON output, exit 0 success, 2 preserved work requiring agent action, 1 error.
The agent owns retrospective decisions, semantic integration, commits and review.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import uuid


class PackageError(RuntimeError):
    pass


def process(args, cwd=None, env=None, timeout=120):
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


def git(root, *args, check=True):
    result = process(["git", "-C", str(root), *args])
    if (result.returncode and args and args[0] == "merge" and
            any(message in result.stderr for message in ("Author identity unknown", "Committer identity unknown"))):
        identity = process(["git", "-C", str(root), "log", "-1", "--format=%an%x00%ae"])
        if identity.returncode == 0:
            name, email = identity.stdout.strip().split("\0", 1)
            env = dict(os.environ)
            for key, value in {"GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email,
                               "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": email}.items():
                env.setdefault(key, value)
            result = process(["git", "-C", str(root), *args], env=env)
    if check and result.returncode:
        raise PackageError(result.stderr.strip() or result.stdout.strip())
    return result


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    os.replace(temporary, path)


def contained(root, relative):
    path = root / relative
    if Path(relative).is_absolute() or not path.resolve().is_relative_to(root.resolve()):
        raise PackageError(f"Path escapes package: {relative}")
    return path


def files(root):
    raw = git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z").stdout
    return sorted(set(name for name in raw.split("\0") if name))


def content_digest(root, names):
    value = hashlib.sha256()
    for name in names:
        path = contained(root, name)
        value.update(name.encode("utf-8") + b"\0")
        if path.is_symlink():
            raise PackageError(f"Linked package file needs investigation: {name}")
        value.update(path.read_bytes() if path.is_file() else b"<deleted>")
        value.update(b"\0")
    return value.hexdigest()


def digest(root):
    return content_digest(root, files(root))


def snapshot(root, destination):
    names = files(root)
    for name in names:
        source = contained(root, name)
        if source.is_symlink():
            raise PackageError(f"Cannot snapshot linked file: {name}")
        if source.is_file():
            target = contained(destination, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    return names


def linked(path):
    try:
        return path.is_symlink() or bool(getattr(path.lstat(), "st_file_attributes", 0)
                                         & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    except FileNotFoundError:
        return False


def read_material(path, relative_to=None, offset=0, limit=2000, pointer=None):
    """Bounded evidence view; relative references belong to their referring file."""
    if offset < 0 or not 1 <= limit <= 6000:
        raise PackageError("Read offset must be nonnegative; limit must be 1..6000 characters")
    if relative_to is not None:
        relative_to = relative_to.resolve()
        if not relative_to.is_file():
            raise PackageError(f"Referring file does not exist: {relative_to}")
        path = relative_to.parent / path
    path = path.resolve()
    if not path.is_file():
        raise PackageError(f"Material does not exist: {path}")
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    view, items = "text", None
    if path.suffix.lower() == ".json" or pointer is not None:
        data = json.loads(text)
        if pointer is None:
            def shape(value):
                result = {"type": type(value).__name__}
                if isinstance(value, (dict, list)):
                    result["items"] = len(value)
                return result
            data = {key: shape(value) for key, value in data.items()} if isinstance(data, dict) else shape(data)
            view = "json_overview"
        else:
            if pointer and not pointer.startswith("/"):
                raise PackageError("JSON pointer must be empty or start with /")
            try:
                for token in pointer.split("/")[1:] if pointer else []:
                    token = token.replace("~1", "/").replace("~0", "~")
                    if isinstance(data, list):
                        if not re.fullmatch(r"0|[1-9][0-9]*", token):
                            raise ValueError("Invalid array index")
                        data = data[int(token)]
                    elif isinstance(data, dict):
                        data = data[token]
                    else:
                        raise ValueError("Pointer reaches a scalar")
            except (KeyError, IndexError, ValueError) as error:
                raise PackageError(f"JSON pointer not found: {pointer}") from error
            view = "json_selection"
            items = len(data) if isinstance(data, (dict, list)) else None
        text = json.dumps(data, ensure_ascii=False, indent=2)
    if offset > len(text):
        raise PackageError("Read offset exceeds the selected view")
    end = min(offset + limit, len(text))
    return {"path": str(path), "size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "view": view, "pointer": pointer, "items": items, "offset": offset,
            "text": text[offset:end], "complete": end == len(text),
            "next_offset": end if end < len(text) else None}


def resource_bytes(path, content, normalize_text=False):
    if normalize_text and Path(path).suffix.lower() in {".md", ".yaml", ".yml", ".json", ".txt", ".py", ".toml", ".ps1", ".sh"}:
        if any(byte < 32 and byte not in (9, 10, 13) or byte == 127 for byte in content):
            return content
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            return content
        return content.replace(b"\r\n", b"\n")
    return content


def upstream_inputs(install_root, names, normalize_text=False):
    versions = {}
    for name in names:
        directory = install_root / name
        if not (directory / "SKILL.md").is_file():
            versions[name] = {"path": None, "fingerprint": None}
            continue
        value = hashlib.sha256()
        resources = []
        for current, folders, filenames in os.walk(directory, followlinks=False):
            folders[:] = sorted(folder for folder in folders if folder not in {".git", "__pycache__", "node_modules", ".venv"})
            for filename in sorted(filenames):
                if filename.startswith(".env") or filename.endswith((".pyc", ".pyo")):
                    continue
                path = Path(current) / filename
                resources.append((path.relative_to(directory).as_posix(), path))
        for relative, path in sorted(resources) if normalize_text else resources:
            value.update(relative.encode("utf-8") + b"\0" + resource_bytes(path, path.read_bytes(), normalize_text))
        versions[name] = {"path": str(directory.resolve()), "fingerprint": value.hexdigest()}
    return versions


def link_directory(source, target):
    if os.name == "nt":
        try:
            target.symlink_to(source, target_is_directory=True)
            return
        except OSError:
            pass  # Ordinary Windows accounts still use the existing Junction path.
        # Arguments travel through environment, never interpolated shell code.
        env = dict(os.environ, SKILL_LINK_SOURCE=str(source), SKILL_LINK_TARGET=str(target))
        result = process(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                          "$ErrorActionPreference='Stop'; New-Item -ItemType Junction "
                          "-Path $env:SKILL_LINK_TARGET -Target $env:SKILL_LINK_SOURCE | Out-Null"],
                         env=env)
        if result.returncode:
            raise PackageError(result.stderr.strip())
    else:
        target.symlink_to(source, target_is_directory=True)


def skills_manager_cli():
    """Use the stamped desktop bridge; never fall back from a broken bridge."""
    directory = Path.home() / ".skills-manager" / "bin"
    binary = directory / ("skills-manager-cli.exe" if os.name == "nt" else "skills-manager-cli")
    stamp = directory / ".version"
    if binary.exists() or stamp.exists():
        if not binary.is_file() or not binary.stat().st_size or not stamp.is_file() or not stamp.stat().st_size:
            raise PackageError("Skills Manager bridge is incomplete; open Skills Manager to republish it")
        return str(binary)
    found = shutil.which("skills-manager-cli")
    if not found:
        raise PackageError("Skills Manager CLI is unavailable; installation remains pending")
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
        raise PackageError(value.get("message", "Skills Manager refused the operation"))
    return value


class Package:
    def __init__(self, root):
        self.root = Path(git(Path(root).resolve(), "rev-parse", "--show-toplevel").stdout.strip())
        self.policy = read_json(self.root / "skill-package.json")
        if self.policy.get("schema") != 1 or self.policy.get("publish") != "automatic":
            raise PackageError("Unsupported package policy")
        for name in self.policy["upstream_skills"]:
            if not name or name in {".", ".."} or "/" in name or "\\" in name:
                raise PackageError("Upstream names must be installed skill directory names")
        self.skills_root = contained(self.root, self.policy["skills_root"])
        if self.skills_root == self.root or self.skills_root.name == ".git":
            raise PackageError("Skills root must be a package subdirectory")
        common = git(self.root, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip()
        self.common = Path(common)
        self.state_root = self.common / "workflow-state"
        actual = git(self.root, "remote", "get-url", "origin").stdout.strip()
        if actual.rstrip("/").removesuffix(".git") != self.policy["remote"].rstrip("/").removesuffix(".git"):
            raise PackageError("Origin does not match authorized package remote")

    @contextlib.contextmanager
    def transaction(self):
        self.state_root.mkdir(parents=True, exist_ok=True)
        with (self.state_root / "lock").open("a+b") as lock:
            lock.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error:
                raise PackageError("Package transaction busy; retry after its owner finishes") from error
            try:
                yield
            finally:
                if os.name == "nt":
                    lock.seek(0)
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def discover(self):
        skills = []
        for directory in sorted(self.skills_root.iterdir()):
            if not directory.is_dir() or not (directory / "SKILL.md").is_file():
                continue
            if linked(directory) or not directory.resolve().is_relative_to(self.skills_root.resolve()):
                raise PackageError(f"Skill escapes managed root: {directory.name}")
            if directory.name in self.policy["upstream_skills"]:
                raise PackageError(f"Upstream skill cannot become managed: {directory.name}")
            content = (directory / "SKILL.md").read_text(encoding="utf-8")
            match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", content, re.S)
            if not match or not re.search(r"(?m)^name:\s*[\"']?" + re.escape(directory.name) + r"[\"']?\s*$", match[1]):
                raise PackageError(f"Skill directory/frontmatter mismatch: {directory.name}")
            if not re.search(r"(?m)^description:\s*\S", match[1]):
                raise PackageError(f"Skill description missing: {directory.name}")
            skills.append(directory.name)
        return skills

    def run_path(self, run):
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", run):
            raise PackageError("Invalid run identifier")
        return self.state_root / "runs" / run

    def load_run(self, run):
        directory = self.run_path(run)
        state = read_json(directory / "state.json")
        if Path(state["common"]).resolve() != self.common.resolve():
            raise PackageError("Run belongs to another repository")
        return directory, state

    def save_run(self, directory, state):
        write_json(directory / "state.json", state)

    def fetch(self):
        git(self.root, "fetch", "origin", self.policy["branch"])
        return git(self.root, "rev-parse", f"refs/remotes/origin/{self.policy['branch']}").stdout.strip()

    def inspect(self, install_root, manager_owned=False):
        self.discover()
        runs = []
        for state_path in sorted((self.state_root / "runs").glob("*/state.json")):
            state = read_json(state_path)
            if state["status"] != "synced":
                runs.append({"run": state_path.parent.name, "status": state["status"],
                             "worktree": state["worktree"], "attempts": state["attempts"]})
        upstream = upstream_inputs(install_root, self.policy["upstream_skills"])
        compatibility_path = self.state_root / "upstream-compatibility.json"
        prior = read_json(compatibility_path) if compatibility_path.exists() else {}
        previous = prior.get("versions", {}) if prior.get("install_root") == str(install_root.resolve()) else {}
        missing = [name for name, version in upstream.items() if not version["fingerprint"]]
        changed = [name for name, version in upstream.items()
                   if version["fingerprint"] != previous.get(name, {}).get("fingerprint")]
        return {"source": str(self.root), "head": git(self.root, "rev-parse", "HEAD").stdout.strip(),
                "dirty": bool(git(self.root, "status", "--porcelain").stdout),
                "skills": self.discover(), "pending": runs,
                "installation": self.installation(install_root, manager_owned),
                "installation_manager": "skills-manager" if manager_owned else "legacy-source-links",
                "upstream": {"versions": upstream, "changed": changed, "missing": missing,
                             "status": "unverified" if not prior or missing else "changed" if changed else "checked",
                             "confirmed_by_run": prior.get("confirmed_by_run")}}

    def installation(self, install_root, manager_owned=False):
        names = self.discover()
        expected = upstream_inputs(self.skills_root, names, normalize_text=manager_owned)
        actual = upstream_inputs(install_root, names, normalize_text=manager_owned)
        entries = {}
        for name in names:
            entry = install_root / name
            kind = ("symlink" if entry.is_symlink() else "directory_link" if linked(entry)
                    else "copy" if entry.is_dir() else "file" if entry.exists() else "missing")
            entries[name] = {"path": str(entry.absolute()), "kind": kind,
                             "target": str(entry.resolve()),
                             "expected_target": str(entry.absolute() if manager_owned else (self.skills_root / name).resolve()),
                             "source": str((self.skills_root / name).resolve()),
                             "matches_source": actual[name]["fingerprint"] == expected[name]["fingerprint"]}
        return entries

    def structure(self, validator, validation_python):
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

    def prepare(self, run, existing_worktree=None, install_root=None):
        directory = self.run_path(run)
        if (directory / "state.json").exists():
            state = self.load_run(run)[1]
            if state["status"] not in {"preparing", "prepare_failed"}:
                return state
            if state.get("worktree") and (Path(state["worktree"]) / ".git").exists():
                state["status"] = "prepared"
                self.save_run(directory, state)
                return state
            if not state.get("runtime") or not state.get("source_files"):
                raise PackageError("Incomplete preparation snapshot; preserve it and start a new run")
            if content_digest(directory / "source-snapshot", state["source_files"]) != state["source_digest"]:
                raise PackageError("Preparation snapshot changed; preserve it and start a new run")
            primary = Path(state["source"])
        else:
            directory.mkdir(parents=True, exist_ok=True)
            primary_text = git(self.root, "worktree", "list", "--porcelain", "-z").stdout.split("\0")[0]
            primary = Path(primary_text.removeprefix("worktree "))
            state = {"common": str(self.common), "source": str(primary), "status": "preparing",
                     "attempts": 0, "policy": self.policy, "source_head": git(primary, "rev-parse", "HEAD").stdout.strip(),
                     "source_digest": digest(primary), "worktree": ""}
            self.save_run(directory, state)
        try:
            if not state.get("runtime"):
                state["source_files"] = snapshot(primary, directory / "source-snapshot")
                state["source_index_tree"] = git(primary, "write-tree").stdout.strip()
                git(primary, "update-ref", f"refs/workflow-snapshots/{run}/index", state["source_index_tree"])
                (directory / "source.patch").write_text(git(primary, "diff", "--binary", "HEAD").stdout,
                                                          encoding="utf-8")
                execution = directory / "execution"
                snapshot(self.root, execution)
                runtime = execution / "tools" / "skill_package.py"
                runtime.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(Path(__file__), runtime)
                state["runtime"] = str(runtime)
                state["entry"] = str(execution / self.policy["skills_root"] / "improve-workflow" / "SKILL.md")
                if install_root is not None:
                    state["upstream"] = upstream_inputs(install_root, self.policy["upstream_skills"])
                    for name, version in state["upstream"].items():
                        if version["path"]:
                            shutil.copytree(version["path"], directory / "upstream-inputs" / name,
                                            ignore=shutil.ignore_patterns(".git", "__pycache__", "node_modules", ".venv", ".env*", "*.pyc", "*.pyo"), symlinks=True)
                    if upstream_inputs(install_root, self.policy["upstream_skills"]) != state["upstream"]:
                        raise PackageError("Upstream changed during snapshot; preserve it and start a new run")
                if digest(primary) != state["source_digest"]:
                    raise PackageError("Source changed during snapshot; protect the new state in a new run")
                self.save_run(directory, state)
            state["base"] = self.fetch()
            if existing_worktree:
                worktree = Path(existing_worktree).resolve()
                if Path(git(worktree, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip()).resolve() != self.common.resolve():
                    raise PackageError("Existing worktree belongs to another repository")
                branch = git(worktree, "branch", "--show-current").stdout.strip()
                if not branch.startswith("codex/") or worktree == primary.resolve():
                    raise PackageError("Adoption requires an isolated codex/ worktree")
                if git(worktree, "merge-base", "--is-ancestor", state["base"], "HEAD", check=False).returncode:
                    raise PackageError("Existing worktree must include latest main")
            else:
                worktree = directory / "worktree"
                state["worktree"] = str(worktree)
                self.save_run(directory, state)
                git(self.root, "worktree", "add", "-b", "codex/" + run, str(worktree), state["base"])
            state.update(worktree=str(worktree), status="prepared")
        except (PackageError, OSError) as error:
            state.update(status="prepare_failed", error=str(error))
            self.save_run(directory, state)
            raise
        self.save_run(directory, state)
        return state

    def verify(self, run, checked_upstream=None):
        directory, state = self.load_run(run)
        worktree = Path(state["worktree"])
        candidate = Package(worktree)
        protected = ("schema", "remote", "branch", "skills_root", "publish", "authorization")
        if any(candidate.policy.get(key) != state["policy"].get(key) for key in protected):
            raise PackageError("Package policy changed; requires an explicit user decision before a new run")
        if not set(state["policy"]["upstream_skills"]).issubset(candidate.policy["upstream_skills"]):
            raise PackageError("Upstream protection reduced; requires an explicit user decision")
        candidate.discover()
        before = digest(worktree)
        if state.get("verified_digest") != before:
            state["upstream_evaluated"] = {}
        if checked_upstream is not None:
            for name in checked_upstream:
                version = state.get("upstream", {}).get(name)
                if not version or not version["fingerprint"]:
                    raise PackageError(f"No saved upstream input to acknowledge: {name}")
                state.setdefault("upstream_evaluated", {})[name] = version
        checks = [{"command": ["package-discovery"], "exit_code": 0}]
        env = dict(os.environ, SKILL_PACKAGE_CANDIDATE=str(worktree), PYTHONDONTWRITEBYTECODE="1")
        changed = set(filter(None, git(worktree, "diff", "--name-only", "-z", state["base"]).stdout.split("\0")))
        changed.update(filter(None, git(worktree, "ls-files", "--others", "--exclude-standard", "-z").stdout.split("\0")))
        needs_regression = any(not (name == "README.md" or
                                   (name.startswith(self.policy["skills_root"] + "/") and
                                    name.endswith((".md", ".yaml")))) for name in changed)
        commands = [[sys.executable if arg == "{python}" else arg for arg in command]
                    for command in state["policy"]["checks"]] if needs_regression else []
        if needs_regression:
            for command in candidate.policy["checks"]:
                resolved = [sys.executable if arg == "{python}" else arg for arg in command]
                if resolved not in commands:
                    commands.append(resolved)
        frozen_tests = directory / "execution" / "tests"
        if needs_regression and frozen_tests.is_dir():
            commands.append([sys.executable, "-m", "unittest", "discover", "-s", str(frozen_tests), "-v"])
        state.update(status="verifying", verified_digest=None)
        self.save_run(directory, state)
        for index, command in enumerate(commands):
            result = process(command, cwd=worktree, env=env, timeout=900)
            log = directory / f"check-{index}.log"
            log.write_text(result.stdout + result.stderr, encoding="utf-8")
            checks.append({"command": command, "exit_code": result.returncode, "log": str(log)})
        valid = all(item["exit_code"] == 0 for item in checks) and digest(worktree) == before
        state.update(status="verified" if valid else "verification_failed", checks=checks,
                     verified_digest=before if valid else None)
        self.save_run(directory, state)
        return {"status": state["status"], "checks": checks, "digest": state["verified_digest"]}

    def publish(self, run):
        directory, state = self.load_run(run)
        worktree = Path(state["worktree"])
        if state.get("published"):
            return {"status": "published", "commit": state["published"], "already_published": True}
        if state.get("verified_digest") != digest(worktree):
            raise PackageError("Final content needs verification")
        if git(worktree, "status", "--porcelain").stdout:
            raise PackageError("Agent must commit the explicit authorized files before publishing")
        if state["attempts"] >= 3:
            return {"status": "pending", "reason": "Three publication attempts used; resume in a later invocation", "worktree": str(worktree)}
        latest = self.fetch()
        if git(worktree, "merge-base", "--is-ancestor", latest, "HEAD", check=False).returncode:
            result = git(worktree, "merge", "--no-edit", latest, check=False)
            state.update(status="needs_verification" if result.returncode == 0 else "conflict", verified_digest=None)
            self.save_run(directory, state)
            return {"status": state["status"], "worktree": str(worktree), "details": result.stdout + result.stderr}
        head = git(worktree, "rev-parse", "HEAD").stdout.strip()
        if head == latest:
            state.update(status="published", published=head)
            self.save_run(directory, state)
            return {"status": "published", "commit": head, "no_change": True}
        state["attempts"] += 1
        state["status"] = "publishing"
        self.save_run(directory, state)
        result = git(worktree, "push", "origin", f"HEAD:refs/heads/{state['policy']['branch']}", check=False)
        if result.returncode:
            state.update(status="pending", error=result.stderr)
            self.save_run(directory, state)
            return {"status": "pending", "worktree": str(worktree), "attempts": state["attempts"], "details": result.stderr}
        # Persist acknowledgement before further network or installation operations.
        state.update(status="published", published=head)
        self.save_run(directory, state)
        observed = self.fetch()
        if git(worktree, "merge-base", "--is-ancestor", head, observed, check=False).returncode:
            raise PackageError("Remote no longer contains published commit")
        return {"status": "published", "commit": head, "remote": observed}

    def resume(self, run):
        directory, state = self.load_run(run)
        if state["status"] in {"preparing", "prepare_failed"}:
            return self.prepare(run)
        if state.get("published"):
            return state
        latest = self.fetch()
        worktree = Path(state["worktree"])
        head = git(worktree, "rev-parse", "HEAD").stdout.strip()
        if not git(worktree, "status", "--porcelain").stdout and not git(worktree, "merge-base", "--is-ancestor", head, latest, check=False).returncode:
            state.update(status="published", published=head)
        else:
            state.update(status="prepared", attempts=0)
        self.save_run(directory, state)
        return state

    def sync(self, install_root, run=None, reconcile_source=False, adopt_copies=False, source_only=False):
        directory, state = self.load_run(run) if run else (None, None)
        if state and not state.get("published"):
            raise PackageError("Run has not been published; preserve it pending and synchronize independently")
        primary_text = git(self.root, "worktree", "list", "--porcelain", "-z").stdout.split("\0")[0]
        primary = Path(primary_text.removeprefix("worktree "))
        if git(primary, "branch", "--show-current").stdout.strip() != self.policy["branch"]:
            raise PackageError("Stable source is not on the configured main branch")
        latest = self.fetch()
        if state and git(primary, "merge-base", "--is-ancestor", state["published"], latest, check=False).returncode:
            raise PackageError("Remote does not contain this run's published commit")
        current = git(primary, "rev-parse", "HEAD").stdout.strip()
        if git(primary, "merge-base", "--is-ancestor", current, latest, check=False).returncode:
            raise PackageError("Stable main has unpublished or divergent commits; preserve and migrate them before syncing")
        if git(primary, "status", "--porcelain").stdout:
            if not reconcile_source or not state or not state.get("published"):
                raise PackageError("Dirty stable source preserved; prepare and reconcile its snapshot first")
            if git(primary, "rev-parse", "HEAD").stdout.strip() != state["source_head"] or digest(primary) != state["source_digest"]:
                raise PackageError("Stable source changed since snapshot; preserve new work before syncing")
            if content_digest(directory / "source-snapshot", state["source_files"]) != state["source_digest"]:
                raise PackageError("Source snapshot is incomplete or changed; preserve originals before syncing")
            # The agent explicitly accounted for the snapshot's delta before opting in.
            tracked = git(primary, "ls-files", "-z").stdout.split("\0")
            tracked = [name for name in tracked if name]
            if tracked:
                git(primary, "restore", "--source=HEAD", "--staged", "--worktree", "--", *tracked)
            untracked = git(primary, "ls-files", "--others", "--exclude-standard", "-z").stdout.split("\0")
            for name in filter(None, untracked):
                path = contained(primary, name)
                backup = contained(directory / "source-snapshot", name)
                if not backup.is_file() or backup.read_bytes() != path.read_bytes():
                    raise PackageError(f"Untracked snapshot mismatch: {name}")
                path.unlink()
        git(primary, "merge", "--ff-only", latest)
        if git(primary, "rev-parse", "HEAD").stdout.strip() != latest:
            raise PackageError("Stable source does not equal the selected remote revision")
        stable = Package(primary)
        skills = stable.discover()
        if source_only:
            if state:
                state.update(status="source_synced", source_synced=latest)
                self.save_run(directory, state)
            return {"status": "source_synced", "commit": latest, "source": str(primary),
                    "skills": skills, "next": "Skills Manager update/deploy, then confirm-install"}
        # Compatibility for frozen pre-migration Python callers and their saved regressions.
        # The current CLI always uses source_only and never enters this legacy installer.
        install_root = install_root.absolute()
        if install_root.resolve().is_relative_to(primary.resolve()):
            raise PackageError("Installation root must be outside the package source")
        install_root.mkdir(parents=True, exist_ok=True)
        backup_root = install_root.parent / "skill-install-backups" / (run or uuid.uuid4().hex)
        installed = []
        for name in skills:
            source = stable.skills_root / name
            target = install_root / name
            if target.resolve() == source.resolve() and linked(target):
                installed.append(name)
                continue
            backup = backup_root / name
            if target.exists() or linked(target):
                if not linked(target):
                    if not adopt_copies:
                        raise PackageError(f"Installed copy preserved: compare {target}, then sync with adopt-copies")
                else:
                    old_target = target.resolve()
                    if not old_target.is_relative_to(primary.resolve()) and not old_target.is_relative_to(self.state_root.resolve()):
                        raise PackageError(f"Foreign installation link preserved: {target}")
                backup.parent.mkdir(parents=True, exist_ok=True)
                if backup.exists() or linked(backup):
                    raise PackageError(f"Backup already exists: {backup}")
                target.rename(backup)  # Move the entry itself, never its target tree.
            try:
                link_directory(source, target)
            except (OSError, PackageError):
                if linked(target) and target.resolve() == source.resolve():
                    if target.is_symlink():
                        target.unlink()
                    else:
                        target.rmdir()
                if backup.exists() and not target.exists():
                    backup.rename(target)
                raise
            if target.resolve() != source.resolve() or not (target / "SKILL.md").is_file():
                raise PackageError(f"Installation verification failed: {target}")
            installed.append(name)
        if state:
            state.update(status="synced", synced=latest, installed=installed)
            if state.get("upstream_evaluated"):
                current_upstream = upstream_inputs(install_root, state["policy"]["upstream_skills"])
                compatibility_path = self.state_root / "upstream-compatibility.json"
                prior = read_json(compatibility_path) if compatibility_path.exists() else {}
                versions = prior.get("versions", {}) if prior.get("install_root") == str(install_root.resolve()) else {}
                for name, evaluated in state["upstream_evaluated"].items():
                    if current_upstream.get(name) == evaluated:
                        versions[name] = evaluated
                write_json(compatibility_path,
                           {"install_root": str(install_root.resolve()), "versions": versions,
                            "confirmed_by_run": run})
            self.save_run(directory, state)
        return {"status": "synced", "commit": latest, "source": str(primary), "installed": installed}

    def manager_source(self, record, library, metadata_root, name):
        entry = library / name
        if not record or Path(record["path"]).resolve() != entry.resolve():
            raise PackageError(f"Skills Manager does not own the expected library entry: {name}")
        reference = record.get("source_ref", "").rstrip("/").removesuffix(".git")
        remote = self.policy["remote"].rstrip("/").removesuffix(".git")
        local_source = record.get("source_type") == "local" and Path(reference).resolve() == (self.skills_root / name).resolve()
        skill_reference = f"{remote}/tree/{self.policy['branch']}/{Path(self.policy['skills_root']).as_posix()}/{name}"
        if not local_source and (record.get("source_type") != "git" or reference not in {remote, skill_reference}):
            raise PackageError(f"Skills Manager source differs from the maintenance source: {name}")
        metadata_path = contained(metadata_root, record["id"] + ".json")
        if not metadata_path.is_file():
            raise PackageError(f"Skills Manager source metadata is missing: {name}")
        metadata = read_json(metadata_path)
        source = metadata.get("source", {})
        if (metadata.get("skill_id") != record["id"] or metadata.get("path") != name
                or source.get("type") != record.get("source_type")
                or source.get("ref") != record.get("source_ref")):
            raise PackageError(f"Skills Manager source metadata disagrees with the registry: {name}")
        if not local_source:
            subpath = str(source.get("subpath", "")).replace("\\", "/").strip("/")
            if subpath != (Path(self.policy["skills_root"]) / name).as_posix():
                raise PackageError(f"Skills Manager source subpath differs: {name}")
            branch = source.get("branch")
            if branch is None:
                remote_head = git(self.root, "ls-remote", "--symref", self.policy["remote"], "HEAD").stdout
                match = re.search(r"(?m)^ref: refs/heads/(.+)\tHEAD$", remote_head)
                if not match:
                    raise PackageError("Cannot verify the default branch used by Skills Manager")
                branch = match[1]
            if branch != self.policy["branch"]:
                raise PackageError(f"Skills Manager source branch differs: {name}")

    def known_skill_version(self, name, fingerprint):
        """Accept only complete committed versions before a wholesale manager update."""
        prefix = (Path(self.policy["skills_root"]) / name).as_posix() + "/"
        revisions = git(self.root, "rev-list", "HEAD", "--", prefix).stdout.splitlines()
        for revision in revisions:
            tree = git(self.root, "ls-tree", "-r", "-z", revision, "--", prefix).stdout
            resources = []
            for row in filter(None, tree.split("\0")):
                header, path = row.split("\t", 1)
                mode, kind, object_id = header.split()
                if mode not in {"100644", "100755"} or kind != "blob":
                    raise PackageError(f"Linked or unsupported committed skill resource: {path}")
                relative = path.removeprefix(prefix)
                if any(part in {".git", "__pycache__", "node_modules", ".venv"} for part in Path(relative).parts[:-1]) or Path(relative).name.startswith(".env") or relative.endswith((".pyc", ".pyo")):
                    continue
                blob = subprocess.run(["git", "-C", str(self.root), "cat-file", "blob", object_id],
                                      capture_output=True, timeout=120)
                if blob.returncode:
                    raise PackageError(f"Cannot read committed skill resource: {path}")
                resources.append((relative, blob.stdout))
            value = hashlib.sha256()
            for relative, content in sorted(resources):
                value.update(relative.encode("utf-8") + b"\0" + resource_bytes(relative, content, True))
            if value.hexdigest() == fingerprint:
                return True
        return False

    def sync_manager(self, cli, run=None, reconcile_source=False, deploy_new_to=()):
        repository = manager_json(cli, "repo", "status")
        library = Path(repository["skills_dir"])
        synchronized = self.sync(library, run, reconcile_source, source_only=True)
        stable = Package(Path(synchronized["source"]))
        records = {record["name"]: record for record in manager_json(cli, "skills", "list")}
        agents = {agent["key"]: agent for agent in manager_json(cli, "agents", "list")}
        for key in deploy_new_to:
            if key not in agents or not agents[key].get("skills_dir"):
                raise PackageError(f"Unknown new-skill deployment agent: {key}")
        names = stable.discover()
        expected = upstream_inputs(stable.skills_root, names, normalize_text=True)
        actual = upstream_inputs(library, names, normalize_text=True)
        metadata_root = Path(repository["metadata_dir"]) / "skills"
        directory, state = self.load_run(run) if run else (None, None)
        intent_path = self.state_root / "pending-manager-deployments.json"
        if state:
            intents = state.get("manager_new_deployments", {})
        elif intent_path.exists():
            pending = read_json(intent_path)
            if Path(pending["library"]).resolve() != library.resolve():
                raise PackageError("Pending deployment intent belongs to another manager library")
            intents = pending["skills"]
        else:
            intents = {}
        for name in names:
            if name not in records:
                intents.setdefault(name, list(deploy_new_to))
        if intents:
            if state:
                state["manager_new_deployments"] = intents
                self.save_run(directory, state)
            else:
                write_json(intent_path, {"library": str(library.resolve()), "skills": intents})
        # Preflight the whole batch before changing the shared central library.
        for name in names:
            if name in records:
                stable.manager_source(records[name], library, metadata_root, name)
                if not stable.known_skill_version(name, actual[name]["fingerprint"]):
                    raise PackageError(f"Uncommitted manager library changes preserved: {name}; compare and migrate them before updating")
                for key in records[name].get("deployed_to", []):
                    if key not in agents or not agents[key].get("skills_dir"):
                        raise PackageError(f"Unknown managed deployment agent: {key}")
                    root = Path(agents[key]["skills_dir"])
                    target = root / name
                    if linked(target) and target.resolve() != (library / name).resolve():
                        raise PackageError(f"Foreign managed deployment link preserved: {key}/{name}")
                    fingerprint = upstream_inputs(root, [name], normalize_text=True)[name]["fingerprint"]
                    if fingerprint is not None and not stable.known_skill_version(name, fingerprint):
                        raise PackageError(f"Uncommitted Agent deployment changes preserved: {key}/{name}")
            elif (library / name).exists() or linked(library / name):
                raise PackageError(f"Unmanaged library entry preserved: {name}")
        for name in names:
            record = records.get(name)
            if record:
                if actual[name]["fingerprint"] != expected[name]["fingerprint"]:
                    manager_json(cli, "skills", "check", record["id"])
                    result = manager_json(cli, "skills", "update", record["id"])
                    reports = result if isinstance(result, list) else [result]
                    held = [path for report in reports for path in report.get("held_back_removals", [])]
                    if held:
                        raise PackageError(f"Skills Manager held back removals for {name}: {held}; installation remains pending")
                selected = tuple(sorted(set(record.get("deployed_to", [])) | set(intents.get(name, []))))
            else:
                reference = f"{stable.policy['remote'].removesuffix('.git')}/tree/{stable.policy['branch']}/{Path(stable.policy['skills_root']).as_posix()}/{name}"
                manager_json(cli, "skills", "install", reference, "--git")
                selected = tuple(intents.get(name, []))
            if selected:
                args = ["skills", "deploy", name]
                for key in selected:
                    args.extend(("--agent", key))
                manager_json(cli, *args, "--dry-run")
                manager_json(cli, *args)
        updated = {record["name"]: record for record in manager_json(cli, "skills", "list")}
        for name, previous in records.items():
            if name in names:
                current = updated.get(name, {})
                if (current.get("id") != previous["id"] or set(current.get("deployed_to", [])) != set(previous.get("deployed_to", [])) | set(intents.get(name, []))
                        or set(current.get("preset_ids", [])) != set(previous.get("preset_ids", [])) or set(current.get("tags", [])) != set(previous.get("tags", []))):
                    raise PackageError(f"Skills Manager changed existing identity or deployment choices: {name}")
        for name, selected in intents.items():
            if name not in names or not set(selected).issubset(updated.get(name, {}).get("deployed_to", [])):
                raise PackageError(f"New skill deployment intent remains pending: {name}")
        result = stable.confirm_install(cli, run)
        if state:
            directory, completed = self.load_run(run)
            completed.pop("manager_new_deployments", None)
            self.save_run(directory, completed)
        elif intent_path.exists():
            intent_path.unlink()
        return result

    def confirm_install(self, cli, run=None):
        """Acknowledge manager-owned files only after inspecting the real library and deployments."""
        directory, state = self.load_run(run) if run else (None, None)
        if state and not state.get("published"):
            raise PackageError("Run has not been published; installation cannot close it")
        head = git(self.root, "rev-parse", "HEAD").stdout.strip()
        if git(self.root, "branch", "--show-current").stdout.strip() != self.policy["branch"] or git(self.root, "status", "--porcelain").stdout:
            raise PackageError("Confirm installation from the clean stable maintenance source")
        if state and (git(self.root, "merge-base", "--is-ancestor", state["published"], head, check=False).returncode
                      or state.get("source_synced", head) != head):
            raise PackageError("Stable source does not match this run's synchronized publication")
        repository = manager_json(cli, "repo", "status")
        library = Path(repository["skills_dir"])
        metadata_root = Path(repository["metadata_dir"]) / "skills"
        records = {record["name"]: record for record in manager_json(cli, "skills", "list")}
        agents = {agent["key"]: agent for agent in manager_json(cli, "agents", "list")}
        names = self.discover()
        expected = upstream_inputs(self.skills_root, names, normalize_text=True)
        actual = upstream_inputs(library, names, normalize_text=True)
        deployments = {}
        for name in names:
            record = records.get(name)
            entry = library / name
            self.manager_source(record, library, metadata_root, name)
            if actual[name]["fingerprint"] != expected[name]["fingerprint"]:
                raise PackageError(f"Manager library is missing or differs from the maintenance source: {name}")
            deployments[name] = []
            for key in record.get("deployed_to", []):
                if key not in agents:
                    raise PackageError(f"Unknown managed deployment agent: {key}")
                root = Path(agents[key]["skills_dir"])
                target = root / name
                fingerprint = upstream_inputs(root, [name], normalize_text=True)[name]["fingerprint"]
                if fingerprint != expected[name]["fingerprint"] or (linked(target) and target.resolve() != entry.resolve()):
                    raise PackageError(f"Managed deployment is missing, stale or points elsewhere: {key}/{name}")
                deployments[name].append(key)
        intents = state.get("manager_new_deployments", {}) if state else {}
        intent_path = self.state_root / "pending-manager-deployments.json"
        if intent_path.exists():
            pending = read_json(intent_path)
            if Path(pending["library"]).resolve() == library.resolve():
                for name, selected in pending["skills"].items():
                    intents = dict(intents)
                    intents[name] = sorted(set(intents.get(name, [])) | set(selected))
        for name, selected in intents.items():
            if name not in deployments or not set(selected).issubset(deployments[name]):
                raise PackageError(f"New skill deployment intent remains pending: {name}")
        if state:
            state.update(status="synced", synced=head, installed=names, deployments=deployments,
                         installation_manager="skills-manager")
            evaluated = state.get("upstream_evaluated", {})
            current = upstream_inputs(library, self.policy["upstream_skills"])
            compatibility = self.state_root / "upstream-compatibility.json"
            prior = read_json(compatibility) if compatibility.exists() else {}
            versions = prior.get("versions", {}) if prior.get("install_root") == str(library.resolve()) else {}
            for name, version in evaluated.items():
                if current.get(name) == version:
                    versions[name] = version
            if evaluated:
                write_json(compatibility, {"install_root": str(library.resolve()), "versions": versions,
                                           "confirmed_by_run": run})
            self.save_run(directory, state)
        return {"status": "synced", "commit": head, "source": str(self.root), "library": str(library),
                "installation_manager": "skills-manager", "installed": names, "deployments": deployments}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["inspect", "read", "structure", "prepare", "verify", "publish", "resume", "sync", "sync-manager", "confirm-install"])
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--run")
    parser.add_argument("--existing-worktree", type=Path)
    parser.add_argument("--install-root", type=Path, default=Path.home() / ".skills-manager" / "skills")
    parser.add_argument("--skills-manager-cli", type=Path, help="Resolved Skills Manager CLI for confirmation")
    parser.add_argument("--deploy-new-to", action="append", default=[], help="Explicit Agent for newly installed skills; repeat for multiple Agents")
    parser.add_argument("--reconcile-source", action="store_true")
    parser.add_argument("--adopt-copies", action="store_true")
    parser.add_argument("--checked-upstream", nargs="*", help="Dependencies whose saved contracts the agent evaluated")
    parser.add_argument("--file", type=Path)
    parser.add_argument("--relative-to", type=Path, help="Resolve --file against this referring file's directory")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=2000, help="Maximum 6000 characters per read view")
    parser.add_argument("--pointer", help="JSON pointer; omit for overview, empty string selects the root")
    parser.add_argument("--validator", type=Path)
    parser.add_argument("--validation-python", type=Path)
    args = parser.parse_args()
    try:
        if args.action == "read":
            if args.file is None:
                raise PackageError("read needs --file")
            result = read_material(args.file, args.relative_to, args.offset, args.limit, args.pointer)
            print(json.dumps(result, ensure_ascii=False))
            return 0
        package = Package(args.source)
        if args.action not in {"inspect", "structure", "sync", "sync-manager", "confirm-install"} and not args.run:
            raise PackageError("This action needs a run identifier")
        if args.run and args.action in {"verify", "publish", "resume", "sync", "sync-manager"}:
            runtime = Path(package.load_run(args.run)[1]["runtime"]).resolve()
            if Path(__file__).resolve() != runtime:
                raise PackageError(f"Use the pinned execution tool for this run: {runtime}")
        with package.transaction():
            if args.action == "inspect":
                result = package.inspect(args.install_root, manager_owned=True)
            elif args.action == "structure":
                if args.validator is None or args.validation_python is None:
                    raise PackageError("structure needs --validator and --validation-python")
                result = package.structure(args.validator, args.validation_python)
            elif args.action == "prepare":
                result = package.prepare(args.run, args.existing_worktree, args.install_root)
            elif args.action == "sync":
                if args.adopt_copies:
                    raise PackageError("Skills Manager owns installation; adopt copies through manage-skills")
                result = package.sync(args.install_root, args.run, args.reconcile_source, source_only=True)
            elif args.action == "confirm-install":
                result = package.confirm_install(args.skills_manager_cli or skills_manager_cli(), args.run)
            elif args.action == "sync-manager":
                result = package.sync_manager(args.skills_manager_cli or skills_manager_cli(), args.run,
                                              args.reconcile_source, args.deploy_new_to)
            elif args.action == "verify":
                result = package.verify(args.run, args.checked_upstream)
            else:
                result = getattr(package, args.action)(args.run)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get("status", "ok") in {"ok", "prepared", "verified", "published", "source_synced", "synced"} else 2
    except (PackageError, OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"status": "blocked", "error": str(error)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
