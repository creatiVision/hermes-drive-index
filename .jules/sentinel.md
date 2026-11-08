# Sentinel Journal

## 2026-04-16 - Hardcoded Database Fallback Password in Plugin API
**Vulnerability:** A hardcoded plaintext database password was used as the default fallback in `src/hermes_auto_organizer/dashboard/plugin_api.py` (`DB_PASS = os.getenv("HERMES_DB_PASSWORD", "81914287...")`), which was also embedded into a module-level `DSN` connection string on import.
**Learning:** Fallback defaults in environment variable lookups often sneak into production files during local testing or rapid prototyping, inadvertently exposing credentials and leaking them into module-level DSN strings.
**Prevention:** Always default sensitive configuration such as `HERMES_DB_PASSWORD` to an empty string. Validate and construct connection strings strictly using variables provided via the environment without hardcoded fallback secrets.

## 2026-04-17 - Remote Python Code Injection in SSH Node Execution
**Vulnerability:** Remote node inspection and subtree profiling commands passed filesystem paths and parameters directly into inline Python script templates (`f"root = Path('{remote_path}')\n"`), allowing arbitrary Python execution and shell command injection over SSH.
**Learning:** Formatting parameters into Python code strings executed remotely via `python3 -c` is equivalent to an unsanitized `eval()` on remote machines.
**Prevention:** Always serialize untrusted or filesystem-supplied paths with `json.dumps(str(...))` or pass them as separate command-line arguments to avoid breaking out of string literals.

## 2026-04-18 - Critical System Directory Cleanup Escape
**Vulnerability:** `DiskCleaningPolicy.assert_cleanup_safe` checked exact equality against `CRITICAL_SYSTEM_PATHS` (e.g. `/etc`), allowing child directories and files within critical system directories (e.g., `/etc/ssh`, `/var/log`, `/usr/bin`) to bypass validation and be admitted for trash cleanup or migration.
**Learning:** Exact set membership checks for path blacklists fail to protect child elements under protected system trees.
**Prevention:** Check path ancestry against critical paths using `Path.parents` or hierarchical prefix checking rather than exact equality alone.

## 2026-04-19 - Unchecked Migration Destination Path in Symlink Migrator
**Vulnerability:** `SymlinkMigratorUseCase.migrate` checked source directory safety via `DiskCleaningPolicy.assert_cleanup_safe(src)` but omitted safety assertions on `dest_dir` and `target_dest`, permitting directory migrations into critical OS trees (e.g. `/etc`, `/usr`) or protected mount roots.
**Learning:** File move and migration operations often focus defensive validation on the source operand being moved or deleted, inadvertently treating the destination directory as inherently safe.
**Prevention:** Always assert path safety and non-critical containment on both source and destination operands (`DiskCleaningPolicy.assert_cleanup_safe`) before filesystem mutation.
