"""
Media parser for audio and video files.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

from hermes_auto_organizer.domain.models import FileExtraction
from hermes_auto_organizer.infrastructure.storage.hashing import compute_full_sha256

logger = logging.getLogger("hermes_auto_organizer.parsers.media")

try:
    import mutagen
    _HAS_MUTAGEN = True
except ImportError:
    _HAS_MUTAGEN = False


class MediaParser:
    """Extracts metadata from audio files and video containers."""

    AUDIO_EXTS = {".mp3", ".flac", ".wav", ".m4a", ".ogg", ".aac"}
    VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}

    @property
    def strategy_name(self) -> str:
        return "media_extractor"

    def supports(self, path: Path, mime_type: str | None = None) -> bool:
        ext = path.suffix.lower()
        return ext in self.AUDIO_EXTS or ext in self.VIDEO_EXTS

    async def extract_content(self, path: Path) -> FileExtraction:
        sha256 = compute_full_sha256(path)
        ext = path.suffix.lower()

        if ext in self.AUDIO_EXTS and _HAS_MUTAGEN:
            return self._extract_audio(path, sha256)
        if ext in self.VIDEO_EXTS and shutil.which("ffprobe"):
            return self._extract_video_ffprobe(path, sha256)

        return FileExtraction(
            content_sha256=sha256,
            extraction_strategy="media_basic",
            summary_text=f"Media file {path.name} ({ext.upper()}).",
            metadata_json={"extension": ext},
        )

    def _extract_audio(self, path: Path, sha256: str) -> FileExtraction:
        try:
            audio = mutagen.File(str(path))
            meta: dict[str, Any] = {}
            artist = None
            title = None
            album = None

            if audio is not None:
                if audio.tags:
                    for key, val in audio.tags.items():
                        norm_key = str(key).lower()
                        if "artist" in norm_key and not artist:
                            artist = str(val)
                        elif "title" in norm_key and not title:
                            title = str(val)
                        elif "album" in norm_key and not album:
                            album = str(val)

                if audio.info:
                    meta["duration_sec"] = getattr(audio.info, "length", 0)
                    meta["bitrate"] = getattr(audio.info, "bitrate", 0)
                    meta["sample_rate"] = getattr(audio.info, "sample_rate", 0)

            summary = (
                f"Audio track {path.name}: title='{title or 'Unknown'}', "
                f"artist='{artist or 'Unknown'}', album='{album or 'Unknown'}'."
            )
            meta.update({"artist": artist, "title": title, "album": album})
            return FileExtraction(
                content_sha256=sha256,
                extraction_strategy="media_audio_mutagen",
                summary_text=summary,
                metadata_json=meta,
            )
        except Exception as e:
            logger.warning("Failed to parse audio %s: %s", path, e)
            return self._fallback(path, sha256, f"Audio parse error: {e}")

    def _extract_video_ffprobe(self, path: Path, sha256: str) -> FileExtraction:
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(path),
            ]
            # Safety: shell=False, timeout=5
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            if proc.returncode != 0:
                return self._fallback(path, sha256, "ffprobe execution failed")

            data = json.loads(proc.stdout)
            fmt = data.get("format", {})
            duration = float(fmt.get("duration", 0))
            streams = data.get("streams", [])
            video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})

            width = video_stream.get("width")
            height = video_stream.get("height")
            codec = video_stream.get("codec_name")

            summary = f"Video {path.name}: resolution={width}x{height}, codec={codec}, duration={duration:.1f}s."
            metadata = {
                "duration_sec": duration,
                "width": width,
                "height": height,
                "video_codec": codec,
            }
            return FileExtraction(
                content_sha256=sha256,
                extraction_strategy="media_video_ffprobe",
                summary_text=summary,
                metadata_json=metadata,
            )
        except Exception as e:
            return self._fallback(path, sha256, f"Video parse error: {e}")

    def _fallback(self, path: Path, sha256: str, reason: str) -> FileExtraction:
        return FileExtraction(
            content_sha256=sha256,
            extraction_strategy="media_fallback",
            summary_text=f"Media file {path.name} ({reason}).",
            metadata_json={"error": reason},
        )
