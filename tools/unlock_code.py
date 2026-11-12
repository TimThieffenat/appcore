"""Unlock code of an app's Pro version, for Google Play's reviewers.

Development tool, not used by the app. From the app's folder:

    python appcore/tools/unlock_code.py                  # a new random code
    python appcore/tools/unlock_code.py RIFF-XXXX-XXXX   # this code
    python appcore/tools/unlock_code.py --check CODE     # does it open the current app?

Gives the code and the UNLOCK_CODE_SHA256 line to copy into app_info.py. The
code itself is written nowhere in the project (repository, APK): only its
fingerprint is. Give it in the Play Console (App content › Sign-in details), and
change it there with every new code. A device already unlocked by the old code
stays unlocked.

Upper / lower case, spaces and dashes do not count: "riff abcd…" is
"RIFF-ABCD-…" (pro.normalize_code). The code starts with UNLOCK_CODE_PREFIX of
app_info.py (default: the first four letters of the app's name).
"""

from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

CORE = Path(__file__).resolve().parent.parent
ROOT = Path(os.getcwd())
for path in (str(ROOT), str(CORE.parent)):
    if path not in sys.path:
        sys.path.insert(0, path)

from appcore import app, pro  # noqa: E402

ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"   # no 0/O nor 1/I/L: nothing to mix up


def prefix() -> str:
    text = pro.normalize_code(app.get("UNLOCK_CODE_PREFIX", "") or "")
    return text or pro.normalize_code(app.name())[:4] or "CODE"


def new_code() -> str:
    """The prefix then 3 random groups of 4 signs (about 60 bits)."""
    groups = ("".join(secrets.choice(ALPHABET) for _ in range(4)) for _ in range(3))
    return prefix() + "-" + "-".join(groups)


def check(code: str) -> int:
    expected = str(app.get("UNLOCK_CODE_SHA256", "") or "").strip().lower()
    if not expected:
        print("UNLOCK_CODE_SHA256 is empty in app_info.py: no code is planned.")
        return 1
    if pro.code_hash(code) == expected:
        print(f"OK: this code opens {app.name()} Pro in this version.")
        return 0
    print("No: this code is not the one of app_info.py.")
    return 1


def main(args: list[str]) -> int:
    if not (ROOT / "app_info.py").is_file():
        print("Run it from the app's folder (the one holding app_info.py).")
        return 2
    if args[:1] in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    if args[:1] == ["--check"]:
        if len(args) < 2:
            print(__doc__)
            return 2
        return check(" ".join(args[1:]))
    if not pro.enabled():
        print("Note: PRO_PRODUCT is empty in app_info.py (no Pro version yet).")
    code = " ".join(args).strip() or new_code()
    if len(pro.normalize_code(code)) < 10:
        print("Code too short: at least 10 letters or digits.")
        return 2
    print(f"Code (Play Console, keep it to yourself): {code}")
    print("Line to put in app_info.py:")
    print(f'UNLOCK_CODE_SHA256 = "{pro.code_hash(code)}"')
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
