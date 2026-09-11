## 2026-03-30 - Accessible Modal Dialogs and Icon-Only Controls in Vanilla React createElement Apps

**Learning:** Single-file React applications using `React.createElement` often lack ARIA attributes on modal overlays (`role="dialog"`, `aria-modal="true"`, `aria-labelledby`) and on icon-only interactive controls (`"✕"`, `"🗑"`, `"+"`, `"-"`), rendering them opaque or ambiguous to screen readers.
**Action:** Always provide explicit `aria-label` attributes for symbol/emoji buttons and assign standard dialog ARIA roles (`role="dialog"`, `aria-modal="true"`, `aria-labelledby`) on backdrop overlay containers.
