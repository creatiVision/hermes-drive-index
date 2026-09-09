/**
 * Hermes Auto-Organizer — Dashboard Plugin Bundle
 *
 * Tabbed dashboard: Quellen | Übersicht | Taxonomie | Regeln | Vorschau | Journal
 * Left-rail + main-panel layout. Dark theme, pure React.createElement, no JSX.
 *
 * Plain IIFE compatible with window.__HERMES_PLUGIN_SDK__.
 */
(function () {
  "use strict";

  const API_BASE = "/api/plugins/auto-organizer";
  const SDK = window.__HERMES_PLUGIN_SDK__;
  const authedFetch = SDK && SDK.authedFetch;

  // ---- React (loaded by host page) ----
  const React = window.React || window.__HERMES_PLUGIN_SDK__.React;
  const h = React.createElement;
  const useState = React.useState;
  const useEffect = React.useEffect;
  const useCallback = React.useCallback;
  const useRef = React.useRef;

  // ---- Inline dark-theme styles ----
  if (typeof document !== "undefined") {
    if (!document.getElementById("auto-org-dashboard-style")) {
      const s = document.createElement("style");
      s.id = "auto-org-dashboard-style";
      s.textContent = `
        .ao-root { display:flex; flex-direction:column; height:100vh; background:#0f172a; color:#f8fafc; font-family:system-ui,sans-serif; }
        .ao-topbar { display:flex; align-items:center; justify-content:space-between; padding:12px 20px; border-bottom:1px solid #334155; background:#1e293b; }
        .ao-topbar-title { font-size:16px; font-weight:600; }
        .ao-topbar-spacer { flex:1; }
        .ao-btn { background:#3b82f6; color:#fff; border:none; border-radius:6px; padding:8px 14px; cursor:pointer; font-size:13px; }
        .ao-btn:hover { background:#2563eb; }
        .ao-btn-ghost { background:transparent; color:#94a3b8; border:1px solid #334155; border-radius:6px; padding:6px 12px; cursor:pointer; font-size:12px; }
        .ao-btn-ghost:hover { background:#334155; color:#f8fafc; }
        .ao-btn-danger { background:#ef4444; color:#fff; border:none; border-radius:6px; padding:6px 12px; cursor:pointer; font-size:12px; }
        .ao-btn-sm { padding:4px 10px; font-size:12px; }
        .ao-rail { width:210px; min-width:210px; border-right:1px solid #334155; background:#0f172a; padding:12px 0; overflow-y:auto; display:flex; flex-direction:column; }
        .ao-rail-tab { display:flex; align-items:center; gap:8px; padding:10px 16px; cursor:pointer; font-size:13px; color:#94a3b8; border:none; background:none; width:100%; text-align:left; }
        .ao-rail-tab:hover { background:#1e293b; color:#f8fafc; }
        .ao-rail-tab.active { background:#1e293b; color:#3b82f6; font-weight:600; border-right:3px solid #3b82f6; }
        .ao-rail-bottom { margin-top:auto; padding:12px 16px; border-top:1px solid #334155; }
        .ao-main { flex:1; overflow-y:auto; padding:16px; }
        .ao-card { background:#1e293b; border:1px solid #334155; border-radius:8px; padding:16px; margin-bottom:12px; }
        .ao-card-title { font-size:14px; font-weight:600; margin-bottom:10px; }
        .ao-stat-row { display:flex; flex-wrap:wrap; gap:12px; }
        .ao-stat { flex:1; min-width:140px; background:#0f172a; border:1px solid #334155; border-radius:6px; padding:12px; }
        .ao-stat-label { font-size:11px; color:#64748b; text-transform:uppercase; letter-spacing:0.5px; }
        .ao-stat-value { font-size:22px; font-weight:700; margin-top:4px; }
        .ao-progress { height:6px; background:#334155; border-radius:3px; margin-top:8px; overflow:hidden; }
        .ao-progress-bar { height:100%; background:#3b82f6; border-radius:3px; transition:width 0.3s; }
        .ao-tree-node { margin:2px 0; }
        .ao-tree-row { display:flex; align-items:center; gap:6px; padding:4px 8px; border-radius:4px; cursor:pointer; font-size:13px; }
        .ao-tree-row:hover { background:#1e293b; }
        .ao-tree-row.selected { background:#1e3a5f; }
        .ao-tree-caret { width:14px; text-align:center; color:#64748b; cursor:pointer; }
        .ao-tree-caret.expanded { transform:rotate(90deg); }
        .ao-tree-indent { flex:1; }
        .ao-tree-name { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
        .ao-checkbox { width:16px; height:16px; accent-color:#3b82f6; cursor:pointer; }
        .ao-badge { display:inline-block; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:600; }
        .ao-badge-green { background:#166534; color:#4ade80; }
        .ao-badge-red { background:#7f1d1d; color:#fca5a5; }
        .ao-badge-yellow { background:#854d0e; color:#fde047; }
        .ao-badge-gray { background:#334155; color:#94a3b8; }
        .ao-badge-blue { background:#1e3a5f; color:#93c5fd; }
        .ao-table { width:100%; border-collapse:collapse; font-size:13px; }
        .ao-table th { text-align:left; padding:8px 10px; color:#64748b; font-weight:600; border-bottom:1px solid #334155; }
        .ao-table td { padding:8px 10px; border-bottom:1px solid #1e293b; }
        .ao-table tr:hover td { background:#1e293b; }
        .ao-modal-overlay { position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.6); display:flex; align-items:center; justify-content:center; z-index:1000; }
        .ao-modal { background:#1e293b; border:1px solid #334155; border-radius:8px; padding:24px; max-width:560px; width:90%; max-height:80vh; overflow-y:auto; }
        .ao-modal-title { font-size:16px; font-weight:600; margin-bottom:16px; }
        .ao-form-group { margin-bottom:12px; }
        .ao-form-label { display:block; font-size:12px; color:#94a3b8; margin-bottom:4px; }
        .ao-form-input { width:100%; background:#0f172a; color:#f8fafc; border:1px solid #475569; border-radius:6px; padding:8px 10px; font-size:13px; box-sizing:border-box; }
        .ao-form-input::placeholder { color:#64748b; }
        .ao-form-textarea { resize:vertical; min-height:60px; }
        .ao-empty { text-align:center; padding:40px; color:#64748b; font-size:13px; }
        .ao-spinner { display:inline-block; width:16px; height:16px; border:2px solid #334155; border-top-color:#3b82f6; border-radius:50%; animation:spin 0.6s linear infinite; }
        @keyframes spin { to { transform:rotate(360deg); } }
        .ao-tag { display:inline-block; background:#1e3a5f; color:#93c5fd; border-radius:4px; padding:2px 6px; font-size:11px; margin-right:4px; }
        .ao-chat-box { background:#0f172a; border:1px solid #334155; border-radius:6px; padding:8px; margin-top:8px; }
        .ao-chat-msg { font-size:12px; padding:4px 0; color:#94a3b8; }
        .ao-chat-msg.user { color:#f8fafc; text-align:right; }
        .ao-collapse { overflow:hidden; transition:height 0.2s; }
        .ao-collapse-content { padding-top:8px; }
      `;
      document.head.appendChild(s);
    }
  }

  // ---- Helpers ----
  function fetchJSON(url, opts) {
    return authedFetch
      ? authedFetch(url, opts)
      : fetch(url, Object.assign({ credentials: "same-origin" }, opts || {})).then(function (r) { return r.json(); });
  }

  function badgeHtml(type, label) {
    var cls = "ao-badge";
    if (type === "green") cls += " ao-badge-green";
    else if (type === "red") cls += " ao-badge-red";
    else if (type === "yellow") cls += " ao-badge-yellow";
    else if (type === "gray") cls += " ao-badge-gray";
    else if (type === "blue") cls += " ao-badge-blue";
    return h("span", { className: cls }, label);
  }

  function spinner() {
    return h("span", { className: "ao-spinner" });
  }

  function Button(props) {
    return h("button", Object.assign({ className: "ao-btn" }, props));
  }

  function GhostButton(props) {
    return h("button", Object.assign({ className: "ao-btn-ghost" }, props));
  }

  // ---- Modal ----
  function SettingsModal() {
    var [health, setHealth] = useState(null);
    var [mounts, setMounts] = useState(null);
    var [loading, setLoading] = useState(true);
    useEffect(function () {
      Promise.all([
        fetchJSON(API_BASE + "/health"),
        fetchJSON(API_BASE + "/mounts")
      ]).then(function (res) {
        setHealth(res[0]);
        setMounts(res[1]);
        setLoading(false);
      }).catch(function () { setLoading(false); });
    }, []);

    if (loading) return h("div", { className: "ao-modal-overlay" }, h("div", { className: "ao-modal" }, spinner()));

    var dbStatus = health && health.database_connected
      ? badgeHtml("green", "verbunden")
      : badgeHtml("red", "getrennt");

    var rows = (mounts && mounts.mounts) ? mounts.mounts.map(function (m) {
      return h("div", { className: "ao-form-group" },
        h("div", { style: { display:"flex", justifyContent:"space-between", fontSize:"13px" } },
          h("span", null, m.label || m.host_path),
          badgeHtml(m.is_writable ? "green" : "red", m.is_writable ? "RW" : "RO")
        )
      );
    }) : [];

    return h("div", { className: "ao-modal-overlay" },
      h("div", { className: "ao-modal", style: { maxWidth: "480px" } },
        h("div", { className: "ao-modal-title" }, "Einstellungen"),
        h("div", { className: "ao-card" },
          h("div", { className: "ao-card-title" }, "Datenbank-Status"),
          h("div", { style: { display:"flex", gap:"12px", alignItems:"center" } },
            badgeHtml(health && health.ok ? "green" : "red", health && health.ok ? "Plugin OK" : "Fehler"),
            dbStatus,
            h("span", { style: { fontSize:"12px", color:"#64748b" } },
              "Tabellen: " + (health ? health.table_count : "?")
            )
          )
        ),
        h("div", { className: "ao-card" },
          h("div", { className: "ao-card-title" }, "Docker-Mounts (" + (mounts ? mounts.total_mounts : 0) + ")"),
          rows.length ? h("div", null, rows) : h("div", { className: "ao-empty" }, "Keine Mounts konfiguriert")
        ),
        h("div", { style: { display:"flex", justifyContent:"flex-end", marginTop:"16px" } },
          GhostButton({ onClick: function () { document.getElementById("ao-settings-modal").remove(); } }, "Schließen")
        )
      )
    );
  }

  // ---- Root App ----
  function App() {
    var [tab, setTab] = useState("quellen");
    var [showSettings, setShowSettings] = useState(false);

    var tabs = [
      { id: "quellen", icon: "📁", label: "Quellen" },
      { id: "uebersicht", icon: "📊", label: "Übersicht" },
      { id: "taxonomie", icon: "🗺️", label: "Taxonomie" },
      { id: "regeln", icon: "📋", label: "Regeln" },
      { id: "vorschau", icon: "▶", label: "Vorschau" },
      { id: "journal", icon: "📜", label: "Journal" }
    ];

    return h("div", { className: "ao-root", id: "auto-org-dashboard" },
      h("div", { className: "ao-topbar" },
        h("div", { className: "ao-topbar-title" }, "Auto-Organizer"),
        h("div", { className: "ao-topbar-spacer" }, null),
        GhostButton({ onClick: function () { setShowSettings(true); } }, "⚙ Einstellungen")
      ),
      h("div", { style: { display:"flex", flex:1, overflow:"hidden" } },
        h("nav", { className: "ao-rail" },
          tabs.map(function (t) {
            return h("button", {
              className: "ao-rail-tab" + (tab === t.id ? " active" : ""),
              onClick: function () { setTab(t.id); }
            }, h("span", null, t.icon), h("span", null, t.label));
          }),
          h("div", { className: "ao-rail-bottom" },
            h("button", { className: "ao-btn", style: { width:"100%" } },
              h("span", null, "🔍 Scannen")
            )
          )
        ),
        h("main", { className: "ao-main" },
          tab === "quellen" && QuellenTab(),
          tab === "uebersicht" && UebersichtTab(),
          tab === "taxonomie" && TaxonomieTab(),
          tab === "regeln" && RegelnTab(),
          tab === "vorschau" && VorschauTab(),
          tab === "journal" && JournalTab()
        )
      ),
      showSettings && h("div", { id: "ao-settings-modal" }, h(SettingsModal))
    );
  }

  // ── Tab 1: Quellen ──────────────────────────────────────────────────────
  function QuellenTab() {
    var [path, setPath] = useState("/");
    var [tree, setTree] = useState(null);
    var [loading, setLoading] = useState(false);
    var [expanded, setExpanded] = useState({});
    var [checked, setChecked] = useState({});

    function loadTree(p) {
      setLoading(true);
      fetchJSON(API_BASE + "/sources/tree?path=" + encodeURIComponent(p))
        .then(function (d) { setTree(d); setLoading(false); })
        .catch(function () { setLoading(false); });
    }
    useEffect(function () { loadTree(path); }, [path]);

    function toggleExpand(id) {
      setExpanded(Object.assign({}, expanded, { [id]: !expanded[id] }));
    }

    function toggleCheck(id, ev) {
      ev.stopPropagation();
      setChecked(Object.assign({}, checked, { [id]: !checked[id] }));
    }

    function nodeRows(nodes, indent) {
      if (!nodes || !nodes.length) return null;
      return nodes.map(function (n) {
        var hasChildren = n.node_type === "folder";
        var isOpen = expanded[n.id];
        var sel = checked[n.id] ? " selected" : "";
        var rows = [];
        rows.push(h("div", { className: "ao-tree-node" },
          h("div", { className: "ao-tree-row" + sel, onClick: function () {
            if (hasChildren) toggleExpand(n.id);
          } },
            hasChildren
              ? h("span", { className: "ao-tree-caret" + (isOpen ? " expanded" : ""), onClick: function (e) { e.stopPropagation(); toggleExpand(n.id); } }, "▶")
              : h("span", { className: "ao-tree-caret" }, "·"),
            h("span", { style: { paddingLeft: (indent || 0) + "px" } }, null),
            h("input", { type: "checkbox", className: "ao-checkbox", checked: !!checked[n.id], onClick: function (e) { toggleCheck(n.id, e); } }),
            h("span", { className: "ao-tree-name" }, n.name || n.path)
          )
        ));
        if (isOpen && hasChildren) {
          rows.push(nodeRows(n.children, (indent || 0) + 16));
        }
        return rows;
      });
    }

    var containerPath = path === "/" ? "/" : path.substring(0, path.lastIndexOf("/") || 0);

    return h("div", null,
      h("div", { className: "ao-card" },
        h("div", { className: "ao-card-title" }, "📁 Quellen — Dateisystem"),
        loading && spinner(),
        tree && !loading && h("div", { style: { marginTop:"8px" } },
          nodeRows(tree.children, 0)
        ),
        !tree && !loading && h("div", { className: "ao-empty" }, "Baum laden…")
      ),
      h("div", { className: "ao-card" },
        h("div", { style: { display:"flex", justifyContent:"space-between", alignItems:"center" } },
          h("div", null,
            h("span", { style: { fontSize:"12px", color:"#94a3b8" } }, "Pfad: "),
            h("input", {
              className: "ao-form-input",
              style: { width:"240px", fontSize:"13px" },
              value: path,
              onChange: function (e) { setPath(e.target.value); }
            }),
            h("button", { className: "ao-btn-ghost ao-btn-sm", onClick: function () { loadTree(path); } }, "Neu laden")
          ),
          h("button", { className: "ao-btn", onClick: function () {
            var paths = Object.keys(checked).filter(function (k) { return checked[k]; });
            if (!paths.length) { alert("Bitte mindestens einen Ordner auswählen."); return; }
            fetchJSON(API_BASE + "/sources/scan", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ roots: paths })
            }).then(function (d) {
              alert("Scan abgeschlossen: " + d.total_files + " Dateien, " + d.duplicates_found + " Duplikate.");
            });
          } }, "▶ Scannen")
        )
      )
    );
  }

  // ── Tab 2: Übersicht ────────────────────────────────────────────────────
  function UebersichtTab() {
    var [stats, setStats] = useState(null);
    var [mounts, setMounts] = useState(null);
    useEffect(function () {
      Promise.all([
        fetchJSON(API_BASE + "/stats"),
        fetchJSON(API_BASE + "/mounts")
      ]).then(function (r) { setStats(r[0]); setMounts(r[1]); });
    }, []);

    function statCard(label, value, sub, color) {
      return h("div", { className: "ao-stat" },
        h("div", { className: "ao-stat-label" }, label),
        h("div", { className: "ao-stat-value", style: { color: color || "#f8fafc" } }, value),
        sub ? h("div", { style: { fontSize:"11px", color:"#64748b", marginTop:"2px" } }, sub) : null
      );
    }

    if (!stats) return h("div", { className: "ao-empty" }, "Lade Statistiken…");

    var mountBars = (mounts && mounts.mounts) ? mounts.mounts.map(function (m) {
      var pct = m.total_gb > 0 ? (m.free_gb / m.total_gb) * 100 : 0;
      return h("div", { className: "ao-stat", key: m.host_path },
        h("div", { className: "ao-stat-label" }, m.label || m.host_path),
        h("div", { className: "ao-stat-value", style: { fontSize:"14px" } },
          m.free_gb.toFixed(1) + " GB frei von " + m.total_gb.toFixed(1) + " GB"
        ),
        h("div", { className: "ao-progress" },
          h("div", { className: "ao-progress-bar", style: { width: pct + "%" } })
        )
      );
    }) : [];

    return h("div", null,
      h("div", { className: "ao-stat-row" },
        statCard("Gesamtdateien", stats.total_files, "Indexerade Dateien"),
        statCard("Gesamtgröße", (stats.total_size_mb || 0).toFixed(0) + " MB", "Auf allen Wurzeln"),
        statCard("Duplikate", stats.open_anomalies || 0, "Offene Anomalien", "#fca5a5"),
        statCard("Aktive Regeln", stats.active_rules || 0, "Konfigurierte Regeln", "#93c5fd"),
        statCard("Recent Batches", stats.recent_batches || 0, "Letzte Ausführungen")
      ),
      h("div", { className: "ao-card", style: { marginTop:"12px" } },
        h("div", { className: "ao-card-title" }, "💾 Datenträger"),
        h("div", { className: "ao-stat-row" }, mountBars.length ? mountBars : h("div", { className: "ao-empty" }, "Keine Mounts"))
      )
    );
  }

  // ── Tab 3: Taxonomie ────────────────────────────────────────────────────
  function TaxonomieTab() {
    var [nodes, setNodes] = useState(null);
    var [expanded, setExpanded] = useState({});
    var [newName, setNewName] = useState("");
    var [newPath, setNewPath] = useState("");
    var [newParent, setNewParent] = useState("");
    var [saving, setSaving] = useState(false);

    useEffect(function () {
      fetchJSON(API_BASE + "/taxonomy").then(function (d) { setNodes(d); });
    }, []);

    function toggleExpand(id) {
      setExpanded(Object.assign({}, expanded, { [id]: !expanded[id] }));
    }

    function stateBadge(state) {
      if (state === "approved") return badgeHtml("green", "🟢 genehmigt");
      if (state === "excluded") return badgeHtml("red", "⚪ excluded");
      return badgeHtml("yellow", "🟡 vorgeschlagen");
    }

    function toggleState(id, newState) {
      fetchJSON(API_BASE + "/taxonomy/node", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: id, state: newState })
      }).then(function () { fetchJSON(API_BASE + "/taxonomy").then(function (d) { setNodes(d); }); });
    }

    function addNode() {
      if (!newName || !newPath) return;
      setSaving(true);
      fetchJSON(API_BASE + "/taxonomy/node", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          parent_id: newParent || null,
          node_name: newName,
          node_path: newPath,
          state: "proposed",
          source: "user"
        })
      }).then(function () {
        setNewName(""); setNewPath(""); setSaving(false);
        fetchJSON(API_BASE + "/taxonomy").then(function (d) { setNodes(d); });
      });
    }

    function treeNodes(ns, indent) {
      if (!ns || !ns.length) return null;
      return ns.map(function (n) {
        var isOpen = expanded[n.id];
        var rows = [];
        rows.push(h("div", { className: "ao-tree-node" },
          h("div", { className: "ao-tree-row", onClick: function () { toggleExpand(n.id); } },
            h("span", { className: "ao-tree-caret expanded", style: { cursor:"pointer" } }, "▶"),
            h("span", { style: { paddingLeft: (indent || 0) + "px" } }, null),
            h("span", { className: "ao-tree-name" }, n.node_name || n.node_path),
            h("span", { style: { marginLeft:"8px", fontSize:"11px", color:"#64748b" } },
              "⚡" + (n.confidence != null ? n.confidence : "?") + "%"
            ),
            stateBadge(n.state)
          )
        ));
        if (n.children && n.children.length) {
          rows.push(treeNodes(n.children, (indent || 0) + 16));
        }
        return rows;
      });
    }

    return h("div", null,
      h("div", { className: "ao-card" },
        h("div", { className: "ao-card-title" }, "🗺️ Taxonomie — Zielordner-Struktur"),
        nodes && treeNodes(nodes.nodes, 0),
        !nodes && h("div", { className: "ao-empty" }, "Lade Taxonomie…")
      ),
      h("div", { className: "ao-card" },
        h("div", { className: "ao-card-title" }, "Neuer Knoten"),
        h("div", { className: "ao-form-group" },
          h("label", { className: "ao-form-label" }, "Name"),
          h("input", { className: "ao-form-input", value: newName, onChange: function (e) { setNewName(e.target.value); } })
        ),
        h("div", { className: "ao-form-group" },
          h("label", { className: "ao-form-label" }, "Pfad"),
          h("input", { className: "ao-form-input", value: newPath, onChange: function (e) { setNewPath(e.target.value); } })
        ),
        h("div", { className: "ao-form-group" },
          h("label", { className: "ao-form-label" }, "Elternknoten (optional)"),
          h("input", { className: "ao-form-input", value: newParent, onChange: function (e) { setNewParent(e.target.value); } })
        ),
        h("div", { style: { display:"flex", gap:"8px" } },
          Button({ onClick: addNode, disabled: saving || !newName || !newPath }, "Hinzufügen"),
          GhostButton({ onClick: function () { setNewName(""); setNewPath(""); setNewParent(""); } }, "Reset")
        )
      )
    );
  }

  // ── Tab 4: Regeln ───────────────────────────────────────────────────────
  function RegelnTab() {
    var [rules, setRules] = useState(null);
    var [chatOpen, setChatOpen] = useState({});
    var [chatMsg, setChatMsg] = useState({});
    var [chatHistory, setChatHistory] = useState({});
    var [newName, setNewName] = useState("");
    var [newDesc, setNewDesc] = useState("");
    var [newSource, setNewSource] = useState("");
    var [newTarget, setNewTarget] = useState("");
    var [creating, setCreating] = useState(false);

    useEffect(function () {
      fetchJSON(API_BASE + "/rules").then(function (d) { setRules(d); });
    }, []);

    function toggleRule(id) {
      fetchJSON(API_BASE + "/rules/" + id + "/toggle", { method: "POST" })
        .then(function () { fetchJSON(API_BASE + "/rules").then(function (d) { setRules(d); }); });
    }

    function sendChat(id, msg) {
      if (!msg.trim()) return;
      setChatHistory(Object.assign({}, chatHistory, {
        [id]: (chatHistory[id] || []).concat({ role: "user", text: msg })
      }));
      setChatMsg(Object.assign({}, chatMsg, { [id]: "" }));
      fetchJSON(API_BASE + "/rules/" + id + "/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg })
      }).then(function (d) {
        setChatHistory(Object.assign({}, chatHistory, {
          [id]: (chatHistory[id] || []).concat({ role: "ai", text: d.thought_process || "" })
        }));
      });
    }

    function createRule() {
      if (!newName || !newTarget) return;
      setCreating(true);
      fetchJSON(API_BASE + "/rules", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          rule_name: newName,
          description: newDesc,
          source_pattern: newSource,
          condition_json: "{}",
          target_path_template: newTarget,
          state: "active"
        })
      }).then(function () {
        setNewName(""); setNewDesc(""); setNewSource(""); setNewTarget(""); setCreating(false);
        fetchJSON(API_BASE + "/rules").then(function (d) { setRules(d); });
      });
    }

    function ruleCard(r) {
      var isOpen = chatOpen[r.id];
      var thought = r.thought_process || "Kein Gedankenprozess konfiguriert.";
      var stateCls = r.state === "active" ? "green" : "red";
      var stateLabel = r.state === "active" ? "🟢 aktiv" : "🔴 disabled";
      return h("div", { className: "ao-card" },
        h("div", { className: "ao-tree-row", style: { justifyContent:"space-between", cursor:"pointer" }, onClick: function () { setChatOpen(Object.assign({}, chatOpen, { [r.id]: !isOpen })); } },
          h("div", null,
            h("div", { style: { fontWeight:600, fontSize:"14px" } }, r.rule_name),
            h("div", { style: { fontSize:"12px", color:"#94a3b8", marginTop:"2px" } },
              "Von: " + (r.source_pattern || "—") + " → Nach: " + (r.target_path_template || "—")
            )
          ),
          badgeHtml(stateCls, stateLabel)
        ),
        h("div", { style: { display:"flex", gap:"6px", marginTop:"6px" } },
          GhostButton({ className: "ao-btn-sm", onClick: function () { toggleRule(r.id); } }, r.state === "active" ? "Deaktivieren" : "Aktivieren"),
          GhostButton({ className: "ao-btn-sm", onClick: function () { setChatOpen(Object.assign({}, chatOpen, { [r.id]: !isOpen })); } }, "Gedankenprozess")
        ),
        isOpen && h("div", { className: "ao-collapse-content" },
          h("div", { style: { fontSize:"12px", color:"#94a3b8", padding:"8px", background:"#0f172a", borderRadius: "4px", marginBottom:"8px" } },
            thought
          ),
          h("div", { className: "ao-chat-box" },
            (chatHistory[r.id] || []).map(function (m) {
              return h("div", { className: "ao-chat-msg " + (m.role === "user" ? "user" : "") }, m.text);
            }),
            h("div", { style: { display:"flex", gap:"4px", marginTop:"6px" } },
              h("input", {
                className: "ao-form-input",
                style: { flex:1, fontSize:"12px", padding:"4px 6px" },
                placeholder: "Nachricht an Regel…",
                value: chatMsg[r.id] || "",
                onChange: function (e) { setChatMsg(Object.assign({}, chatMsg, { [r.id]: e.target.value })); },
                onKeyDown: function (e) { if (e.key === "Enter") sendChat(r.id, e.target.value); }
              }),
              h("button", { className: "ao-btn ao-btn-sm", onClick: function () { sendChat(r.id, chatMsg[r.id] || ""); } }, "Send")
            )
          )
        )
      );
    }

    var ruleList = rules && rules.rules ? rules.rules.map(ruleCard) : null;

    return h("div", null,
      h("div", { className: "ao-card" },
        h("div", { className: "ao-card-title" }, "📋 Regeln"),
        ruleList || h("div", { className: "ao-empty" }, "Keine Regeln vorhanden")
      ),
      h("div", { className: "ao-card" },
        h("div", { className: "ao-card-title" }, "Neue Regel"),
        h("div", { className: "ao-form-group" },
          h("label", { className: "ao-form-label" }, "Name"),
          h("input", { className: "ao-form-input", value: newName, onChange: function (e) { setNewName(e.target.value); } })
        ),
        h("div", { className: "ao-form-group" },
          h("label", { className: "ao-form-label" }, "Beschreibung"),
          h("input", { className: "ao-form-input", value: newDesc, onChange: function (e) { setNewDesc(e.target.value); } })
        ),
        h("div", { className: "ao-form-group" },
          h("label", { className: "ao-form-label" }, "Quellmuster"),
          h("input", { className: "ao-form-input", value: newSource, onChange: function (e) { setNewSource(e.target.value); } })
        ),
        h("div", { className: "ao-form-group" },
          h("label", { className: "ao-form-label" }, "Zielpfad-Vorlage"),
          h("input", { className: "ao-form-input", value: newTarget, onChange: function (e) { setNewTarget(e.target.value); } })
        ),
        h("div", { style: { display:"flex", gap:"8px" } },
          Button({ onClick: createRule, disabled: creating || !newName || !newTarget }, "Regel erstellen"),
          GhostButton({ onClick: function () { setNewName(""); setNewDesc(""); setNewSource(""); setNewTarget(""); } }, "Reset")
        )
      )
    );
  }

  // ── Tab 5: Vorschau ────────────────────────────────────────────────────
  function VorschauTab() {
    var [preview, setPreview] = useState(null);
    var [loading, setLoading] = useState(false);
    var [executing, setExecuting] = useState(false);

    function runPreview() {
      setLoading(true);
      fetchJSON(API_BASE + "/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({})
      }).then(function (d) { setPreview(d); setLoading(false); }).catch(function () { setLoading(false); });
    }

    function execute() {
      if (!preview || !preview.actions || !preview.actions.length) return;
      setExecuting(true);
      fetchJSON(API_BASE + "/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({})
      }).then(function (d) {
        alert("Ausgeführt: " + d.executed_count + " Dateien, " + d.failed_count + " Fehler.");
        setExecuting(false);
        runPreview();
      });
    }

    useEffect(function () { runPreview(); }, []);

    var summary = preview && preview.summary;
    var actions = preview && preview.actions;

    var statusBadge = function (s) {
      if (s === "valid") return badgeHtml("green", "✓ gültig");
      if (s === "collision") return badgeHtml("yellow", "⚠ Kollision");
      if (s === "blocked") return badgeHtml("red", "✗ blockiert");
      return badgeHtml("gray", s);
    };

    var grouped = actions ? actions.reduce(function (acc, a) {
      (acc[a.rule_name] = acc[a.rule_name] || []).push(a);
      return acc;
    }, {}) : {};

    return h("div", null,
      h("div", { className: "ao-card" },
        h("div", { style: { display:"flex", justifyContent:"space-between", alignItems:"center" } },
          h("div", null,
            h("span", { style: { fontSize:"13px", color:"#94a3b8" } },
              (summary ? summary.total : 0) + " Dateien · " +
              (summary ? summary.valid : 0) + " gültig · " +
              (summary ? summary.collisions : 0) + " Kollisionen · " +
              (summary ? summary.blocked : 0) + " blockiert"
            )
          ),
          h("button", { className: "ao-btn", onClick: runPreview, disabled: loading || executing }, loading ? spinner() : "↻ Neu simulieren")
        )
      ),
      h("div", { className: "ao-card" },
        h("div", { className: "ao-card-title" }, "▶ Vorschau — Dry-Run Ergebnisse"),
        actions && grouped ? Object.keys(grouped).map(function (ruleName) {
          return h("div", { key: ruleName, style: { marginBottom:"16px" } },
            h("div", { style: { fontSize:"12px", color:"#94a3b8", marginBottom:"4px" } },
              h("span", { className: "ao-tag" }, ruleName)
            ),
            h("table", { className: "ao-table" },
              h("thead", h("tr", h("th", "Quellpfad"), h("th", "Zielpfad"), h("th", "Status"))),
              h("tbody", grouped[ruleName].map(function (a) {
                return h("tr", null,
                  h("td", { style: { fontFamily:"monospace", fontSize:"12px" } }, a.source_path),
                  h("td", { style: { fontFamily:"monospace", fontSize:"12px" } }, a.destination_path),
                  h("td", null, statusBadge(a.status))
                );
              }))
            )
          );
        }) : h("div", { className: "ao-empty" }, loading ? spinner() : "Noch keine Vorschau")
      ),
      h("div", { className: "ao-card" },
        h("div", { style: { display:"flex", justifyContent:"flex-end" } },
          h("button", {
            className: "ao-btn",
            onClick: execute,
            disabled: !actions || !actions.length || executing,
            style: { background: executing ? "#64748b" : "#22c55e" }
          }, executing ? spinner() : "▶ Ausführen")
        )
      )
    );
  }

  // ── Tab 6: Journal ─────────────────────────────────────────────────────
  function JournalTab() {
    var [batches, setBatches] = useState(null);
    var [rollingBack, setRollingBack] = useState({});

    useEffect(function () {
      fetchJSON(API_BASE + "/journal").then(function (d) { setBatches(d); });
    }, []);

    function rollback(id) {
      setRollingBack(Object.assign({}, rollingBack, { [id]: true }));
      fetchJSON(API_BASE + "/journal/" + id + "/rollback", { method: "POST" })
        .then(function (d) {
          alert("Rollback abgeschlossen: " + d.reverted_count + " Dateien zurückgesetzt.");
          setRollingBack(Object.assign({}, rollingBack, { [id]: false }));
          fetchJSON(API_BASE + "/journal").then(function (d) { setBatches(d); });
        });
    }

    var rows = batches && batches.batches ? batches.batches.map(function (b) {
      var statusBadge = b.status === "completed"
        ? badgeHtml("green", "✓ abgeschlossen")
        : b.status === "failed"
          ? badgeHtml("red", "✗ fehlgeschlagen")
          : badgeHtml("yellow", "⚠ teilweise");
      return h("tr", { key: b.batch_id },
        h("td", { style: { fontSize:"12px", color:"#94a3b8" } },
          new Date(b.executed_at).toLocaleString("de-DE")
        ),
        h("td", b.file_count),
        h("td", null, statusBadge),
        h("td", null,
          h("button", { className: "ao-btn-ghost ao-btn-sm", onClick: function () { rollback(b.batch_id); } },
            rollingBack[b.batch_id] ? spinner() : "↩ Rollback"
          )
        )
      );
    }) : null;

    return h("div", null,
      h("div", { className: "ao-card" },
        h("div", { className: "ao-card-title" }, "📜 Journal — Ausführungsverlauf"),
        batches && rows ? h("table", { className: "ao-table" },
          h("thead", h("tr",
            h("th", "Datum"),
            h("th", "Dateien"),
            h("th", "Status"),
            h("th", "")
          )),
          h("tbody", rows)
        ) : h("div", { className: "ao-empty" }, "Kein Journal vorhanden")
      )
    );
  }

  // ---- Mount ----
  if (typeof document !== "undefined") {
    var container = document.getElementById("auto-org-dashboard") || document.body;
    ReactDOM = window.ReactDOM || window.__HERMES_PLUGIN_SDK__.ReactDOM;
    if (ReactDOM && ReactDOM.createRoot) {
      ReactDOM.createRoot(container).render(h(App));
    } else if (ReactDOM) {
      ReactDOM.render(h(App), container);
    }
  }
})();
