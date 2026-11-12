"""The bridge with the Java part of the Android app (appcore/android/java/Bridge.java.in).

Python cannot call Java in these apps (python-for-android's Qt "bootstrap" has
no pyjnius): both sides exchange files in the app's private folder,
files/bridge:

- `request("billing:buy")` drops a request ("request-<n>.txt", written under
  another name then renamed: Java never reads a half-written file). Java
  handles the base's commands (billing:…, see pro.py) and passes the others to
  the app's AppHooks.onCommand;
- `state()` reads back "state.json", which Java keeps up to date, one section
  per subject: {"billing": {"available", "pro", "pending", "price", "message",
  "time"}, …} (an app's Java can add its own sections with Bridge.put);
- `write_json(name, data)` / `read_json(name)`: other files shared with the
  app's Java (for example a reminder's settings).

Outside Android (desktop, tests), `folder()` is None and everything does nothing.
No dependency on Qt.
"""

from __future__ import annotations

import itertools
import json
import logging
import os
import time
from pathlib import Path

log = logging.getLogger(__name__)
_counter = itertools.count()


def folder() -> Path | None:
    """files/bridge on Android (ANDROID_PRIVATE = the app's getFilesDir()), else None."""
    base = os.environ.get("ANDROID_PRIVATE")
    if not base:
        return None
    path = Path(base) / "bridge"
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    return path


def available() -> bool:
    return folder() is not None


def _atomic_write(path: Path, text: str) -> bool:
    tmp = path.with_name(path.name + ".part")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
        return True
    except OSError as error:
        log.warning("bridge: %s not written (%s)", path.name, error)
        return False


def request(command: str) -> bool:
    """Asks Java for something ("billing:buy", "billing:restore", or a command
    of the app's Java)."""
    base = folder()
    if base is None:
        return False
    name = f"request-{time.time_ns():020d}-{next(_counter):04d}.txt"
    log.info("bridge request: %s", command)
    return _atomic_write(base / name, command)


def read_json(name: str) -> dict:
    base = folder()
    if base is None:
        return {}
    try:
        data = json.loads((base / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def write_json(name: str, data: dict) -> bool:
    base = folder()
    if base is None:
        return False
    return _atomic_write(base / name, json.dumps(data, ensure_ascii=False))


def state() -> dict:
    """The last state given by Java ({} outside Android or if there is none yet)."""
    return read_json("state.json")
