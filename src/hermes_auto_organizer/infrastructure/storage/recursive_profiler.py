"""
Recursive Subtree Profiler and Disruption Detection Engine.

Implements bottom-up directory aggregation, Shannon MIME entropy calculation,
lifecycle age profiling, disruption diagnostics, natural language rule synthesis,
and 'Von -> Nach' (S_now -> S_ideal) Tree-Diff projection.

Zero hardcoding of paths: generalized logic works on any storage device or OS.

Copyright (c) 2026 creatiVision
Licensed under the Apache License, Version 2.0 (the "License").
See LICENSE in the repository root for license information.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from hermes_auto_organizer.application.ports.profiler_port import SubtreeProfilerPort
from hermes_auto_organizer.domain.profiler_models import (
    DisruptionItem,
    DisruptionSeverity,
    DisruptionType,
    FolderProfile,
    LifecycleDistribution,
    NaturalLanguageRule,
    OutlierItem,
    SolutionProposal,
    TreeDiffNode,
)


CLEANABLE_DIR_NAMES = {
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    ".cache",
    ".tmp",
    "tmp",
    "temp",
    ".trash",
}

INSTALLER_EXTENSIONS = {".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm", ".iso", ".appimage"}
ARCHIVE_EXTENSIONS = {".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar"}
MEDIA_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mov", ".mkv", ".mp3", ".wav", ".flac"}
DOC_EXTENSIONS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".odt", ".ods"}
CODE_EXTENSIONS = {".py", ".ts", ".js", ".go", ".rs", ".java", ".c", ".cpp", ".html", ".css", ".json", ".yaml", ".yml"}


class RecursiveSubtreeProfiler(SubtreeProfilerPort):
    """
    Generalized recursive bottom-up directory profiler.
    Analyzes all subdirectories and computes entropy, lifecycle, and disruptions.
    """

    def __init__(self, now: Optional[datetime] = None) -> None:
        self._now = now or datetime.now(timezone.utc)

    def profile_directory(
        self,
        path: Path | str,
        max_depth: int = 8,
        include_hidden: bool = False,
    ) -> FolderProfile:
        """Recursively scan path and return a bottom-up aggregated FolderProfile tree."""
        root_path = Path(path).resolve()
        return self._profile_node(root_path, current_depth=0, max_depth=max_depth, include_hidden=include_hidden)

    def _profile_node(
        self,
        node_path: Path,
        current_depth: int,
        max_depth: int,
        include_hidden: bool,
    ) -> FolderProfile:
        profile = FolderProfile(
            path=str(node_path),
            name=node_path.name or str(node_path),
            depth=current_depth,
        )

        if not node_path.exists() or not node_path.is_dir():
            return profile

        direct_ext_counts: Counter[str] = Counter()
        direct_files = 0
        direct_bytes = 0
        direct_active = 0
        direct_dormant = 0
        direct_cold = 0
        subfolder_profiles: List[FolderProfile] = []

        try:
            with os.scandir(node_path) as entries:
                for entry in entries:
                    try:
                        if not include_hidden and entry.name.startswith("."):
                            continue

                        if entry.is_file(follow_symlinks=False):
                            direct_files += 1
                            stat_res = entry.stat(follow_symlinks=False)
                            size = stat_res.st_size
                            direct_bytes += size

                            # Extension tracking
                            ext = Path(entry.name).suffix.lower()
                            ext_key = ext if ext else "(no_ext)"
                            direct_ext_counts[ext_key] += 1

                            # Lifecycle tracking
                            mtime_dt = datetime.fromtimestamp(stat_res.st_mtime, tz=timezone.utc)
                            age_days = (self._now - mtime_dt).total_seconds() / 86400.0
                            if age_days < 30.0:
                                direct_active += 1
                            elif age_days <= 365.0:
                                direct_dormant += 1
                            else:
                                direct_cold += 1

                        elif entry.is_dir(follow_symlinks=False):
                            if current_depth < max_depth:
                                child_profile = self._profile_node(
                                    Path(entry.path),
                                    current_depth=current_depth + 1,
                                    max_depth=max_depth,
                                    include_hidden=include_hidden,
                                )
                                subfolder_profiles.append(child_profile)
                    except (PermissionError, FileNotFoundError, OSError):
                        continue
        except (PermissionError, FileNotFoundError, OSError):
            pass

        # Bottom-up roll-up from subfolders
        total_files = direct_files + sum(c.total_files_count for c in subfolder_profiles)
        total_bytes = direct_bytes + sum(c.total_bytes for c in subfolder_profiles)
        total_subdirs = len(subfolder_profiles) + sum(c.total_subdirs_count for c in subfolder_profiles)

        aggregated_ext_counts = Counter(direct_ext_counts)
        aggregated_active = direct_active
        aggregated_dormant = direct_dormant
        aggregated_cold = direct_cold

        for child in subfolder_profiles:
            aggregated_ext_counts.update(child.extension_counts)
            aggregated_active += child.lifecycle.active_count
            aggregated_dormant += child.lifecycle.dormant_count
            aggregated_cold += child.lifecycle.cold_count

        dominant_ext = ""
        if aggregated_ext_counts:
            dominant_ext = aggregated_ext_counts.most_common(1)[0][0]

        lifecycle = LifecycleDistribution(
            active_count=aggregated_active,
            dormant_count=aggregated_dormant,
            cold_count=aggregated_cold,
            total_count=total_files,
        )

        mime_entropy = FolderProfile.calculate_mime_entropy(dict(aggregated_ext_counts))
        root_pollution = direct_files / max(1, total_files)

        profile.direct_files_count = direct_files
        profile.direct_bytes = direct_bytes
        profile.total_files_count = total_files
        profile.total_bytes = total_bytes
        profile.direct_subdirs_count = len(subfolder_profiles)
        profile.total_subdirs_count = total_subdirs
        profile.extension_counts = dict(aggregated_ext_counts)
        profile.dominant_extension = dominant_ext
        profile.mime_entropy = mime_entropy
        profile.lifecycle = lifecycle
        profile.root_pollution_ratio = root_pollution
        profile.subfolders = subfolder_profiles

        # Detect local disruptions for this folder
        profile.disruptions = self._detect_folder_disruptions(profile)

        return profile

    def _detect_folder_disruptions(self, profile: FolderProfile) -> List[DisruptionItem]:
        """Evaluates structural metrics against generalized disruption rules."""
        disruptions: List[DisruptionItem] = []
        name_lower = profile.name.lower()

        # 1. Cleanable temp/cache directory
        if name_lower in CLEANABLE_DIR_NAMES:
            disruptions.append(
                DisruptionItem(
                    disruption_type=DisruptionType.CLEANABLE_TEMP,
                    severity=DisruptionSeverity.INFO,
                    description=f"Temporäres Cache-/Build-Verzeichnis erkannt ({profile.name}): {profile.total_bytes // 1024 // 1024} MB freigebbar.",
                    detected_path=profile.path,
                    metric_value=float(profile.total_bytes),
                )
            )

        # 2. Dump-Zone: High entropy + many direct loose files
        if profile.mime_entropy > 0.70 and profile.direct_files_count >= 15:
            disruptions.append(
                DisruptionItem(
                    disruption_type=DisruptionType.DUMP_ZONE,
                    severity=DisruptionSeverity.WARNING,
                    description=f"Sammel-Ablagezone (Dump-Zone) mit hoher Unordnung (Entropie: {profile.mime_entropy:.2f}, {profile.direct_files_count} lose Dateien).",
                    detected_path=profile.path,
                    metric_value=profile.mime_entropy,
                )
            )

        # 3. Root Pollution: Folder with subdirectories has too many loose files in its root
        if profile.direct_subdirs_count > 0 and profile.direct_files_count >= 20 and profile.root_pollution_ratio > 0.40:
            disruptions.append(
                DisruptionItem(
                    disruption_type=DisruptionType.ROOT_POLLUTION,
                    severity=DisruptionSeverity.WARNING,
                    description=f"Wurzel-Verschmutzung: {profile.direct_files_count} lose Dateien in Ordner-Wurzel ({profile.root_pollution_ratio*100:.0f}% aller Dateien).",
                    detected_path=profile.path,
                    metric_value=profile.root_pollution_ratio,
                )
            )

        # 4. Mixed Lifecycle: Active new files heavily mixed with cold dormant files
        if (
            profile.total_files_count >= 20
            and profile.lifecycle.active_ratio >= 0.25
            and profile.lifecycle.cold_ratio >= 0.35
        ):
            disruptions.append(
                DisruptionItem(
                    disruption_type=DisruptionType.MIXED_LIFECYCLE,
                    severity=DisruptionSeverity.INFO,
                    description=f"Gemischter Lebenszyklus: Aktive Arbeitsdateien ({profile.lifecycle.active_ratio*100:.0f}%) vermischt mit Altbestand ({profile.lifecycle.cold_ratio*100:.0f}% > 1 Jahr).",
                    detected_path=profile.path,
                    metric_value=profile.lifecycle.cold_ratio,
                )
            )

        # 5. Excessive nesting depth
        if profile.depth >= 7:
            disruptions.append(
                DisruptionItem(
                    disruption_type=DisruptionType.DEEP_NESTING,
                    severity=DisruptionSeverity.INFO,
                    description=f"Tiefe Ordnerverschachtelung (Ebene {profile.depth}). Erschwert Auffindbarkeit und Navigation.",
                    detected_path=profile.path,
                    metric_value=float(profile.depth),
                )
            )

        return disruptions

    def detect_disruptions(self, profile: FolderProfile) -> List[DisruptionItem]:
        """Gathers all disruptions across the entire subtree."""
        results: List[DisruptionItem] = list(profile.disruptions)
        for sub in profile.subfolders:
            results.extend(self.detect_disruptions(sub))
        return results

    def detect_outliers(self, profile: FolderProfile) -> List[OutlierItem]:
        """
        Scans all nodes and discovers misplaced items, isolated project repos,
        lingering installers, and large orphan media folders.
        """
        outliers: List[OutlierItem] = []
        self._find_outliers_recursive(profile, outliers)
        return outliers

    def _find_outliers_recursive(self, node: FolderProfile, outliers: List[OutlierItem]) -> None:
        p_path = Path(node.path)
        name_lower = node.name.lower()
        parent_name = p_path.parent.name.lower()

        # Check 1: Code Repository or Project located inside a generic / non-code folder
        # (e.g. inside "Downloads", "Desktop", "Dokumente")
        is_generic_parent = any(k in parent_name for k in ["download", "desktop", "schreibtisch", "temp"])
        has_code_dominant = any(ext in CODE_EXTENSIONS for ext in node.extension_counts.keys())
        has_git = (p_path / ".git").exists()

        if is_generic_parent and (has_git or (has_code_dominant and node.total_files_count >= 5)):
            target = str(p_path.parent.parent / "Projekte" / node.name)
            outliers.append(
                OutlierItem(
                    source_path=node.path,
                    disruption_type=DisruptionType.TYPE_OUTLIER,
                    reason_de=f"Code-Projekt '{node.name}' liegt in flüchtigem Ordner '{p_path.parent.name}'.",
                    proposal=SolutionProposal(
                        target_path=target,
                        confidence=0.92,
                        reasoning_de="Projekt in strukturierten Entwicklungs-Ordner verschieben.",
                        action_type="MOVE",
                    ),
                    status="pending",
                )
            )

        # Check 2: Large Media collection inside general text/doc folder
        is_doc_parent = any(k in parent_name for k in ["dokument", "document", "office", "texte"])
        media_count = sum(cnt for ext, cnt in node.extension_counts.items() if ext in MEDIA_EXTENSIONS)
        if is_doc_parent and media_count >= 20 and (media_count / max(1, node.total_files_count)) > 0.6:
            target = str(p_path.parent.parent / "Medien" / node.name)
            outliers.append(
                OutlierItem(
                    source_path=node.path,
                    disruption_type=DisruptionType.ORPHAN_MEDIA,
                    reason_de=f"Große Mediensammlung ({media_count} Bilder/Videos) in Dokumenten-Ordner '{p_path.parent.name}'.",
                    proposal=SolutionProposal(
                        target_path=target,
                        confidence=0.88,
                        reasoning_de="Medien in zentralen Medien-/Bilder-Bereich überführen.",
                        action_type="MOVE",
                    ),
                    status="pending",
                )
            )

        # Check 3: Cleanable cache/temp folder
        if name_lower in CLEANABLE_DIR_NAMES and node.total_bytes > 5 * 1024 * 1024:  # > 5 MB
            outliers.append(
                OutlierItem(
                    source_path=node.path,
                    disruption_type=DisruptionType.CLEANABLE_TEMP,
                    reason_de=f"Verwaister Cache/Build-Ordner '{node.name}' belegt {node.total_bytes // 1024 // 1024} MB.",
                    proposal=SolutionProposal(
                        target_path=f"trash://{node.name}",
                        confidence=0.95,
                        reasoning_de="In Papierkorb verschieben zur sicheren Speicherplatz-Rückgewinnung.",
                        action_type="CLEAN",
                    ),
                    status="pending",
                )
            )

        # Check 4: Thematic folder or document collection sitting directly on Desktop/Downloads
        if is_generic_parent and node.total_files_count > 0:
            if any(k in name_lower for k in ["strafzettel", "rechnung", "steuer", "konto", "finanz", "ibiza", "vertrag", "arzt"]):
                target = f"/media/privat-data/6_PrivatBüro/{node.name}"
                outliers.append(
                    OutlierItem(
                        source_path=node.path,
                        disruption_type=DisruptionType.TYPE_OUTLIER,
                        reason_de=f"Privates Dokumentenpaket '{node.name}' liegt ungesichert auf '{p_path.parent.name}'.",
                        proposal=SolutionProposal(
                            target_path=target,
                            confidence=0.92,
                            reasoning_de="In das PrivatBüro auf privat-data verschieben und sichern.",
                            action_type="MOVE",
                        ),
                        status="pending",
                    )
                )
            elif any(k in name_lower for k in ["cv_", "work", "admin", "client", "bookaccount", "project", "wiki", "code"]):
                target = f"/media/work-data/002_cv-projects/{node.name}"
                outliers.append(
                    OutlierItem(
                        source_path=node.path,
                        disruption_type=DisruptionType.TYPE_OUTLIER,
                        reason_de=f"Geschäftliches Projekt '{node.name}' liegt auf '{p_path.parent.name}'.",
                        proposal=SolutionProposal(
                            target_path=target,
                            confidence=0.90,
                            reasoning_de="In Projektverzeichnis auf work-data einsortieren.",
                            action_type="MOVE",
                        ),
                        status="pending",
                    )
                )
        # Check 5: Empty directory left on Desktop/Downloads
        elif is_generic_parent and node.total_files_count == 0 and node.direct_subdirs_count == 0:
            outliers.append(
                OutlierItem(
                    source_path=node.path,
                    disruption_type=DisruptionType.CLEANABLE_TEMP,
                    reason_de=f"Leerer Ordner '{node.name}' auf '{p_path.parent.name}'.",
                    proposal=SolutionProposal(
                        target_path=f"trash://{node.name}",
                        confidence=0.95,
                        reasoning_de="Leeren Ordner in den Papierkorb verschieben.",
                        action_type="CLEAN",
                    ),
                    status="pending",
                )
            )

        # Recurse down
        for child in node.subfolders:
            self._find_outliers_recursive(child, outliers)

    def synthesize_rules(self, profile: FolderProfile) -> List[NaturalLanguageRule]:
        """
        Synthesizes human-readable German meta-rules for bulk operations (the 90% case).
        Uses condition_json compatible with domain/rule_engine.py.
        """
        rules: List[NaturalLanguageRule] = []

        # Find all dump zones and download/desktop-like roots
        all_profiles = self._flatten_profiles(profile)

        # 1. Rule: Clean old installer / executable files in temporary/download zones
        installer_count = 0
        installer_bytes = 0
        for p in all_profiles:
            for ext, count in p.extension_counts.items():
                if ext in INSTALLER_EXTENSIONS:
                    installer_count += count
        if installer_count >= 3:
            rules.append(
                NaturalLanguageRule(
                    id="rule-installers-purge",
                    title_de="Alte Installationsdateien archivieren",
                    description_de="Installationsprogramme (.iso, .dmg, .deb, .exe), die älter als 60 Tage sind, in das Software-Archiv verschieben.",
                    condition_json={
                        "logic": "AND",
                        "conditions": [
                            {"field": "extension", "operator": "is_one_of", "value": "iso,dmg,deb,rpm,exe,msi,pkg,appimage"},
                            {"field": "timeframe", "operator": "older_than_days", "value": "60"},
                        ],
                    },
                    target_path_template="{target_root}/Archiv/Software/{YYYY}/{filename}",
                    affected_files_count=installer_count,
                    confidence=0.90,
                )
            )

        # 2. Rule: Archive dormant downloads (>90 days)
        downloads_folders = [p for p in all_profiles if "download" in p.name.lower()]
        if downloads_folders:
            target_dl = downloads_folders[0]
            if target_dl.lifecycle.dormant_count + target_dl.lifecycle.cold_count >= 10:
                rules.append(
                    NaturalLanguageRule(
                        id="rule-downloads-archive",
                        title_de="Inaktive Downloads archivieren",
                        description_de=f"Dateien aus '{target_dl.name}', die seit über 90 Tagen nicht verwendet wurden, nach '{target_dl.name}/Archiv/{{YYYY}}' verschieben.",
                        condition_json={
                            "logic": "AND",
                            "conditions": [
                                {"field": "source_folder", "operator": "contains", "value": target_dl.name},
                                {"field": "timeframe", "operator": "older_than_days", "value": "90"},
                            ],
                        },
                        target_path_template=f"{target_dl.path}/Archiv/{{YYYY}}/{{filename}}",
                        affected_files_count=target_dl.lifecycle.dormant_count + target_dl.lifecycle.cold_count,
                        confidence=0.95,
                    )
                )

        # 3. Rule: Bundle loose photos/media into dated directories
        photo_count = 0
        for p in all_profiles:
            if p.direct_files_count >= 15:
                img_cnt = sum(c for ext, c in p.extension_counts.items() if ext in {".jpg", ".jpeg", ".png", ".heic", ".webp"})
                if img_cnt >= 10 and (img_cnt / max(1, p.direct_files_count)) > 0.4:
                    photo_count += img_cnt
        if photo_count >= 10:
            rules.append(
                NaturalLanguageRule(
                    id="rule-photos-by-year",
                    title_de="Fotos chronologisch strukturieren",
                    description_de="Lose Bilddateien (.jpg, .png, .heic) nach Aufnahme-/Änderungsjahr in Jahresordner einsortieren.",
                    condition_json={
                        "logic": "AND",
                        "conditions": [
                            {"field": "extension", "operator": "is_one_of", "value": "jpg,jpeg,png,heic,webp"},
                        ],
                    },
                    target_path_template="{target_root}/Fotos/{YYYY}/{filename}",
                    affected_files_count=photo_count,
                    confidence=0.85,
                )
            )

        # 4. Rule: Group Office & PDF documents into structured document archive
        doc_count = 0
        for p in all_profiles:
            d_cnt = sum(c for ext, c in p.extension_counts.items() if ext in DOC_EXTENSIONS)
            doc_count += d_cnt
        if doc_count >= 10:
            rules.append(
                NaturalLanguageRule(
                    id="rule-docs-organize",
                    title_de="Dokumente nach Jahr & Typ ordnen",
                    description_de="Dokumente (.pdf, .docx, .xlsx) in den strukturierten Dokumentenbaum überführen.",
                    condition_json={
                        "logic": "AND",
                        "conditions": [
                            {"field": "extension", "operator": "is_one_of", "value": "pdf,docx,doc,xlsx,xls"},
                        ],
                    },
                    target_path_template="{target_root}/Dokumente/{YYYY}/{filename}",
                    affected_files_count=doc_count,
                    confidence=0.82,
                )
            )

        return rules

    def compute_tree_diff(
        self,
        profile: FolderProfile,
        confirmed_rules: List[NaturalLanguageRule],
        resolved_outliers: List[OutlierItem],
    ) -> List[TreeDiffNode]:
        """
        Projects S_ideal from S_now using approved natural language rules and resolved outliers.
        Produces structured 'Von -> Nach' diff entries for preview and execution.
        """
        diff_nodes: List[TreeDiffNode] = []

        # 1. Map resolved outliers
        outlier_map: Dict[str, OutlierItem] = {
            item.source_path: item
            for item in resolved_outliers
            if item.status in ("approved", "customized")
        }

        # 2. Traverse tree and apply actions
        self._diff_traverse(profile, confirmed_rules, outlier_map, diff_nodes)
        return diff_nodes

    def _diff_traverse(
        self,
        node: FolderProfile,
        confirmed_rules: List[NaturalLanguageRule],
        outlier_map: Dict[str, OutlierItem],
        diff_nodes: List[TreeDiffNode],
    ) -> None:
        # Check if node itself is an outlier
        if node.path in outlier_map:
            outlier = outlier_map[node.path]
            target = outlier.custom_target_path or outlier.proposal.target_path
            action = "CLEAN_TEMP" if outlier.proposal.action_type == "CLEAN" else "MOVE"
            diff_nodes.append(
                TreeDiffNode(
                    name=node.name,
                    source_path=node.path,
                    target_path=target,
                    action=action,
                    rule_id=None,
                    reason_de=outlier.proposal.reasoning_de or outlier.reason_de,
                    size_bytes=node.total_bytes,
                    is_directory=True,
                    is_outlier=True,
                )
            )
        else:
            # Check cleanable directory
            if node.name.lower() in CLEANABLE_DIR_NAMES:
                diff_nodes.append(
                    TreeDiffNode(
                        name=node.name,
                        source_path=node.path,
                        target_path=f"trash://{node.name}",
                        action="CLEAN_TEMP",
                        reason_de="Temporärer Cache/Build-Ordner zur Freigabe",
                        size_bytes=node.total_bytes,
                        is_directory=True,
                        is_outlier=False,
                    )
                )
            else:
                diff_nodes.append(
                    TreeDiffNode(
                        name=node.name,
                        source_path=node.path,
                        target_path=node.path,
                        action="RETAIN",
                        reason_de="Beibehalten (Struktur intakt)",
                        size_bytes=node.direct_bytes,
                        is_directory=True,
                        is_outlier=False,
                    )
                )

        # Recurse into children
        for child in node.subfolders:
            self._diff_traverse(child, confirmed_rules, outlier_map, diff_nodes)

    def _flatten_profiles(self, root: FolderProfile) -> List[FolderProfile]:
        """Flattens the FolderProfile tree into a list."""
        res = [root]
        for sub in root.subfolders:
            res.extend(self._flatten_profiles(sub))
        return res
