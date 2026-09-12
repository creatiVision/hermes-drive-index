## 2026-03-30 - Accessible Modal Dialogs and Icon-Only Controls in Vanilla React createElement Apps

**Learning:** Single-file React applications using `React.createElement` often lack ARIA attributes on modal overlays (`role="dialog"`, `aria-modal="true"`, `aria-labelledby`) and on icon-only interactive controls (`"✕"`, `"🗑"`, `"+"`, `"-"`), rendering them opaque or ambiguous to screen readers.
**Action:** Always provide explicit `aria-label` attributes for symbol/emoji buttons and assign standard dialog ARIA roles (`role="dialog"`, `aria-modal="true"`, `aria-labelledby`) on backdrop overlay containers.

## 2026-09-12 - Dashboard Plugin Single-File JS Bundle Architecture
**Learning:** In the hermes-auto-organizer dashboard plugin, `src/hermes_auto_organizer/dashboard/dist/index.js` serves as the primary source file for the plain React IIFE bundle rather than a build artifact generated from a separate build pipeline.
**Action:** When adding accessibility or micro-UX enhancements (such as ARIA labels) to the dashboard plugin UI, modify `src/hermes_auto_organizer/dashboard/dist/index.js` directly and verify changes using pytest suite.

