"""Android permissions declared by an APK (read from its AndroidManifest.xml).

    python appcore/android/apk_permissions.py dist/RiffFinder.apk

build_apk.sh runs it at the end of each build: it shows the APK's
permissions and warns if one of them is not expected
(ANDROID_PERMISSIONS of app_info.py, which build_apk.sh passes in APPCORE_PERMISSIONS)
(for example if an update of Qt's tool adds a useless one back, see the
"permissions" fix in patch_deploy_tools.py). Only needs Python.
"""

from __future__ import annotations

import os
import struct
import sys
import zipfile

# The only ones the app uses (see patch_deploy_tools.py, fix 2b bis)
# + those added by the app's Java libraries (LIBRARY_PERMISSIONS of
# app_info.py: BILLING for Google Play Billing, WAKE_LOCK for WorkManager…)
EXPECTED = {p.strip() for p in (os.environ.get(
    "APPCORE_PERMISSIONS", "android.permission.MODIFY_AUDIO_SETTINGS") + ","
    + os.environ.get("APPCORE_EXPECTED_PERMISSIONS", "")).split(",") if p.strip()}
# Added by AndroidX under its own name (app package + suffix): harmless
EXPECTED_SUFFIXES = (".DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION",)

_STRING_POOL, _START_ELEMENT = 0x0001, 0x0102
_TYPE_STRING = 0x03


def _strings(data: bytes, offset: int) -> list[str]:
    """String table of Android's binary XML (UTF-8 or UTF-16)."""
    header_size, = struct.unpack_from("<H", data, offset + 2)
    count, _styles, flags, start, _ = struct.unpack_from("<IIIII", data, offset + 8)
    utf8 = bool(flags & 0x100)
    offsets = struct.unpack_from(f"<{count}I", data, offset + header_size)
    out = []
    for item in offsets:
        p = offset + start + item
        if utf8:
            p += 2 if data[p] & 0x80 else 1           # length in characters
            n = data[p]
            p += 1
            if n & 0x80:
                n = ((n & 0x7F) << 8) | data[p]
                p += 1
            out.append(data[p:p + n].decode("utf-8", errors="replace"))
        else:
            n, = struct.unpack_from("<H", data, p)
            p += 2
            if n & 0x8000:
                n = ((n & 0x7FFF) << 16) | struct.unpack_from("<H", data, p)[0]
                p += 2
            out.append(data[p:p + 2 * n].decode("utf-16-le", errors="replace"))
    return out


def manifest_permissions(manifest: bytes) -> list[str]:
    """Names of the <uses-permission> of a binary AndroidManifest.xml."""
    strings: list[str] = []
    found = []
    pos = 8                                   # after the file header
    while pos + 8 <= len(manifest):
        kind, _header, size = struct.unpack_from("<HHI", manifest, pos)
        if size <= 0:
            break
        if kind == _STRING_POOL:
            strings = _strings(manifest, pos)
        elif kind == _START_ELEMENT and strings:
            name_index, = struct.unpack_from("<I", manifest, pos + 20)
            attr_start, attr_size, attr_count = struct.unpack_from("<HHH", manifest, pos + 24)
            if strings[name_index].startswith("uses-permission"):
                for i in range(attr_count):
                    a = pos + 16 + attr_start + i * attr_size
                    _ns, attr_name, raw, _vsize, _zero, vtype, vdata = \
                        struct.unpack_from("<IIIHBBI", manifest, a)
                    if strings[attr_name] == "name":
                        index = raw if raw != 0xFFFFFFFF else (vdata if vtype == _TYPE_STRING else None)
                        if index is not None:
                            found.append(strings[index])
        pos += size
    return found


def apk_permissions(apk: str) -> list[str]:
    with zipfile.ZipFile(apk) as z:
        return manifest_permissions(z.read("AndroidManifest.xml"))


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    for apk in sys.argv[1:]:
        permissions = apk_permissions(apk)
        print(f"Permissions of {apk.rsplit('/', 1)[-1]}:")
        for name in permissions or ["(aucune)"]:
            print(f"  {name}")
        extra = sorted(name for name in set(permissions) - EXPECTED
                       if not name.endswith(EXPECTED_SUFFIXES))
        if extra:
            print("\033[1;33mWARNING: unexpected permissions (see the "
                  "\"permissions\" fix in android/patch_deploy_tools.py):\033[0m")
            for name in extra:
                print(f"  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
