"""Configuration for hermes-drive-index.

Configuration precedence (highest to lowest):

1. Explicit overrides passed to :func:`load_config` (e.g. CLI flags / API args)
2. Environment variables (``HERMES_DRIVE_INDEX_*``)
3. A local TOML config file
4. Built-in defaults

``default_config()`` is preserved as a zero-argument convenience that resolves
the same paths as before when no overrides are supplied.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
import tomllib

from hermes_drive_index.core.organize import OrganizeConfig, OrganizeRule
from hermes_drive_index.core.sync import SyncMapping

DEFAULT_OCR_PDF_ARGS = ("--rotate-pages", "--deskew")
_SAFE_OCRMYPDF_FLAGS_WITH_VALUES = {
    "--image-dpi": str.isdigit,
    "--tesseract-pagesegmode": str.isdigit,
}
_SAFE_OCRMYPDF_FLAGS = {
    "--rotate-pages",
    "--deskew",
    "--remove-background",
}

try:
    from hermes_constants import get_hermes_home
except Exception:  # pragma: no cover - used outside Hermes
    def get_hermes_home() -> str:
        return str(Path.home() / ".hermes")


@dataclass(frozen=True)
class DriveIndexConfig:
    root_folder_id: str | None
    root_folder_name: str
    base_dir: Path
    cache_dir: Path
    db_path: Path
    google_api_dir: Path
    config_path: Path
    # OCR is disabled by default and consumed only when explicitly enabled.
    ocr_enabled: bool = False
    ocr_image_enabled: bool = False
    ocr_pdf_args: tuple[str, ...] = DEFAULT_OCR_PDF_ARGS
    include_folders: tuple[str, ...] = ()
    exclude_folders: tuple[str, ...] = ()
    auto_organize: OrganizeConfig = field(default_factory=OrganizeConfig)
    local_drives: tuple[Path, ...] = ()
    sync_mappings: tuple[SyncMapping, ...] = ()


def _local_config_path(hermes_home: Path, override: str | None = None) -> Path:
    raw = override or os.getenv("HERMES_DRIVE_INDEX_CONFIG") or hermes_home / "drive_index" / "config.toml"
    return Path(raw).expanduser()


def _load_local_config(path: Path) -> dict:
    if not path.exists():
        return {}
    return tomllib.loads(path.read_text())


def _path(value, default: Path) -> Path:
    return Path(value if value is not None else default).expanduser()


def _pick(override, env_name: str, local: dict, key: str):
    """Resolve a single value: explicit override > env > TOML > None."""
    if override is not None:
        return override
    env_val = os.getenv(env_name)
    if env_val is not None:
        return env_val
    return local.get(key)


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _as_tuple(value) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(str(v) for v in value if str(v).strip())
    return tuple(item for item in str(value).split(os.pathsep) if item.strip())


def _safe_ocr_pdf_args(value) -> tuple[str, ...]:
    args = _as_tuple(value) or DEFAULT_OCR_PDF_ARGS
    safe: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in _SAFE_OCRMYPDF_FLAGS:
            safe.append(arg)
            i += 1
            continue
        validator = _SAFE_OCRMYPDF_FLAGS_WITH_VALUES.get(arg)
        if validator is None:
            raise ValueError(f"Unsupported OCRmyPDF argument: {arg}")
        if i + 1 >= len(args):
            raise ValueError(f"OCRmyPDF argument requires a value: {arg}")
        value_arg = args[i + 1]
        if value_arg.startswith("--") or not validator(value_arg):
            raise ValueError(f"Unsupported OCRmyPDF value for {arg}: {value_arg}")
        safe.extend((arg, value_arg))
        i += 2
    return tuple(safe)


def _organize_config(local: dict, overrides: dict) -> OrganizeConfig:
    raw_candidate = local.get("auto_organize")
    raw: dict = raw_candidate if isinstance(raw_candidate, dict) else {}
    rules_raw = raw.get("rules") or []
    rules = tuple(
        OrganizeRule(
            name=str(item.get("name") or item.get("category") or "rule"),
            pattern=str(item.get("pattern") or ".*"),
            target_folder_path=str(item.get("target_folder_path") or item.get("target") or ""),
            category=str(item.get("category")) if item.get("category") is not None else None,
            rename_template=str(item.get("rename_template")) if item.get("rename_template") is not None else None,
        )
        for item in rules_raw
        if isinstance(item, dict) and (item.get("target_folder_path") or item.get("target"))
    )
    dry_raw = _pick(overrides.get("auto_organize_dry_run"), "HERMES_DRIVE_INDEX_AUTO_ORGANIZE_DRY_RUN", raw, "dry_run")
    return OrganizeConfig(
        enabled=_as_bool(_pick(overrides.get("auto_organize_enabled"), "HERMES_DRIVE_INDEX_AUTO_ORGANIZE", raw, "enabled")),
        dry_run=_as_bool(dry_raw) if dry_raw is not None else True,
        apply_to_existing=_as_bool(_pick(overrides.get("auto_organize_apply_to_existing"), "HERMES_DRIVE_INDEX_AUTO_ORGANIZE_APPLY_TO_EXISTING", raw, "apply_to_existing")),
        default_target_folder_path=_pick(overrides.get("auto_organize_default_target_folder_path"), "HERMES_DRIVE_INDEX_AUTO_ORGANIZE_DEFAULT_TARGET", raw, "default_target_folder_path"),
        rename_template=str(_pick(overrides.get("auto_organize_rename_template"), "HERMES_DRIVE_INDEX_AUTO_ORGANIZE_RENAME_TEMPLATE", raw, "rename_template") or "{date} - {category} - {title}{ext}"),
        rules=rules,
    )


def _sync_mappings(local: dict, overrides: dict) -> tuple[SyncMapping, ...]:
    raw_list = overrides.get("sync_mappings") or local.get("sync_mappings") or []
    mappings: list[SyncMapping] = []
    for item in raw_list:
        if isinstance(item, dict) and item.get("name") and (item.get("local_path") or item.get("local")):
            mappings.append(
                SyncMapping(
                    name=str(item["name"]),
                    local_path=Path(item.get("local_path") or item.get("local")).expanduser(),
                    drive_folder_path=str(item.get("drive_folder_path") or item.get("drive") or ""),
                    drive_folder_id=str(item.get("drive_folder_id")) if item.get("drive_folder_id") else None,
                    direction=str(item.get("direction", "bidirectional")),
                    include_patterns=tuple(item.get("include_patterns", ())),
                    exclude_patterns=tuple(item.get("exclude_patterns", ())),
                )
            )
        elif isinstance(item, SyncMapping):
            mappings.append(item)
    return tuple(mappings)


def load_config(overrides: dict | None = None) -> DriveIndexConfig:
    """Resolve configuration following explicit > env > TOML > default precedence.

    ``overrides`` keys map to ``DriveIndexConfig`` fields (``config_path``,
    ``base_dir``, ``root_folder_id``, ``root_folder_name``, ``google_api_dir``,
    ``db_path``, ``ocr_enabled``, ``ocr_image_enabled``, ``ocr_pdf_args``,
    ``include_folders``, ``exclude_folders``, ``local_drives``, ``sync_mappings``).
    ``None`` values are ignored (treated as "not set").
    """
    overrides = {k: v for k, v in (overrides or {}).items() if v is not None}
    hermes_home = Path(get_hermes_home())
    config_path = _local_config_path(hermes_home, overrides.get("config_path"))
    local = _load_local_config(config_path)

    base_dir = _path(
        _pick(overrides.get("base_dir"), "HERMES_DRIVE_INDEX_BASE_DIR", local, "base_dir"),
        hermes_home / "drive_index" / "personal_files",
    )
    root_folder_id = _pick(overrides.get("root_folder_id"), "HERMES_DRIVE_INDEX_ROOT_FOLDER_ID", local, "root_folder_id")
    root_folder_name = _pick(overrides.get("root_folder_name"), "HERMES_DRIVE_INDEX_ROOT_FOLDER_NAME", local, "root_folder_name") or "Personal Files"
    google_api_dir = _path(
        _pick(overrides.get("google_api_dir"), "HERMES_DRIVE_INDEX_GOOGLE_API_DIR", local, "google_api_dir"),
        hermes_home / "skills" / "productivity" / "google-workspace" / "scripts",
    )
    db_path = _path(
        _pick(overrides.get("db_path"), "HERMES_DRIVE_INDEX_DB_PATH", local, "db_path"),
        base_dir / "index.db",
    )
    ocr_enabled = _as_bool(_pick(overrides.get("ocr_enabled"), "HERMES_DRIVE_INDEX_OCR", local, "ocr_enabled"))
    ocr_image_enabled = _as_bool(_pick(overrides.get("ocr_image_enabled"), "HERMES_DRIVE_INDEX_OCR_IMAGE", local, "ocr_image_enabled"))
    ocr_pdf_args = _safe_ocr_pdf_args(_pick(overrides.get("ocr_pdf_args"), "HERMES_DRIVE_INDEX_OCR_PDF_ARGS", local, "ocr_pdf_args"))
    include_folders = _as_tuple(_pick(overrides.get("include_folders"), "HERMES_DRIVE_INDEX_INCLUDE_FOLDERS", local, "include_folders"))
    exclude_folders = _as_tuple(_pick(overrides.get("exclude_folders"), "HERMES_DRIVE_INDEX_EXCLUDE_FOLDERS", local, "exclude_folders"))
    auto_organize = _organize_config(local, overrides)
    raw_local_drives = _pick(overrides.get("local_drives"), "HERMES_DRIVE_INDEX_LOCAL_DRIVES", local, "local_drives")
    local_drives = tuple(Path(p).expanduser() for p in _as_tuple(raw_local_drives))
    sync_mappings = _sync_mappings(local, overrides)

    return DriveIndexConfig(
        root_folder_id=root_folder_id,
        root_folder_name=root_folder_name,
        base_dir=base_dir,
        cache_dir=base_dir / "cache",
        db_path=db_path,
        google_api_dir=google_api_dir,
        config_path=config_path,
        ocr_enabled=ocr_enabled,
        ocr_image_enabled=ocr_image_enabled,
        ocr_pdf_args=ocr_pdf_args,
        include_folders=include_folders,
        exclude_folders=exclude_folders,
        auto_organize=auto_organize,
        local_drives=local_drives,
        sync_mappings=sync_mappings,
    )


def default_config() -> DriveIndexConfig:
    return load_config()
