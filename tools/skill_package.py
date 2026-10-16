#!/usr/bin/env python3
"""Read-only checks for a skill source and Skills Manager installations.

Git publishes the source; Skills Manager owns updates and deployment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class PackageError(RuntimeError):
    pass


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
        self.skills_root = contained(self.root, self.policy["skills_root"])
        if self.skills_root == self.root or self.skills_root.name == ".git":
            raise PackageError("Skills root must be a package subdirectory")
        actual = git(self.root, "remote", "get-url", "origin")
        if actual.rstrip("/").removesuffix(".git") != self.policy["remote"].rstrip("/").removesuffix(".git"):
            raise PackageError("Origin does not match authorized package remote")

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
        if not skills:
            raise PackageError("No skills found in the authorized source")
        return skills

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

    def manager_source(self, record, library, metadata_root, name):
        entry = library / name
        if not record or Path(record["path"]).resolve() != entry.resolve() or linked(entry):
            raise PackageError(f"Skills Manager does not own the expected library entry: {name}")
        reference = record.get("source_ref", "").rstrip("/").removesuffix(".git")
        remote = self.policy["remote"].rstrip("/").removesuffix(".git")
        tree_reference = f"{remote}/tree/{self.policy['branch']}/{Path(self.policy['skills_root']).as_posix()}"
        if record.get("source_type") != "git" or reference not in {remote, tree_reference, tree_reference + "/" + name}:
            raise PackageError(f"Skills Manager source differs from the maintenance source: {name}")
        metadata = read_json(contained(metadata_root, record["id"] + ".json"))
        source = metadata.get("source", {})
        if (metadata.get("skill_id") != record["id"] or metadata.get("path") != name
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

    @staticmethod
    def selection(record):
        for key in ("tags", "preset_ids", "deployed_to"):
            if not isinstance(record.get(key, []), list) or any(not isinstance(value, str) for value in record.get(key, [])):
                raise PackageError(f"Invalid Manager selection: {key}")
        return {"id": record["id"], **{key: sorted(record.get(key, []))
                for key in ("tags", "preset_ids", "deployed_to")}}

    @staticmethod
    def deployment(agents, key, name, library):
        if key not in agents or not agents[key].get("skills_dir"):
            raise PackageError(f"Unknown managed deployment agent: {key}")
        target = Path(agents[key]["skills_dir"]) / name
        if linked(target) and target.resolve() != (library / name).resolve():
            raise PackageError(f"Foreign managed deployment link preserved: {key}/{name}")
        return target

    def preflight(self, cli, revision):
        self.require_revision(revision)
        library, metadata_root, records, agents = self.manager_context(cli)
        selections = {}
        for name in self.discover():
            record = records.get(name)
            if record is None:
                if (library / name).exists() or linked(library / name):
                    raise PackageError(f"Unmanaged library entry preserved: {name}")
                selections[name] = {"id": None, "tags": [], "preset_ids": [], "deployed_to": []}
                continue
            self.manager_source(record, library, metadata_root, name)
            if not self.known_skill_version(name, directory_fingerprint(library / name)):
                raise PackageError(f"Unknown library edits preserved: {name}")
            selections[name] = self.selection(record)
            for key in selections[name]["deployed_to"]:
                target = self.deployment(agents, key, name, library)
                if (target.exists() or linked(target)) and not self.known_skill_version(name, directory_fingerprint(target)):
                    raise PackageError(f"Unknown Agent edits preserved: {key}/{name}")
        return {"status": "preflight_ok", "revision": revision, "source": str(self.root),
                "library": str(library), "skills": selections}

    def confirm_install(self, cli, revision, plan):
        self.require_revision(revision)
        library, metadata_root, records, agents = self.manager_context(cli)
        names = self.discover()
        if (plan.get("status") != "preflight_ok" or plan.get("revision") != revision
                or plan.get("source") != str(self.root) or plan.get("library") != str(library)
                or set(plan.get("skills", {})) != set(names)):
            raise PackageError("Update plan does not match this source, revision, library and skill set")
        deployments = {}
        for name in names:
            record = records.get(name)
            self.manager_source(record, library, metadata_root, name)
            previous, current = plan["skills"][name], self.selection(record)
            if (not isinstance(previous, dict) or set(previous) != {"id", "tags", "preset_ids", "deployed_to"}
                    or (previous["id"] is not None and not isinstance(previous["id"], str))):
                raise PackageError(f"Incomplete or invalid update selection: {name}")
            previous = self.selection(previous)
            if any(current[key] != value for key, value in previous.items() if key != "id" or value is not None):
                raise PackageError(f"Identity or deployment choices changed: {name}")
            expected = self.committed_fingerprint(revision, name)
            if directory_fingerprint(library / name) != expected:
                raise PackageError(f"Manager library differs from the verified revision: {name}")
            deployments[name] = current["deployed_to"]
            for key in deployments[name]:
                target = self.deployment(agents, key, name, library)
                if directory_fingerprint(target) != expected:
                    raise PackageError(f"Managed deployment is missing or stale: {key}/{name}")
        return {"status": "installation_verified", "revision": revision, "library": str(library),
                "deployments": deployments, "scope": "local files; host loading and other devices not checked"}

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
            if self.committed_fingerprint(head, name, library) != self.committed_fingerprint(revision, name):
                raise PackageError(f'Manager backup omits or changes skill resources: {name}')
            relative = (metadata / (records[name]['id'] + '.json')).relative_to(library).as_posix()
            if json.loads(git(library, 'show', f'{head}:{relative}')) != read_json(library / relative):
                raise PackageError(f'Manager backup source metadata differs: {name}')
        return dict(source, status='distribution_verified', backup_revision=head,
                    deployments=installation['deployments'],
                    cross_device_detection='requires_receiver_verification' if portable_revisions else 'needs_calibration_after_restore',
                    receiver_action='After restore, use official Manager update for affected skills, then check; unknown is not up-to-date',
                    scope='published source CI, local deployments, pushed portable backup; other physical devices not checked')


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["structure", "preflight", "confirm-install", "confirm-source", "confirm-distribution"])
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--revision", help="Full verified commit SHA for installation checks")
    parser.add_argument("--skills-manager-cli", type=Path)
    parser.add_argument("--plan", type=Path, help="Saved preflight JSON, with any explicitly authorized new deployment choices")
    parser.add_argument("--validator", type=Path)
    parser.add_argument("--validation-python", type=Path)
    args = parser.parse_args()
    try:
        package = Package(args.source)
        if args.action == "structure":
            if args.validator is None or args.validation_python is None:
                raise PackageError("structure needs --validator and --validation-python")
            result = package.structure(args.validator, args.validation_python)
        else:
            if args.revision is None:
                raise PackageError("Installation checks need --revision")
            cli = args.skills_manager_cli or skills_manager_cli()
            if args.action == 'confirm-source':
                result = package.confirm_source(args.revision)
            elif args.action == "preflight":
                result = package.preflight(cli, args.revision)
            else:
                if args.plan is None:
                    raise PackageError("confirm-install needs --plan from the update preflight")
                check = package.confirm_distribution if args.action == 'confirm-distribution' else package.confirm_install
                result = check(cli, args.revision, read_json(args.plan))
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["status"] in {"verified", "preflight_ok", "installation_verified", "source_verified", "distribution_verified"} else 1
    except (PackageError, OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"status": "blocked", "error": str(error)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
