#!/usr/bin/env python3

import subprocess
import sys
from pathlib import Path

ANALYZER = Path("/home/station1/station-dashboard/tools/analyze-daily-log.py")

result = subprocess.run(
    [sys.executable, str(ANALYZER), "--email"],
    capture_output=True,
    text=True,
)

output = result.stdout

marker = "STATION DASHBOARD\n"

if marker not in output:
    sys.stderr.write(output)
    sys.stderr.write(result.stderr)
    sys.exit(result.returncode or 1)

report = output[output.index(marker):]

print(report, end="")

sys.exit(result.returncode)
