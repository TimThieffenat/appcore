"""Tests du socle, sans Qt. Depuis le dossier d'une app :

    python -m unittest discover -s appcore/tests -t .

(ou depuis le dépôt du socle seul : python -m unittest discover -s tests -t ..)
"""

from __future__ import annotations

import importlib
import importlib.util
import runpy
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

CORE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CORE.parent))

from appcore import app, guitar_synth, i18n  # noqa: E402
from appcore import music_theory as mt  # noqa: E402


def _tool(name: str):
    spec = importlib.util.spec_from_file_location(name, CORE / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    old = sys.argv
    sys.argv = [name, "--core"]
    try:
        spec.loader.exec_module(module)
    finally:
        sys.argv = old
    return module


class AppConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = app._info

    def tearDown(self) -> None:
        app._info = self._saved

    def test_defaults_without_app_info(self) -> None:
        app._info = types.ModuleType("app_info")
        self.assertEqual(app.name(), "App")
        self.assertEqual(app.languages()[0], "en")
        self.assertEqual(app.get("VOICES"), ("steel", "nylon"))

    def test_values_and_slug(self) -> None:
        info = types.ModuleType("app_info")
        info.NAME = "Riff_Finder2"
        info.LANGUAGES = ("fr", "en")
        app._info = info
        self.assertEqual(app.slug(), "rifffinder2")
        self.assertEqual(app.languages(), ("en", "fr"))

    def test_android_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "app_info.py").write_text('NAME = "MyApp"\nANDROID_PERMISSIONS = ("RECORD_AUDIO",)\n',
                                                encoding="utf-8")
            out = subprocess.run([sys.executable, str(CORE / "android" / "app_config.py"), tmp],
                                 capture_output=True, text=True, check=True).stdout
            values = dict(line.removeprefix("export ").split("=", 1) for line in out.splitlines())
            self.assertEqual(values["APP_PACKAGE"], "com.myapp.app")
            self.assertEqual(values["JAVA_PACKAGE"], "org.myapp")
            self.assertEqual(values["APP_KEY_ALIAS"], "myapp")
            self.assertIn("android.permission.RECORD_AUDIO", values["APP_PERMISSIONS"])
            Path(tmp, "app_info.py").write_text('NAME = "My App"\n', encoding="utf-8")
            bad = subprocess.run([sys.executable, str(CORE / "android" / "app_config.py"), tmp],
                                 capture_output=True, text=True)
            self.assertNotEqual(bad.returncode, 0)


class TranslationTests(unittest.TestCase):
    def test_every_core_text_is_translated(self) -> None:
        check = _tool("i18n_check")
        texts = check.core_texts()
        self.assertGreater(len(texts), 50)
        for code in i18n.ALL_LANGUAGES:
            if code == "en":
                continue
            catalog = importlib.import_module(f"appcore.locales.{code}").T
            missing, _, wrong = check.check(catalog, texts)
            self.assertEqual(missing, [], code)
            self.assertEqual(wrong, [], code)

    def test_app_entry_replaces_core_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp, "locales")
            pkg.mkdir()
            (pkg / "__init__.py").write_text("", encoding="utf-8")
            (pkg / "fr.py").write_text("T = {'Settings': 'Paramètres', 'Hello': 'Bonjour'}\n",
                                       encoding="utf-8")
            saved = sys.modules.pop("locales", None), sys.modules.pop("locales.fr", None)
            sys.path.insert(0, tmp)
            try:
                catalog = i18n.catalog_for("fr")
                self.assertEqual(catalog["Settings"], "Paramètres")    # l'app remplace le socle
                self.assertEqual(catalog["Hello"], "Bonjour")
                self.assertEqual(catalog["Error report"], "Rapport d'erreur")   # le socle
            finally:
                sys.path.remove(tmp)
                for name in ("locales", "locales.fr"):
                    sys.modules.pop(name, None)
                for name, module in zip(("locales", "locales.fr"), saved):
                    if module is not None:
                        sys.modules[name] = module

    def test_plural_and_fields(self) -> None:
        old = i18n._language, i18n._catalog
        try:
            i18n._language, i18n._catalog = "fr", {"{n} bar": ("{n} mesure", "{n} mesures")}
            self.assertEqual(i18n.ntr("{n} bar", "{n} bars", 0), "0 mesure")
            self.assertEqual(i18n.ntr("{n} bar", "{n} bars", 2), "2 mesures")
            self.assertEqual(i18n.tr("Bar {n}", n=3), "Bar 3")
        finally:
            i18n._language, i18n._catalog = old


class SoundTests(unittest.TestCase):
    def test_voices_have_labels(self) -> None:
        for key in ("steel", "nylon", "keys"):
            self.assertIn(key, guitar_synth.VOICES)

    def test_arpeggio(self) -> None:
        synth = guitar_synth.GuitarSynth(22050, None, "keys")
        perf = guitar_synth.arpeggio(synth, (60, 64, 67), step=0.1, seconds=0.3)
        self.assertEqual(perf.sample_rate, 22050)
        self.assertGreater(len(perf.pcm), 2 * 22050 * 0.5)
        self.assertAlmostEqual(perf.duration, len(perf.pcm) / 2 / 22050, delta=0.01)

    def test_music_theory(self) -> None:
        self.assertEqual(mt.note_pc("A"), 9)
        self.assertIn("Major", mt.CHORDS)


class TemplateTests(unittest.TestCase):
    def test_new_app(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp, "DemoApp")
            subprocess.run([sys.executable, str(CORE / "tools" / "new_app.py"), "DemoApp", str(dest),
                            "--copy", "--email", "a@b.c"], check=True, capture_output=True)
            info = runpy.run_path(str(dest / "app_info.py"))
            self.assertEqual(info["NAME"], "DemoApp")
            self.assertEqual(info["ANDROID_PACKAGE"], "com.demoapp.app")
            for name in ("main.py", "page_home.py", "page_settings.py", "icons.py", "locales/fr.py",
                         ".github/workflows/android.yml", "appcore/boot.py"):
                self.assertTrue((dest / name).is_file(), name)
            for path in dest.rglob("*.py"):
                if "appcore" in path.parts:
                    continue
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("__APP_NAME__", text, path)
                compile(text, str(path), "exec")
            bad = subprocess.run([sys.executable, str(CORE / "tools" / "new_app.py"), "Demo App",
                                  str(Path(tmp, "x"))], capture_output=True)
            self.assertNotEqual(bad.returncode, 0)


if __name__ == "__main__":
    unittest.main()
