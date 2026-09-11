# Frontend Audit Report: hermes-auto-organizer Dashboard Plugin

Below is the severity-ranked list of findings from the static analysis of `src/hermes_auto_organizer/dashboard/dist/index.js` and its interactions with the backend API `src/hermes_auto_organizer/dashboard/plugin_api.py`.

No XSS vulnerabilities or injection risks were found, as the app strictly uses React's `h` (createElement) which safely escapes variables by default, and there is no usage of `dangerouslySetInnerHTML`.

## 1. 🔴 Critical React Anti-Pattern: Component Functions Called as Regular Functions (UI State/Performance)
**Location:** `App()` (lines ~187-192)
**Problem:** The tab components are executed as standard JavaScript function calls (e.g., `QuellenTab()`) instead of being mounted as React components (e.g., `h(QuellenTab)`).
**Why it matters:** This severely breaks component isolation by hoisting all hooks from every tab directly into the parent `App` component. Any state change in one tab (like typing a single character in a path input) forces every single tab to completely re-render and execute all of their logic. While it technically doesn't currently throw a hook violation because the number of hooks inside the tabs is static, it causes massive performance degradation and is highly fragile.
**Suggested Fix:**
```javascript
// BEFORE:
h("div", { style: { display: tab === "quellen" ? "block" : "none" } }, QuellenTab()),

// AFTER:
h("div", { style: { display: tab === "quellen" ? "block" : "none" } }, h(QuellenTab)),
// (Repeat for all other tabs)
```

## 2. 🔴 API Contract Mismatch: Rule Creation Fails with 422 (Backend Crash)
**Location:** `RegelnTab.createRule()` (line ~423)
**Problem:** The frontend sends `condition_json` as a string (`"{}"`) in the payload body. However, `plugin_api.py` defines `RuleCreateRequest.condition_json` as a `Dict[str, Any]`.
**Why it matters:** Pydantic strictly validates the payload and will reject it with a `422 Unprocessable Entity` error. Creating new rules will fail 100% of the time.
**Suggested Fix:**
```javascript
// BEFORE:
condition_json: "{}",

// AFTER:
condition_json: {},
```

## 3. 🟠 API Contract Mismatch: Taxonomy Tree Silently Fails to Render (UI Bug)
**Location:** `TaxonomieTab()` (line ~342)
**Problem:** The JS code attempts to render the tree using `nodes && treeNodes(nodes.nodes, 0)`. However, the `/taxonomy` endpoint returns the tree array under the key `tree` (i.e., `{ ok: true, total_nodes: X, tree: [...] }`).
**Why it matters:** `nodes.nodes` is `undefined`. When passed to `treeNodes(undefined, 0)`, the function returns `null`, causing the taxonomy tree to silently fail to render and just show an empty UI space despite loading successfully.
**Suggested Fix:**
```javascript
// BEFORE:
nodes && treeNodes(nodes.nodes, 0)

// AFTER:
nodes && treeNodes(nodes.tree, 0)
```

## 4. 🟠 Missing Error Handling: TypeErrors on Failed API Calls (Crash Risk)
**Location:** Multiple (e.g., `RegelnTab.sendChat` line 407, `QuellenTab.scan` line 249, `VorschauTab.execute` line 489)
**Problem:** The custom `fetchJSON` helper catches all internal errors and resolves to `null` if the request fails (e.g. 500 or network drop). However, the `.then(function (d) { ... })` callbacks blindly assume `d` is an object and access properties on it.
**Why it matters:** If an API call fails, accessing `d.thought_process`, `d.executed_count`, etc., will throw an unhandled `TypeError: Cannot read properties of null`, breaking React's execution flow and leaving UI elements stuck (like loading spinners permanently active).
**Suggested Fix:**
Add a null check at the start of these callbacks. Example for `sendChat`:
```javascript
// BEFORE:
fetchJSON(...).then(function (d) {
  setChatHistory(... d.thought_process ...);
});

// AFTER:
fetchJSON(...).then(function (d) {
  if (!d) return; // Add null check
  setChatHistory(... d.thought_process ...);
});
```

## 5. 🟡 API Contract Mismatch: Undefined Data in Alerts (UI Bug)
**Location:** `VorschauTab.execute()` (line 489) and `QuellenTab.scan()` (line 249)
**Problem:** The success alerts try to display properties that the backend does not return:
- Execute alert uses `d.executed_count` and `d.failed_count`, but the API returns `d.executed` and `d.failed`.
- Scan alert uses `d.total_files` and `d.duplicates_found`, but the API returns `d.files_indexed` (and doesn't return duplicate counts).
**Why it matters:** Users will see alerts saying "Ausgeführt: undefined Dateien, undefined Fehler", causing confusion.
**Suggested Fix:**
```javascript
// VorschauTab execute
alert("Ausgeführt: " + d.executed + " Dateien, " + d.failed + " Fehler.");

// QuellenTab scan
alert("Scan abgeschlossen: " + d.files_indexed + " Dateien verarbeitet.");
```

## 6. 🟡 React Anti-Pattern: Race Condition in `useEffect` (UI Bug)
**Location:** `QuellenTab` (line 211)
**Problem:** `useEffect(function () { loadTree(path); }, [path]);` makes an async API call whenever the user modifies the path string. There is no cleanup or abortion of previous requests.
**Why it matters:** If a user types quickly, out-of-order network responses could result in `setTree` writing stale data over the final path's data, causing the UI to display the wrong folder contents.
**Suggested Fix:** Implement a boolean flag in the effect cleanup.
```javascript
useEffect(function () {
  var active = true;
  setLoading(true);
  fetchJSON(API_BASE + "/sources/tree?path=" + encodeURIComponent(path))
    .then(function (d) {
      if (active) { setTree(d); setLoading(false); }
    })
    .catch(function () { if (active) setLoading(false); });
  return function () { active = false; };
}, [path]);
```