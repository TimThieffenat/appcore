"""Crée une nouvelle app sur le socle, prête à lancer et à compiler.

    python appcore/tools/new_app.py MonApp D:\\Projects\\MonApp
    python appcore/tools/new_app.py MonApp D:\\Projects\\MonApp --email moi@exemple.fr \\
        --description "A metronome trainer"

1. copie le modèle (appcore/template/) dans le dossier, avec le nom de l'app ;
2. y ajoute les workflows GitHub du socle (.github/workflows/) ;
3. si git est là : crée le dépôt, ajoute le socle comme sous-module (adresse
   du dépôt appcore actuel, ou --core-url) et fait le premier commit ;
   sinon (ou avec --copy) : copie le socle dans appcore/.

Le nom doit être un identifiant Java valide (lettres, chiffres, _ ; pas
d'espace) : c'est aussi le nom de l'APK.
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
    """L'adresse du dépôt du socle (celle d'où vient ce dossier appcore/)."""
    try:
        return _git("remote", "get-url", "origin", cwd=CORE).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def fill(dest: Path, values: dict[str, str]) -> None:
    for path in dest.rglob("*"):
        if path.is_file() and (path.suffix in TEXT or path.name in TEXT):
            text = path.read_bytes().decode("utf-8")   # fins de ligne gardées (.bat)
            new = text
            for key, value in values.items():
                new = new.replace(key, value)
            if new != text:
                path.write_bytes(new.encode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("name", help="nom de l'app (identifiant Java : MonApp)")
    parser.add_argument("folder", help="dossier à créer")
    parser.add_argument("--email", default="", help="adresse des rapports d'erreur")
    parser.add_argument("--description", default="A music app",
                        help="une phrase (README, politique de confidentialité)")
    parser.add_argument("--core-url", default="", help="adresse git du socle (sous-module)")
    parser.add_argument("--copy", action="store_true", help="copier le socle au lieu d'un sous-module")
    args = parser.parse_args()

    name = args.name
    if not name.isidentifier() or not name.isascii():
        raise SystemExit(f"{name!r} : le nom doit être un identifiant Java (lettres, chiffres, _)")
    slug = "".join(c for c in name.lower() if c.isalnum())
    dest = Path(args.folder).resolve()
    if dest.exists() and any(dest.iterdir()):
        raise SystemExit(f"{dest} existe déjà et n'est pas vide")

    shutil.copytree(TEMPLATE, dest, ignore=IGNORE, dirs_exist_ok=True)
    shutil.copytree(WORKFLOWS, dest / ".github" / "workflows", dirs_exist_ok=True)
    email = args.email or _read_email()
    fill(dest, {"__APP_NAME__": name, "__app_slug__": slug, "__EMAIL__": email,
                "__DESCRIPTION__": args.description,
                "__DATE__": datetime.date.today().strftime("%d %B %Y")})
    print(f"{name} créée dans {dest}")

    url = args.core_url or core_url()
    use_git = shutil.which("git") is not None and not args.copy and bool(url)
    if use_git:
        try:
            _git("init", "-b", "main", cwd=dest)
            _git("submodule", "add", url, "appcore", cwd=dest)
            _git("add", "-A", cwd=dest)
            _git("commit", "-m", f"{name} : création sur le socle appcore", cwd=dest)
            print(f"Dépôt git créé, socle en sous-module ({url}).")
        except subprocess.CalledProcessError as error:
            print("git a échoué :", (error.stderr or error.stdout).strip())
            print("Le socle est copié à la place.")
            use_git = False
    if not use_git:
        shutil.copytree(CORE, dest / "appcore", ignore=shutil.ignore_patterns(
            "__pycache__", "*.pyc", ".git"), dirs_exist_ok=True)
        if not url:
            print("Socle copié dans appcore/ (pas d'adresse git : --core-url pour un sous-module).")
    print("Ensuite :")
    print(f"  cd {dest}")
    print("  python main.py                       (lancer)")
    print("  appcore\\tools\\smoke_test.bat         (tests + captures)")
    print("  python tools/make_icon.py            (icône, pillow nécessaire)")
    print("Pour GitHub : créer le dépôt, puis git remote add origin <adresse> && git push -u origin main")


def _read_email() -> str:
    """L'adresse de l'app voisine (celle d'où l'outil est lancé), sinon rien."""
    try:
        import runpy
        return str(runpy.run_path(str(Path.cwd() / "app_info.py")).get("SUPPORT_EMAIL", ""))
    except Exception:  # noqa: BLE001
        return ""


if __name__ == "__main__":
    sys.exit(main())
