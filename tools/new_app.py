"""Creates a new app on the base, ready to run and to build.

    python appcore/tools/new_app.py MyApp D:\\Projects\\MyApp
    python appcore/tools/new_app.py MyApp D:\\Projects\\MyApp --email me@example.com \\
        --description "A metronome trainer"

1. copies the template (appcore/template/) into the folder, with the app's name;
2. adds the base's GitHub workflows to it (.github/workflows/);
3. if git is there: creates the repository, adds the base as a submodule (URL
   of the current appcore repository, or --core-url) and makes the first commit;
   otherwise (or with --copy): copies the base into appcore/.

The name must be a valid Java identifier (letters, digits, _; no
spaces): it is also the APK's name.
"""

from __future__ import annotations

import argparse
import datetime
import shutil
import subprocess
import sys
from pathlib import Path

CORE = Path(__file__).resolve().parent.parent
TEMPLATE = CORE / "template"
WORKFLOWS = CORE / "templates" / "github" / "workflows"
TEXT = {".py", ".md", ".txt", ".html", ".yml", ".bat", ".gitignore", ".gitattributes"}
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "build", "dist")


def _git(*args: str, cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, check=check, capture_output=True, text=True)


def core_url() -> str:
    """The URL of the base's repository (the one this appcore/ folder comes from)."""
    try:
        return _git("remote", "get-url", "origin", cwd=CORE).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def fill(dest: Path, values: dict[str, str]) -> None:
    for path in dest.rglob("*"):
        if path.is_file() and (path.suffix in TEXT or path.name in TEXT):
            text = path.read_bytes().decode("utf-8")   # line endings kept (.bat)
            new = text
            for key, value in values.items():
                new = new.replace(key, value)
            if new != text:
                path.write_bytes(new.encode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("name", help="app name (Java identifier: MyApp)")
    parser.add_argument("folder", help="folder to create")
    parser.add_argument("--email", default="", help="address for error reports")
    parser.add_argument("--description", default="A music app",
                        help="one sentence (README, privacy policy)")
    parser.add_argument("--core-url", default="", help="git URL of the base (submodule)")
    parser.add_argument("--copy", action="store_true", help="copy the base instead of a submodule")
    args = parser.parse_args()

    name = args.name
    if not name.isidentifier() or not name.isascii():
        raise SystemExit(f"{name!r}: the name must be a Java identifier (letters, digits, _)")
    slug = "".join(c for c in name.lower() if c.isalnum())
    dest = Path(args.folder).resolve()
    if dest.exists() and any(dest.iterdir()):
        raise SystemExit(f"{dest} already exists and is not empty")

    shutil.copytree(TEMPLATE, dest, ignore=IGNORE, dirs_exist_ok=True)
    shutil.copytree(WORKFLOWS, dest / ".github" / "workflows", dirs_exist_ok=True)
    email = args.email or _read_email()
    fill(dest, {"__APP_NAME__": name, "__app_slug__": slug, "__EMAIL__": email,
                "__DESCRIPTION__": args.description,
                "__DATE__": datetime.date.today().strftime("%d %B %Y")})
    print(f"{name} created in {dest}")

    url = args.core_url or core_url()
    use_git = shutil.which("git") is not None and not args.copy and bool(url)
    if use_git:
        try:
            _git("init", "-b", "main", cwd=dest)
            _git("submodule", "add", url, "appcore", cwd=dest)
            _git("add", "-A", cwd=dest)
            _git("commit", "-m", f"{name}: created on the appcore base", cwd=dest)
            print(f"Git repository created, base as a submodule ({url}).")
        except subprocess.CalledProcessError as error:
            print("git failed:", (error.stderr or error.stdout).strip())
            print("The base is copied instead.")
            use_git = False
    if not use_git:
        shutil.copytree(CORE, dest / "appcore", ignore=shutil.ignore_patterns(
            "__pycache__", "*.pyc", ".git"), dirs_exist_ok=True)
        if not url:
            print("Base copied into appcore/ (no git URL: --core-url for a submodule).")
    print("Next:")
    print(f"  cd {dest}")
    print("  python main.py                       (run)")
    print("  appcore\\tools\\smoke_test.bat         (tests + screenshots)")
    print("  python tools/make_icon.py            (icon, needs pillow)")
    print("For GitHub: create the repository, then git remote add origin <url> && git push -u origin main")


def _read_email() -> str:
    """The URL of the neighbouring app (the one the tool is run from), otherwise nothing."""
    try:
        import runpy
        return str(runpy.run_path(str(Path.cwd() / "app_info.py")).get("SUPPORT_EMAIL", ""))
    except Exception:  # noqa: BLE001
        return ""


if __name__ == "__main__":
    sys.exit(main())
