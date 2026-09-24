"""Optional OCR helpers.

OCR is deliberately binary-driven and best-effort so the default package keeps no
hard OCR dependencies. Missing tools, timeouts, and command failures return
``None`` rather than raising into index builds.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

_SAFE_OCRMYPDF_FLAGS_WITH_VALUES = {
    "--image-dpi": str.isdigit,
    "--tesseract-pagesegmode": str.isdigit,
}
_SAFE_OCRMYPDF_FLAGS = {
    "--rotate-pages",
    "--deskew",
    "--remove-background",
}

_SAFE_TESSERACT_FLAGS_WITH_VALUES = {
    "--dpi": str.isdigit,
    "--psm": str.isdigit,
    "--oem": str.isdigit,
    "-l": lambda v: bool(v and not v.startswith("-") and all(c.isalnum() or c in "+_-" for c in v)),
}
_SAFE_TESSERACT_FLAGS: set[str] = set()


def validate_ocr_args(
    args: tuple[str, ...] | list[str],
    flags: set[str],
    flags_with_values: dict[str, Any],
    tool_name: str,
) -> tuple[str, ...]:
    """Validate that argument list contains only allowed flags and safe values."""
    args_tuple = tuple(args) if isinstance(args, (list, tuple)) else ()
    safe: list[str] = []
    i = 0
    while i < len(args_tuple):
        arg = args_tuple[i]
        if arg in flags:
            safe.append(arg)
            i += 1
            continue
        validator = flags_with_values.get(arg)
        if validator is None:
            raise ValueError(f"Unsupported {tool_name} argument: {arg}")
        if i + 1 >= len(args_tuple):
            raise ValueError(f"{tool_name} argument requires a value: {arg}")
        value_arg = args_tuple[i + 1]
        if value_arg.startswith("-") or not validator(value_arg):
            raise ValueError(f"Unsupported {tool_name} value for {arg}: {value_arg}")
        safe.extend((arg, value_arg))
        i += 2
    return tuple(safe)


def ocr_available(kind: str) -> bool:
    """Return whether the external OCR tool for ``kind`` is available."""
    if kind == "pdf":
        return shutil.which("ocrmypdf") is not None
    if kind == "image":
        return shutil.which("tesseract") is not None
    return False


def ocr_pdf(path: Path, *, timeout: int = 120, extra_args: tuple[str, ...] = ()) -> str | None:
    """OCR a scanned PDF and return its extracted text, or ``None`` on failure."""
    if not ocr_available("pdf"):
        return None
    try:
        from .extract import extract_pdf

        validated_args = validate_ocr_args(extra_args, _SAFE_OCRMYPDF_FLAGS, _SAFE_OCRMYPDF_FLAGS_WITH_VALUES, "OCRmyPDF")
        with tempfile.TemporaryDirectory(prefix="hermes-drive-index-ocr-") as tmpdir:
            out = Path(tmpdir) / "ocr.pdf"
            subprocess.run(
                ["ocrmypdf", "--skip-text", "--quiet", *validated_args, str(path), str(out)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout,
            )
            text = extract_pdf(out)
            return text if text.strip() else None
    except Exception:
        return None


def ocr_image(path: Path, *, timeout: int = 120, extra_args: tuple[str, ...] = ()) -> str | None:
    """OCR an image and return text, or ``None`` on failure."""
    if not ocr_available("image"):
        return None
    try:
        validated_args = validate_ocr_args(extra_args, _SAFE_TESSERACT_FLAGS, _SAFE_TESSERACT_FLAGS_WITH_VALUES, "Tesseract")
        proc = subprocess.run(
            ["tesseract", str(path), "stdout", "--quiet", *validated_args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=timeout,
        )
        return proc.stdout if proc.stdout.strip() else None
    except Exception:
        return None
