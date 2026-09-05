"""Shared fixtures and duck-typed fakes for the test suite."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest
from _pytest.monkeypatch import MonkeyPatch

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication

    from thaipua.core.font.composer import ThaiPuaFontGenerator
    from thaipua.gui.font_service import FontService
    from thaipua.gui.main_window import MainWindow

SAMPLE_FONT_PATH = Path(__file__).resolve().parents[1] / "assets" / "fonts" / "Sarabun-Regular.ttf"


class FakeGlyph:
    """Minimal stand-in for a `glyf` glyph exposing only `isComposite`."""

    def __init__(self, composite: bool, contours: int | None = None) -> None:
        self._composite = composite
        self.numberOfContours = contours

    def isComposite(self) -> bool:
        return self._composite


class FakeCompositeGlyph:
    """Composite glyph stand-in exposing its component names."""

    def __init__(self, component_names: list[str]) -> None:
        self.components = [SimpleNamespace(glyphName=name) for name in component_names]

    def isComposite(self) -> bool:
        return True


class FakeGlyf:
    """Dict-like stand-in for a `glyf` table keyed by glyph name."""

    def __init__(self, glyphs: dict[str, Any]) -> None:
        self._glyphs = glyphs

    def __contains__(self, name: str) -> bool:
        return name in self._glyphs

    def __getitem__(self, name: str) -> Any:
        return self._glyphs[name]


def make_glyf(**glyphs: bool) -> FakeGlyf:
    """Build a `FakeGlyf` mapping each glyph name to its composite flag."""
    return FakeGlyf({name: FakeGlyph(composite) for name, composite in glyphs.items()})


class FakeFont:
    """Duck-typed `TTFont` exposing only `getBestCmap` and `get`."""

    def __init__(self, cmap: dict[int, str], glyf: FakeGlyf | None = None) -> None:
        self._cmap = cmap
        self._glyf = glyf

    def getBestCmap(self) -> dict[int, str]:
        return self._cmap

    def get(self, key: str) -> Any:
        return self._glyf if key == "glyf" else None


def write_encoding_map(tmp_path: Path, mapping: dict[str, str], name: str = "pua.json") -> Path:
    """Write a raw JSON encoding map under `tmp_path` and return its path."""
    map_path = tmp_path / name
    map_path.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
    return map_path


def service_with_layout(tmp_path: Path) -> FontService:
    """Build a `FontService` bound to fresh layout and PUA-map paths under `tmp_path`."""
    from thaipua.gui.font_service import FontService

    service = FontService()
    service.set_layout_path(str(tmp_path / "layout.json"))
    service.set_pua_map_path(str(tmp_path / "pua.json"))
    service.load_layout()
    return service


@pytest.fixture
def generator() -> Iterator[ThaiPuaFontGenerator]:
    """Yield a generator over the sample font, skipping when the asset is missing."""
    from thaipua.core.font.composer import ThaiPuaFontGenerator

    if not SAMPLE_FONT_PATH.exists():
        pytest.skip(f"sample font missing: {SAMPLE_FONT_PATH}")
    gen = ThaiPuaFontGenerator(str(SAMPLE_FONT_PATH), None)
    yield gen
    gen.font.close()


@pytest.fixture(scope="session")
def qapp() -> Iterator[QApplication]:
    """Share one QApplication; Qt reads the platform env on first construction."""
    from PySide6.QtWidgets import QApplication

    # Headless runners have no display server; force offscreen before Qt picks a platform.
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    assert isinstance(app, QApplication)
    yield app
    app.processEvents()


@pytest.fixture
def window(qapp: QApplication, tmp_path: Path) -> Iterator[MainWindow]:
    """Build a window isolated to tmp paths; close without the dirty prompt on teardown."""
    from thaipua.gui.main_window import MainWindow

    win = MainWindow()
    win._service.set_layout_path(str(tmp_path / "layout.json"))
    win._service.set_pua_map_path(str(tmp_path / "pua.json"))
    yield win
    win._state.dirty = False
    win.close()
    win.deleteLater()
    qapp.processEvents()


@pytest.fixture
def loaded_window(window: MainWindow, monkeypatch: MonkeyPatch, tmp_path: Path) -> MainWindow:
    """Run the real open-font flow with a stubbed file dialog and no stem profile on disk."""
    from PySide6.QtWidgets import QFileDialog

    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args, **kwargs: (str(SAMPLE_FONT_PATH), ""))
    monkeypatch.setattr(window._service, "default_profile_path", lambda: tmp_path / "absent.json")
    window._toolbar.open_font_requested.emit()
    assert window._service.is_loaded
    return window
