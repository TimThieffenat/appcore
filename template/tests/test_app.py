"""Tests of the app without Qt:  python -m unittest discover tests

(Those of the base: python -m unittest discover -s appcore/tests -t .)
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app_info  # noqa: E402
from appcore import music_theory as mt  # noqa: E402


class AppInfoTests(unittest.TestCase):
    def test_name_is_a_java_identifier(self) -> None:
        self.assertTrue(app_info.NAME.isidentifier(), app_info.NAME)

    def test_version(self) -> None:
        parts = app_info.VERSION.split(".")
        self.assertTrue(all(p.isdigit() for p in parts), app_info.VERSION)


class HomeTests(unittest.TestCase):
    def test_arpeggio_notes(self) -> None:
        root = mt.note_pc("A")
        notes = [48 + root + step for step in (0, 4, 7, 12, 16)]
        self.assertEqual(notes[0] % 12, 9)
        self.assertTrue(all(36 <= n <= 88 for n in notes))


if __name__ == "__main__":
    unittest.main()
