"""Find Windows process command lines that refer to worktrees."""
import json
from pathlib import Path
import re
import subprocess
import sys


def _mentions_path(command: str, path: Path) -> bool:
    needle = re.escape(path.as_posix().rstrip('/').casefold())
    return bool(re.search(rf'(?:^|[\s"\'=,;(]){needle}(?:$|[\s"\'/,;)\]])', command))


def process_references(paths: list[Path]) -> dict:
    if sys.platform != 'win32':
        return {'checked': False, 'error': 'Windows process inspection is unavailable'}
    script = (
        "$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[Text.UTF8Encoding]::new(); "
        "ConvertTo-Json -Compress -InputObject @(Get-CimInstance Win32_Process | "
        "Select-Object ProcessId,Name,CommandLine)"
    )
    try:
        output = subprocess.run(
            ['powershell.exe', '-NoProfile', '-Command', script], capture_output=True,
            encoding='utf-8', check=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW,
        ).stdout
        processes = json.loads(output)
        matches = []
        for process in processes:
            command = (process.get('CommandLine') or '').replace('\\', '/').casefold()
            for path in paths:
                if _mentions_path(command, path):
                    matches.append({'worktree': str(path), 'pid': process['ProcessId'], 'name': process['Name']})
        return {'checked': True, 'matches': matches,
                'without_command_line': sum(not process.get('CommandLine') for process in processes)}
    except (OSError, subprocess.SubprocessError, ValueError, TypeError, KeyError) as error:
        return {'checked': False, 'error': type(error).__name__}
