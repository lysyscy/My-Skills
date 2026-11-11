"""Use the fixed artifact runtime and enrolled output root of this checkout."""
from pathlib import Path
import subprocess
import sys


PROJECT = Path(__file__).resolve().parents[1]
RUNTIME = PROJECT / 'tools/_vendor/setup_solo_workflow/artifact_lifecycle.py'
OUTPUT = PROJECT / '.artifacts/runs'


def main(argv):
    if not argv:
        raise SystemExit('action required')
    action, *args = argv
    own_args = args[:args.index('--')] if '--' in args else args
    if any(arg.split('=', 1)[0] in {'--r', '--ro', '--roo', '--root'} for arg in own_args):
        raise SystemExit('Project output root is fixed')
    if action == 'enroll':
        raise SystemExit('Use setup to enroll the output root for this checkout')
    return subprocess.run(
        [sys.executable, '-B', str(RUNTIME), action, '--root', str(OUTPUT), *args],
        check=False,
    ).returncode


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
