## 2026-09-12 - Dashboard Plugin Single-File JS Bundle Architecture
**Learning:** In the hermes-auto-organizer dashboard plugin, `src/hermes_auto_organizer/dashboard/dist/index.js` serves as the primary source file for the plain React IIFE bundle rather than a build artifact generated from a separate build pipeline.
**Action:** When adding accessibility or micro-UX enhancements (such as ARIA labels) to the dashboard plugin UI, modify `src/hermes_auto_organizer/dashboard/dist/index.js` directly and verify changes using pytest suite.
