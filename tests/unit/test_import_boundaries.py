"""Enforce the core/adapter dependency boundary (Phase E-1).

``core/`` and ``api`` must not import the Hermes adapter or Hermes-only modules.
"""

from __future__ import annotations

import pathlib
import re
import sys

CORE_DIR = pathlib.Path(__file__).resolve().parents[2] / "src" / "hermes_drive_index" / "core"
FORBIDDEN_IMPORT_RE = re.compile(
    r"(from\s+\.\.hermes_adapter|import\s+hermes_adapter"
    r"|from\s+hermes_drive_index\.hermes_adapter"
    r"|import\s+(model_tools|toolsets|hermes_constants)\b"
    r"|from\s+(model_tools|toolsets|tools\.registry|hermes_constants)\b)"
)


def _core_files() -> list[pathlib.Path]:
    return sorted(CORE_DIR.glob("*.py"))


def test_core_sources_have_no_hermes_imports():
    offenders = []
    for path in _core_files():
        text = path.read_text()
        for match in FORBIDDEN_IMPORT_RE.finditer(text):
            offenders.append(f"{path.name}: {match.group(0)!r}")
    assert not offenders, "Forbidden Hermes import(s) in core/:\n" + "\n".join(offenders)


def test_importing_core_and_api_does_not_load_adapter():
    saved_modules = {m: sys.modules[m] for m in sys.modules if m.startswith("hermes_drive_index")}
    try:
        for mod in saved_modules:
            del sys.modules[mod]
        import hermes_drive_index.api  # noqa: F401
        import hermes_drive_index.core.orchestrator  # noqa: F401
        import hermes_drive_index.core.search  # noqa: F401

        adapter_loaded = [m for m in sys.modules if "hermes_adapter" in m]
        assert not adapter_loaded, f"core/api import pulled in adapter modules: {adapter_loaded}"
    finally:
        sys.modules.update(saved_modules)
