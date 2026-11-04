# Sentinel Journal

## 2026-04-16 - Hardcoded Database Fallback Password in Plugin API
**Vulnerability:** A hardcoded plaintext database password was used as the default fallback in `src/hermes_auto_organizer/dashboard/plugin_api.py` (`DB_PASS = os.getenv("HERMES_DB_PASSWORD", "81914287...")`), which was also embedded into a module-level `DSN` connection string on import.
**Learning:** Fallback defaults in environment variable lookups often sneak into production files during local testing or rapid prototyping, inadvertently exposing credentials and leaking them into module-level DSN strings.
**Prevention:** Always default sensitive configuration such as `HERMES_DB_PASSWORD` to an empty string. Validate and construct connection strings strictly using variables provided via the environment without hardcoded fallback secrets.
