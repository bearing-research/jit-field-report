"""Report the JIT state of the current interpreter.

Call `jit_state()` once per benchmark or test subprocess, outside timed code,
and store the result next to the measurement. It confirms configuration only:
`is_enabled()` does not mean any JIT code ran. Never call
`sys._jit.is_active()` in timed code; the docs reserve it for debugging the
JIT and warn that it can change what gets compiled.
"""

from __future__ import annotations

import json
import os
import platform
import sys
import sysconfig


def jit_state() -> dict:
    jit = getattr(sys, "_jit", None)
    return {
        "python": sys.version,
        "executable": sys.executable,
        "PYTHON_JIT": os.environ.get("PYTHON_JIT"),
        "jit_available": bool(jit and jit.is_available()),
        "jit_enabled": bool(jit and jit.is_enabled()),
        "config_args": sysconfig.get_config_var("CONFIG_ARGS"),
        "machine": platform.machine(),
    }


if __name__ == "__main__":
    print(json.dumps(jit_state(), indent=2))
