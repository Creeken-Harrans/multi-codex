from __future__ import annotations

import subprocess
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print('usage: launch_team.py "<task>"')
        return 1
    task = sys.argv[1]
    return subprocess.call(["codex-hive", "run", task])


if __name__ == "__main__":
    raise SystemExit(main())
