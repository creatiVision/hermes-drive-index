"""
Filesystem Extended Attribute (xattr) Metadata Carrier for Hermes Auto-Organizer.

Attaches AI-generated content summaries, tags/keywords, and document classifications
directly to the physical file using Linux Extended Attributes (xattr).
Adheres to the Freedesktop.org XDG specification (user.xdg.tags).

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hermes_auto_organizer.storage.metadata")


def write_file_metadata(
    path: Path | str,
    summary: Optional[str] = None,
    tags: Optional[List[str]] = None,
    document_type: Optional[str] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Writes AI-generated summary, tags, and document classification to the file's
    extended attributes (xattr).
    """
    p = Path(path)
    if not p.exists() or not hasattr(os, "setxattr"):
        return False

    success = True

    try:
        # 1. Standard desktop tags (Freedesktop / XDG standard)
        if tags:
            tag_str = ",".join(t.strip() for t in tags if t.strip())
            os.setxattr(str(p), "user.xdg.tags", tag_str.encode("utf-8"))
            os.setxattr(str(p), "user.hermes.tags", tag_str.encode("utf-8"))

        # 2. Hermes AI Content Summary
        if summary:
            # Truncate to reasonable xattr size limit (typically 4KB)
            clean_sum = " ".join(summary.split())[:3000]
            os.setxattr(str(p), "user.hermes.summary", clean_sum.encode("utf-8"))

        # 3. Document Classification
        if document_type:
            os.setxattr(str(p), "user.hermes.document_type", document_type.strip().encode("utf-8"))

        # 4. Structured extra metadata
        if extra_metadata:
            meta_json = json.dumps(extra_metadata, ensure_ascii=False)[:3000]
            os.setxattr(str(p), "user.hermes.meta", meta_json.encode("utf-8"))

        return True
    except OSError as exc:
        # Some filesystems (e.g. NFS without xattr, FAT32) do not support xattr
        logger.debug("Filesystem at %s does not support xattr or permission denied: %s", p, exc)
        return False


def read_file_metadata(path: Path | str) -> Dict[str, Any]:
    """
    Reads extended attributes attached to the file.
    Returns tags, summary, document_type, and custom metadata.
    """
    p = Path(path)
    if not p.exists() or not hasattr(os, "getxattr"):
        return {}

    result: Dict[str, Any] = {}

    def _read_attr(name: str) -> Optional[str]:
        try:
            val = os.getxattr(str(p), name)
            return val.decode("utf-8", errors="replace")
        except OSError:
            return None

    # Read tags
    tags_raw = _read_attr("user.xdg.tags") or _read_attr("user.hermes.tags")
    if tags_raw:
        result["tags"] = [t.strip() for t in tags_raw.split(",") if t.strip()]

    # Read summary
    summary_raw = _read_attr("user.hermes.summary")
    if summary_raw:
        result["summary"] = summary_raw

    # Read document type
    doc_type = _read_attr("user.hermes.document_type")
    if doc_type:
        result["document_type"] = doc_type

    # Read extra metadata
    meta_raw = _read_attr("user.hermes.meta")
    if meta_raw:
        try:
            result["meta"] = json.loads(meta_raw)
        except Exception:
            pass

    return result
