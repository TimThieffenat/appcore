"""The paid "Pro" version of an app: a one-time purchase on Google Play.

An app sells a Pro version when its app_info.py sets PRO_PRODUCT (the product
ID created in the Play Console, for example "pro"). What Pro unlocks is up to
the app (pages with `PRO = True`, see pro_ui.py; game tiers; instruments of
PRO_VOICES…); it asks `pro.is_pro()`.

On Android, the purchase goes through Google Play (PlayBilling.java, through the
file bridge of bridge.py). What Google Play answers is kept in the settings
("pro/owned"): Pro stays open without a network, and it is checked again at
every start and every time the app comes back (a refund closes it again).

Unlock code (Settings › Unlock code): for Google Play's reviewers, who cannot
buy anything (Play Console › App content › Sign-in details). The right code
opens Pro for good on the device ("pro/code"). The code is written nowhere in
the project: only its fingerprint is (UNLOCK_CODE_SHA256, app_info.py). To
change it: `python appcore/tools/unlock_code.py`.

On a computer (tests), "Unlock" opens Pro without paying and "Lock again" closes
it (code included). The environment variable <APP>_PRO=1 (or 0), for example
RIFFFINDER_PRO, forces one or the other (tests, screenshots).

    pro.enabled()     -> the app has a Pro version (PRO_PRODUCT)
    pro.is_pro()      -> bool (always True in an app without a Pro version)
    pro.buy() / pro.restore()
    pro.redeem(code)  -> True if the code is right (Pro unlocked)
    pro.price()       -> "€4.99" (empty until Google Play has given it)
    pro.status()      -> text to show under the purchase button (waiting, error…)
    bus.pro_changed   -> emitted when any of them changes

boot.py reads the known purchase before the window, asks Google Play again once
it is shown, and the window does it again when the app comes back.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re

from appcore import app, bridge

KEY = "pro/owned"
CODE_KEY = "pro/code"       # opened by the unlock code (Google Play reviewers)
POLL_MS = 700           # state.json read again after a request…
POLL_COUNT = 90         # … for ~1 minute (Google Play's purchase window)

log = logging.getLogger(__name__)

_owned: bool | None = None
_code: bool | None = None
_billing: dict = {}
_seen_message_time = 0
_message = ""
_timer = None
_polls_left = 0


def enabled() -> bool:
    """The app sells a Pro version (PRO_PRODUCT of app_info.py)."""
    return bool(str(app.get("PRO_PRODUCT", "") or "").strip())


def product() -> str:
    return str(app.get("PRO_PRODUCT", "") or "").strip()


def _bus():
    from appcore.app_signals import bus
    return bus


def _settings():
    from PySide6.QtCore import QSettings
    return QSettings()


def _forced() -> bool | None:
    value = os.environ.get(app.slug().upper() + "_PRO", "").strip().lower()
    if value in ("1", "true", "yes"):
        return True
    if value in ("0", "false", "no"):
        return False
    return None


def _flag(key: str) -> bool:
    return str(_settings().value(key, False)).lower() in ("true", "1")


def is_pro() -> bool:
    global _owned, _code
    if not enabled():
        return True
    forced = _forced()
    if forced is not None:
        return forced
    if _owned is None:
        _owned = _flag(KEY)
    if _code is None:
        _code = _flag(CODE_KEY)
    return _owned or _code


def _set_owned(value: bool) -> None:
    global _owned
    before = is_pro()
    _owned = bool(value)
    _settings().setValue(KEY, _owned)
    if before != is_pro():
        log.info("pro: %s", "unlocked" if is_pro() else "locked")
        _bus().pro_changed.emit()


def _set_code(value: bool) -> None:
    global _code
    before = is_pro()
    _code = bool(value)
    _settings().setValue(CODE_KEY, _code)
    if before != is_pro():
        log.info("pro: %s", "unlocked" if is_pro() else "locked")
        _bus().pro_changed.emit()


# --- Unlock code -------------------------------------------------------------------------
def normalize_code(text) -> str:
    """The code without spaces, dashes or lower case: "riff-ab12" = "RIFFAB12"."""
    return re.sub(r"[^A-Z0-9]", "", str(text or "").upper())


def code_salt() -> str:
    """Mixed with the code before hashing; depends on the app's name (renaming
    the app changes the fingerprint: make a new code then)."""
    return f"{app.name()} unlock code\n"


def code_hash(text) -> str:
    """The fingerprint of a code (the one put in UNLOCK_CODE_SHA256)."""
    return hashlib.sha256((code_salt() + normalize_code(text)).encode("utf-8")).hexdigest()


def _expected_hash() -> str:
    return str(app.get("UNLOCK_CODE_SHA256", "") or "").strip().lower()


def code_enabled() -> bool:
    """An unlock code exists (UNLOCK_CODE_SHA256 filled in app_info.py)."""
    return enabled() and bool(_expected_hash())


def redeem(text) -> bool:
    """The code typed in the settings: the right one opens Pro for good on this
    device. The code itself is never written to the log."""
    expected = _expected_hash()
    if not expected or not normalize_code(text):
        return False
    if not hmac.compare_digest(code_hash(text), expected):
        log.info("pro: wrong unlock code")
        return False
    log.info("pro: unlock code accepted")
    _set_code(True)
    return True


# --- Google Play -------------------------------------------------------------------------
def store_available() -> bool:
    """Google Play answers (always true on a computer: test purchase)."""
    if not bridge.available():
        return True
    return bool(_billing.get("available", True))


def price() -> str:
    return str(_billing.get("price") or "")


def pending() -> bool:
    return bool(_billing.get("pending"))


def status() -> str:
    """What to say under the purchase button (empty: nothing)."""
    from appcore.i18n import tr
    if is_pro():
        return ""
    if pending():
        return tr("Payment pending: Pro unlocks as soon as Google Play confirms it.")
    if bridge.available() and not _billing.get("available", True):
        return tr("Google Play is not available: try again later.")
    if _message == "cancelled":
        return tr("Purchase cancelled.")
    if _message:
        return tr("The purchase did not go through ({reason}).", reason=_message)
    return ""


def refresh() -> None:
    """Reads what Java wrote (purchase, price, waiting, message)."""
    global _billing, _seen_message_time, _message
    if not enabled():
        return
    billing = bridge.state().get("billing")
    if not isinstance(billing, dict):
        return
    changed = billing != _billing
    _billing = billing
    stamp = int(billing.get("time") or 0)
    if stamp > _seen_message_time:
        _seen_message_time = stamp
        _message = str(billing.get("message") or "")
    if "pro" in billing:
        _set_owned(bool(billing["pro"]))
    if changed:
        _bus().pro_changed.emit()


def _poll() -> None:
    global _polls_left
    refresh()
    _polls_left -= 1
    if _polls_left <= 0 and _timer is not None:
        _timer.stop()


def _watch() -> None:
    """Reads state.json regularly for a minute."""
    global _timer, _polls_left
    if not bridge.available():
        return
    if _timer is None:
        from PySide6.QtCore import QTimer
        _timer = QTimer()
        _timer.setInterval(POLL_MS)
        _timer.timeout.connect(_poll)
    _polls_left = POLL_COUNT
    _timer.start()


def start() -> None:
    """At start-up and every time the app comes back: Java checks the purchase again."""
    if not enabled():
        return
    refresh()
    _watch()


def buy() -> None:
    global _message
    _message = ""
    if not bridge.available():
        log.info("pro: test unlock (computer)")
        _set_owned(True)
        return
    bridge.request("billing:buy")
    _watch()
    _bus().pro_changed.emit()


def restore() -> None:
    global _message
    _message = ""
    if not bridge.available():
        log.info("pro: test lock (computer)")
        _set_code(False)        # the code too: to try it again
        _set_owned(False)
        return
    bridge.request("billing:restore")
    _watch()
