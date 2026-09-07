/**
 * Hermes Auto-Organizer — Dashboard Plugin Bundle
 *
 * 4-Step Guided Workflow with Dedicated Organizational System (Tree / Taxonomy) Approval:
 *   [Step 1: Quelle & Ist-Stand] -> [Step 2: Organisationssystem & Baum-Freigabe] -> [Step 3: Filter-Regeln & Zuordnung] -> [Step 4: Simulation & Reorganisation]
 * with Top Bar Config Tools (Docker Mounts & Pfad-Prüfer, Speicherwurzeln, Journal & 1-Klick Rollback).
 *
 * Plain IIFE compatible with window.__HERMES_PLUGIN_SDK__.
 */
(function () {
  "use strict";

  // Inject bulletproof high-contrast stylesheet into document.head to guarantee
  // that text is crisp, radiant #f8fafc and completely immune to host CSS variable leaks or stale CSS caching.
  if (typeof document !== "undefined" && !document.getElementById("auto-org-bulletproof-contrast")) {
    const styleEl = document.createElement("style");
    styleEl.id = "auto-org-bulletproof-contrast";
    styleEl.textContent = `
      .auto-org-container { color: #f8fafc !important; }
      .auto-org-container, .auto-org-container * {
        box-sizing: border-box;
      }
      .auto-org-container h1, .auto-org-container h2, .auto-org-container h3, .auto-org-container h4 {
        color: #ffffff !important;
      }
      .auto-org-container p, .auto-org-container span, .auto-org-container label, .auto-org-container div, .auto-org-container td {
        color: #f8fafc;
      }
      .auto-org-container th, .auto-org-container .auto-org-subtitle, .auto-org-container .auto-org-step-subtitle, .auto-org-container .auto-org-stat-label {
        color: #94a3b8 !important;
      }
      .auto-org-container select, .auto-org-container input, .auto-org-container textarea {
        background-color: #0f172a !important;
        color: #f8fafc !important;
        -webkit-text-fill-color: #f8fafc !important;
        border: 1px solid #475569 !important;
      }
      .auto-org-container select option, .auto-org-container select optgroup {
        background-color: #1e293b !important;
        color: #f8fafc !important;
        -webkit-text-fill-color: #f8fafc !important;
      }
      .auto-org-container select option:checked {
        background-color: #2563eb !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
      }
      .auto-org-container ::selection {
        background-color: #3b82f6 !important;
        color: #ffffff !important;
      }
    `;
    document.head.appendChild(styleEl);
  }

  const SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK) return;

  const { React } = SDK;
  const h = React.createElement;
  const { useState, useEffect, useCallback } = React;

  const API_BASE = "/api/plugins/auto-organizer";

  async function apiCall(endpoint, options = {}) {
    const url = API_BASE + endpoint;
    const fetchFn = SDK.authedFetch || window.fetch;
    const res = await fetchFn(url, Object.assign({
      headers: { "Content-Type": "application/json" }
    }, options));
    if (!res.ok) {
      const err = await res.text();
      throw new Error(`API Error (${res.status}): ${err}`);
    }
    return await res.json();
  }

  function AutoOrganizerApp() {
    // 4-Step Workflow:
    // 1 = Quelle & Ist-Analyse
    // 2 = Organisationssystem & Baum-Freigabe
    // 3 = Filter-Regeln & Zuordnung
    // 4 = Simulation & Reorganisation
    const [step, setStep] = useState(1);

    // Modal state for top bar config tools: null | "mounts" | "roots" | "journal" | "sync"
    const [activeModal, setActiveModal] = useState(null);

    // Application state
    const [stats, setStats] = useState(null);
    const [roots, setRoots] = useState([]);
    const [anomalies, setAnomalies] = useState([]);
    const [rules, setRules] = useState([]);
    const [dryRun, setDryRun] = useState(null);
    const [batches, setBatches] = useState([]);
    const [mountData, setMountData] = useState(null);
    const [taxonomy, setTaxonomy] = useState(null);
    const [pathCheckInput, setPathCheckInput] = useState("");
    const [pathCheckResult, setPathCheckResult] = useState(null);
    const [checkingPath, setCheckingPath] = useState(false);
    const [loading, setLoading] = useState(false);
    const [notice, setNotice] = useState(null);

    // Google Drive <-> Local Sync Mappings State
    const [syncMappings, setSyncMappings] = useState([]);
    const [syncPlan, setSyncPlan] = useState(null);
    const [syncingId, setSyncingId] = useState(null);
    const [planningId, setPlanningId] = useState(null);
    const [showNewSyncForm, setShowNewSyncForm] = useState(false);
    const [newSyncName, setNewSyncName] = useState("");
    const [newSyncDrivePath, setNewSyncDrivePath] = useState("");
    const [newSyncLocalPath, setNewSyncLocalPath] = useState("");
    const [newSyncDirection, setNewSyncDirection] = useState("bidirectional");
    const [newSyncInclude, setNewSyncInclude] = useState("*.pdf, *.docx, *.xlsx");
    const [newSyncExclude, setNewSyncExclude] = useState("*.tmp, ~*");

    // Step 2 Taxonomy state
    const [showNewNodeForm, setShowNewNodeForm] = useState(false);
    const [newNodeName, setNewNodeName] = useState("");
    const [newNodePath, setNewNodePath] = useState("");
    const [newNodeDesc, setNewNodeDesc] = useState("");
    const [newNodeIcon, setNewNodeIcon] = useState("📁");
    const [newNodeKeywords, setNewNodeKeywords] = useState("");
    const [expandedSamples, setExpandedSamples] = useState({});

    // Step 3 Modular Rule Builder State
    const [ruleName, setRuleName] = useState("");
    const [ruleDesc, setRuleDesc] = useState("");
    const [matchMode, setMatchMode] = useState("all"); // "all" (AND) or "any" (OR)
    const [conditions, setConditions] = useState([
      { field: "source_folder", operator: "starts_with", value: "/home/mb/Downloads", scope: "both" },
      { field: "keyword", operator: "contains", value: "Rechnung", scope: "both" },
      { field: "timeframe", operator: "older_than_days", value: "14", scope: "both" }
    ]);
    const [targetTemplate, setTargetTemplate] = useState("/media/privat-data/10_PrivatBüro/Steuern/{year}/");
    const [testResult, setTestResult] = useState(null);
    const [testing, setTesting] = useState(false);

    const loadData = useCallback(async () => {
      setLoading(true);
      try {
        const [s, r, a, rl, b, m, tx, sm] = await Promise.all([
          apiCall("/stats").catch(() => null),
          apiCall("/roots").catch(() => []),
          apiCall("/anomalies").catch(() => []),
          apiCall("/rules").catch(() => []),
          apiCall("/batches").catch(() => []),
          apiCall("/mounts").catch(() => null),
          apiCall("/taxonomy").catch(() => null),
          apiCall("/sync/mappings").catch(() => ({ mappings: [] })),
        ]);
        if (s) setStats(s);
        setRoots(r || []);
        setAnomalies(a || []);
        setRules(rl || []);
        setBatches(b || []);
        if (m) setMountData(m);
        if (tx) setTaxonomy(tx);
        if (sm && sm.mappings) setSyncMappings(sm.mappings);
      } catch (err) {
        console.error("AutoOrganizer load error:", err);
      } finally {
        setLoading(false);
      }
    }, []);

    useEffect(() => {
      loadData();
    }, [loadData]);

    const handleApproveAllTaxonomy = async () => {
      setLoading(true);
      try {
        const res = await apiCall("/taxonomy/approve", {
          method: "POST",
          body: JSON.stringify({ approve_all: true })
        });
        setNotice(res.message || "Organisationssystem und Verzeichnis-Baum erfolgreich freigegeben!");
        loadData();
      } catch (err) {
        setNotice(`Fehler bei der Freigabe: ${err.message}`);
      } finally {
        setLoading(false);
      }
    };

    const handleToggleNodeApproval = async (nodeId, currentApproved) => {
      setLoading(true);
      try {
        const currentNodes = (taxonomy && taxonomy.tree) || [];
        const newApprovedIds = currentApproved ?
          currentNodes.filter(n => n.id !== nodeId && n.is_approved).map(n => n.id) :
          [...currentNodes.filter(n => n.is_approved).map(n => n.id), nodeId];

        await apiCall("/taxonomy/approve", {
          method: "POST",
          body: JSON.stringify({ approve_all: false, node_ids: newApprovedIds })
        });
        setNotice("Ast-Status im Organisationssystem aktualisiert.");
        loadData();
      } catch (err) {
        setNotice(`Fehler: ${err.message}`);
      } finally {
        setLoading(false);
      }
    };

    const handleAddTaxonomyNode = async (e) => {
      if (e) e.preventDefault();
      if (!newNodeName.trim() || !newNodePath.trim()) {
        alert("Bitte Name und Pfad-Vorlage angeben.");
        return;
      }
      setLoading(true);
      try {
        await apiCall("/taxonomy/node", {
          method: "POST",
          body: JSON.stringify({
            name: newNodeName,
            target_path_template: newNodePath,
            description: newNodeDesc,
            icon: newNodeIcon,
            keywords: newNodeKeywords.split(",").map(k => k.trim()).filter(Boolean),
            extensions: []
          })
        });
        setNewNodeName("");
        setNewNodePath("");
        setNewNodeDesc("");
        setShowNewNodeForm(false);
        setNotice(`Ordner-Ast '${newNodeName}' erfolgreich zum Organisationssystem hinzugefügt!`);
        loadData();
      } catch (err) {
        setNotice(`Fehler beim Speichern: ${err.message}`);
      } finally {
        setLoading(false);
      }
    };

    const handleSaveSyncMapping = async (e) => {
      if (e) e.preventDefault();
      if (!newSyncName.trim() || !newSyncDrivePath.trim() || !newSyncLocalPath.trim()) {
        alert("Bitte Name, Drive-Ordner und Lokalen Pfad angeben.");
        return;
      }
      setLoading(true);
      try {
        const res = await apiCall("/sync/mappings", {
          method: "POST",
          body: JSON.stringify({
            name: newSyncName.trim(),
            drive_folder_path: newSyncDrivePath.trim(),
            local_path: newSyncLocalPath.trim(),
            direction: newSyncDirection,
            include_patterns: newSyncInclude.split(",").map(p => p.trim()).filter(Boolean),
            exclude_patterns: newSyncExclude.split(",").map(p => p.trim()).filter(Boolean),
            is_active: true
          })
        });
        setNotice(res.message || "Sync-Ordner erfolgreich konfiguriert!");
        setShowNewSyncForm(false);
        setNewSyncName("");
        setNewSyncDrivePath("");
        setNewSyncLocalPath("");
        loadData();
      } catch (err) {
        setNotice(`Fehler beim Speichern des Sync-Ordners: ${err.message}`);
      } finally {
        setLoading(false);
      }
    };

    const handleToggleSyncMapping = async (id, currentActive) => {
      try {
        await apiCall("/sync/mappings/toggle", {
          method: "POST",
          body: JSON.stringify({ id, is_active: !currentActive })
        });
        setNotice("Sync-Status aktualisiert.");
        loadData();
      } catch (err) {
        setNotice(`Fehler: ${err.message}`);
      }
    };

    const handleDeleteSyncMapping = async (id, name) => {
      if (!window.confirm(`Sync-Zuordnung '${name}' wirklich entfernen?`)) return;
      try {
        await apiCall(`/sync/mappings/${id}`, { method: "DELETE" });
        setNotice(`Sync-Ordner '${name}' entfernt.`);
        loadData();
      } catch (err) {
        setNotice(`Fehler beim Löschen: ${err.message}`);
      }
    };

    const handleCalculateSyncPlan = async (mappingId) => {
      setPlanningId(mappingId);
      try {
        const plan = await apiCall("/sync/plan", {
          method: "POST",
          body: JSON.stringify({ mapping_id: mappingId })
        });
        setSyncPlan(plan);
        setNotice(`Sync-Plan für '${plan.mapping_name}' berechnet: ${plan.summary.to_upload} Uploads, ${plan.summary.to_download} Downloads.`);
      } catch (err) {
        setNotice(`Fehler bei Plan-Berechnung: ${err.message}`);
      } finally {
        setPlanningId(null);
      }
    };

    const handleExecuteSync = async (mappingId) => {
      setSyncingId(mappingId);
      try {
        const res = await apiCall("/sync/execute", {
          method: "POST",
          body: JSON.stringify({ mapping_id: mappingId })
        });
        setNotice(res.message || "Synchronisation erfolgreich durchgeführt!");
        loadData();
      } catch (err) {
        setNotice(`Fehler bei Synchronisation: ${err.message}`);
      } finally {
        setSyncingId(null);
      }
    };

    const handleApplyTaxonomyBranchToRule = (node) => {
      setTargetTemplate(node.target_path_template);
      if (node.keywords && node.keywords.length > 0) {
        const kwIdx = conditions.findIndex(c => c.field === "keyword");
        if (kwIdx >= 0) {
          handleConditionChange(kwIdx, "value", node.keywords[0]);
        }
      }
      setRuleName(`Sortiere nach ${node.name.split("/").pop() || node.name}`);
      setRuleDesc(`Regel für den freigegebenen Ast '${node.name}'`);
      setStep(3);
      setNotice(`Zielpfad '${node.target_path_template}' aus dem Organisationssystem übernommen!`);
    };

    const handleToggleRule = async (ruleId, currentActive) => {
      try {
        await apiCall("/rules/toggle", {
          method: "POST",
          body: JSON.stringify({ rule_id: ruleId, active: !currentActive }),
        });
        setNotice("Regel-Status erfolgreich aktualisiert.");
        loadData();
      } catch (err) {
        setNotice(`Fehler beim Aktualisieren: ${err.message}`);
      }
    };

    const handleDeleteRule = async (ruleId, rName) => {
      if (!window.confirm(`Regel '${rName}' wirklich löschen?`)) return;
      try {
        await apiCall(`/rules/${ruleId}`, { method: "DELETE" });
        setNotice(`Regel '${rName}' gelöscht.`);
        loadData();
      } catch (err) {
        setNotice(`Fehler beim Löschen: ${err.message}`);
      }
    };

    const handleAddCondition = () => {
      setConditions([
        ...conditions,
        { field: "keyword", operator: "contains", value: "", scope: "both" }
      ]);
    };

    const handleRemoveCondition = (index) => {
      if (conditions.length <= 1) return;
      setConditions(conditions.filter((_, i) => i !== index));
    };

    const handleConditionChange = (index, key, value) => {
      const updated = [...conditions];
      updated[index] = Object.assign({}, updated[index], { [key]: value });

      if (key === "field") {
        if (value === "source_folder") updated[index].operator = "starts_with";
        else if (value === "timeframe") updated[index].operator = "older_than_days";
        else if (value === "keyword") updated[index].operator = "contains";
        else if (value === "extension") updated[index].operator = "is_one_of";
        else if (value === "file_size") updated[index].operator = "greater_than_mb";
      }
      setConditions(updated);
    };

    const handleTestRule = async () => {
      setTesting(true);
      try {
        const res = await apiCall("/rules/test", {
          method: "POST",
          body: JSON.stringify({
            match_mode: matchMode,
            conditions: conditions,
            target_path_template: targetTemplate,
            max_items: 20
          })
        });
        setTestResult(res);
        setNotice(`Simulation: ${res.matches_count} passende Dateien gefunden.`);
      } catch (err) {
        setNotice(`Test fehlgeschlagen: ${err.message}`);
      } finally {
        setTesting(false);
      }
    };

    const handleSaveModularRule = async (e) => {
      if (e) e.preventDefault();
      if (!ruleName.trim()) {
        alert("Bitte einen Regelnamen eingeben.");
        return;
      }
      setLoading(true);
      try {
        await apiCall("/rules", {
          method: "POST",
          body: JSON.stringify({
            name: ruleName,
            description: ruleDesc || "Modulare Filter-Regel",
            match_mode: matchMode,
            conditions: conditions,
            target_path_template: targetTemplate,
            priority: 10,
            state: "USER_APPROVED"
          })
        });
        setRuleName("");
        setRuleDesc("");
        setTestResult(null);
        setNotice(`Modulare Regel '${ruleName}' erfolgreich gespeichert und aktiviert!`);
        loadData();
      } catch (err) {
        setNotice(`Fehler beim Speichern: ${err.message}`);
      } finally {
        setLoading(false);
      }
    };

    const handleRunDryRun = async () => {
      setLoading(true);
      try {
        const result = await apiCall("/dry-run", {
          method: "POST",
          body: JSON.stringify({ max_items: 50 }),
        });
        setDryRun(result);
        setStep(4);
        setNotice(`Dry-Run abgeschlossen: ${result.actions_count} Aktionen vorbereitet.`);
      } catch (err) {
        setNotice(`Dry-Run fehlgeschlagen: ${err.message}`);
      } finally {
        setLoading(false);
      }
    };

    const handleExecuteDryRun = async () => {
      if (!dryRun || !dryRun.batch_id) return;
      if (!window.confirm(`Möchten Sie ${dryRun.safe_count} Datei-Verschiebungen jetzt ausführen? Originale werden mit Papierkorb-Schutz atomar archiviert.`)) {
        return;
      }
      setLoading(true);
      try {
        const res = await apiCall("/execute", {
          method: "POST",
          body: JSON.stringify({ dry_run_batch_id: dryRun.batch_id }),
        });
        setNotice(`Erfolgreich ausgeführt: ${res.executed_count} Dateien verschoben.`);
        setDryRun(null);
        loadData();
        setActiveModal("journal");
      } catch (err) {
        setNotice(`Ausführung fehlgeschlagen: ${err.message}`);
      } finally {
        setLoading(false);
      }
    };

    const handleRollback = async (batchId) => {
      if (!window.confirm(`Batch ${batchId} wirklich zurückrollen und Dateien wiederherstellen?`)) return;
      setLoading(true);
      try {
        const res = await apiCall("/rollback", {
          method: "POST",
          body: JSON.stringify({ batch_id: batchId }),
        });
        setNotice(`Batch zurückgerollt: ${res.reverted_count} Dateien an ihren Ursprungsort wiederhergestellt.`);
        loadData();
      } catch (err) {
        setNotice(`Rollback fehlgeschlagen: ${err.message}`);
      } finally {
        setLoading(false);
      }
    };

    const appendPlaceholder = (ph) => {
      setTargetTemplate(prev => prev.endsWith("/") ? prev + ph : prev + "/" + ph);
    };

    const handleCheckPath = async (pathToTest) => {
      const target = (typeof pathToTest === "string" ? pathToTest : pathCheckInput).trim();
      if (!target) return;
      setCheckingPath(true);
      try {
        const res = await apiCall("/mounts/check", {
          method: "POST",
          body: JSON.stringify({ path: target })
        });
        setPathCheckResult(res);
      } catch (err) {
        setPathCheckResult({ valid: false, message: `Fehler beim Prüfen: ${err.message}` });
      } finally {
        setCheckingPath(false);
      }
    };

    const handleSetRuleSource = (hpath) => {
      const idx = conditions.findIndex(c => c.field === "source_folder");
      if (idx >= 0) {
        handleConditionChange(idx, "value", hpath);
      } else {
        setConditions([{ field: "source_folder", operator: "starts_with", value: hpath, scope: "both" }, ...conditions]);
      }
      setStep(3);
      setActiveModal(null);
      setNotice(`Quellordner im Baukasten auf '${hpath}' gesetzt.`);
    };

    const handleSetRuleTarget = (hpath) => {
      const template = hpath.endsWith("/") ? `${hpath}Archiv/{year}/` : `${hpath}/Archiv/{year}/`;
      setTargetTemplate(template);
      setStep(3);
      setActiveModal(null);
      setNotice(`Zielpfad im Baukasten auf '${template}' gesetzt.`);
    };

    const handleCreateRuleFromAnomaly = (an) => {
      const path = an.physical_path || an.relative_path || "";
      const folder = path.includes("/") ? path.substring(0, path.lastIndexOf("/")) : "/home/mb/Downloads";
      const ext = path.includes(".") ? path.substring(path.lastIndexOf(".") + 1).toLowerCase() : "";

      setRuleName(`Sortiere ${an.anomaly_type === "dump_zone" ? "Downloads" : "Dateien"} (${ext.toUpperCase() || "All"})`);
      setRuleDesc(`Automatisch generiert für ${an.file_name}`);
      setConditions([
        { field: "source_folder", operator: "starts_with", value: folder, scope: "both" },
        ...(ext ? [{ field: "extension", operator: "is_one_of", value: ext, scope: "both" }] : []),
        { field: "timeframe", operator: "older_than_days", value: "7", scope: "both" }
      ]);
      if (an.suggested_target) {
        setTargetTemplate(an.suggested_target.endsWith("/") ? an.suggested_target : an.suggested_target + "/");
      }
      setStep(3);
      setNotice(`Regel-Baukasten mit Daten von '${an.file_name}' vorausgefüllt.`);
    };

    const toggleSampleExpand = (nodeId) => {
      setExpandedSamples(prev => Object.assign({}, prev, { [nodeId]: !prev[nodeId] }));
    };

    // Sub-renderers
    const renderNotice = () => {
      if (!notice) return null;
      return h("div", {
        style: {
          padding: "0.75rem 1rem",
          background: "rgba(59, 130, 246, 0.12)",
          border: "1px solid rgba(59, 130, 246, 0.3)",
          borderRadius: "0.375rem",
          fontSize: "0.875rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center"
        }
      },
        h("span", null, notice),
        h("button", {
          className: "auto-org-btn auto-org-btn-outline",
          style: { padding: "0.1rem 0.4rem", fontSize: "0.75rem" },
          onClick: () => setNotice(null)
        }, "Schließen")
      );
    };

    const renderHeader = () => {
      return h("div", { className: "auto-org-header" },
        h("div", { className: "auto-org-title-group" },
          h("div", { className: "auto-org-title" },
            h("span", null, "📁 Auto-Organizer"),
            stats && stats.db_connected ?
              h("span", { className: "auto-org-badge auto-org-badge-green" }, "✓ PostgreSQL 16 + pgvector") :
              h("span", { className: "auto-org-badge auto-org-badge-yellow" }, "Verbinde..."),
            mountData && mountData.in_container &&
              h("span", { className: "auto-org-badge auto-org-badge-blue" }, "🐳 Docker Jail Aktiv")
          ),
          h("div", { className: "auto-org-subtitle" },
            "Geführter 4-Stufen-Workflow: Quelle & Ist-Stand → Organisationssystem & Baum-Freigabe → Filter-Regeln & Zuordnung → Simulation & Reorganisation."
          )
        ),
        // Top Toolbar Config Buttons
        h("div", { className: "auto-org-top-toolbar" },
          h("button", {
            className: `auto-org-config-btn ${activeModal === "mounts" ? "active" : ""}`,
            onClick: () => setActiveModal(activeModal === "mounts" ? null : "mounts"),
            title: "Docker-Mounts, Freispeicher & Pfad-Prüfer"
          },
            h("span", null, "🐳 Docker Mounts & Pfad-Prüfer"),
            h("span", { className: "auto-org-badge auto-org-badge-blue" }, mountData ? mountData.total_mounts : 0)
          ),
          h("button", {
            className: `auto-org-config-btn ${activeModal === "roots" ? "active" : ""}`,
            onClick: () => setActiveModal(activeModal === "roots" ? null : "roots"),
            title: "Überwachte Speicherwurzeln anzeigen"
          },
            h("span", null, "📁 Speicherwurzeln"),
            h("span", { className: "auto-org-badge auto-org-badge-blue" }, roots.length)
          ),
          h("button", {
            className: `auto-org-config-btn ${activeModal === "journal" ? "active" : ""}`,
            onClick: () => setActiveModal(activeModal === "journal" ? null : "journal"),
            title: "Ausführungs-Historie & 1-Klick Rollback"
          },
            h("span", null, "📜 Journal & Rollback"),
            h("span", { className: "auto-org-badge auto-org-badge-green" }, batches.length)
          ),
          h("button", {
            className: `auto-org-config-btn ${activeModal === "sync" ? "active" : ""}`,
            onClick: () => setActiveModal(activeModal === "sync" ? null : "sync"),
            title: "Google Drive ↔ Lokaler Speicher: Sync-Ordner & Mappings verwalten"
          },
            h("span", null, "☁️ GDrive-Sync"),
            h("span", { className: "auto-org-badge auto-org-badge-blue" }, syncMappings.length)
          ),
          h("button", {
            className: "auto-org-btn auto-org-btn-outline",
            onClick: loadData,
            disabled: loading,
            title: "Daten neu laden"
          }, loading ? "..." : "↻ Aktualisieren")
        )
      );
    };

    const renderStatsStrip = () => {
      if (!stats) return null;
      return h("div", { className: "auto-org-stat-grid" },
        h("div", { className: "auto-org-stat-card" },
          h("div", { className: "auto-org-stat-label" }, "Überwachte Ordner"),
          h("div", { className: "auto-org-stat-value" }, stats.total_roots)
        ),
        h("div", { className: "auto-org-stat-card" },
          h("div", { className: "auto-org-stat-label" }, "Indexierte Dateien"),
          h("div", { className: "auto-org-stat-value" }, stats.total_files.toLocaleString())
        ),
        h("div", { className: "auto-org-stat-card" },
          h("div", { className: "auto-org-stat-label" }, "Ziel-Baum Status"),
          h("div", { className: "auto-org-stat-value", style: { color: taxonomy && taxonomy.system_approved ? "#4ade80" : "#facc15", fontSize: "1.35rem" } },
            taxonomy && taxonomy.system_approved ? "✓ Freigegeben" : "⏳ Entwurf"
          )
        ),
        h("div", { className: "auto-org-stat-card" },
          h("div", { className: "auto-org-stat-label" }, "Unsortierte Anomalien"),
          h("div", { className: "auto-org-stat-value", style: { color: stats.open_anomalies > 0 ? "#f87171" : "#4ade80" } }, stats.open_anomalies)
        ),
        h("div", { className: "auto-org-stat-card" },
          h("div", { className: "auto-org-stat-label" }, "Aktive Filter-Regeln"),
          h("div", { className: "auto-org-stat-value", style: { color: "#60a5fa" } }, stats.active_rules)
        )
      );
    };

    const renderStepper = () => {
      return h("div", { className: "auto-org-stepper" },
        // Step 1
        h("div", {
          className: `auto-org-step-card ${step === 1 ? "active" : ""} ${step > 1 ? "completed" : ""}`,
          onClick: () => setStep(1)
        },
          h("div", { className: "auto-org-step-badge" }, step > 1 ? "✓" : "1"),
          h("div", { className: "auto-org-step-info" },
            h("div", { className: "auto-org-step-number-title" }, "Schritt 1"),
            h("div", { className: "auto-org-step-name" }, "Quelle & Ist-Stand"),
            h("div", { className: "auto-org-step-subtitle" },
              anomalies.length > 0 ? `${anomalies.length} offene Anomalien` : "Keine Anomalien"
            )
          )
        ),
        // Step 2 (Organisationssystem & Baum)
        h("div", {
          className: `auto-org-step-card ${step === 2 ? "active" : ""} ${step > 2 ? "completed" : ""}`,
          onClick: () => setStep(2)
        },
          h("div", { className: "auto-org-step-badge" }, step > 2 ? "✓" : "2"),
          h("div", { className: "auto-org-step-info" },
            h("div", { className: "auto-org-step-number-title" }, "Schritt 2"),
            h("div", { className: "auto-org-step-name" }, "Organisationssystem & Baum"),
            h("div", { className: "auto-org-step-subtitle" },
              taxonomy && taxonomy.system_approved ? "✓ Baum freigegeben" : "Analyse & Freigabe ausstehend"
            )
          )
        ),
        // Step 3 (Filter-Regeln)
        h("div", {
          className: `auto-org-step-card ${step === 3 ? "active" : ""} ${step > 3 ? "completed" : ""}`,
          onClick: () => setStep(3)
        },
          h("div", { className: "auto-org-step-badge" }, step > 3 ? "✓" : "3"),
          h("div", { className: "auto-org-step-info" },
            h("div", { className: "auto-org-step-number-title" }, "Schritt 3"),
            h("div", { className: "auto-org-step-name" }, "Filter-Regeln & Zuordnung"),
            h("div", { className: "auto-org-step-subtitle" },
              `${rules.length} aktive Regeln`
            )
          )
        ),
        // Step 4 (Simulation & Reorganisation)
        h("div", {
          className: `auto-org-step-card ${step === 4 ? "active" : ""}`,
          onClick: () => setStep(4)
        },
          h("div", { className: "auto-org-step-badge" }, "4"),
          h("div", { className: "auto-org-step-info" },
            h("div", { className: "auto-org-step-number-title" }, "Schritt 4"),
            h("div", { className: "auto-org-step-name" }, "Simulation & Reorganisation"),
            h("div", { className: "auto-org-step-subtitle" },
              dryRun ? `${dryRun.actions_count} Aktionen im Staging` : "Dry-Run & Ausführung"
            )
          )
        )
      );
    };

    // ==========================================
    // STEP 1: QUELLE & IST-ANALYSE
    // ==========================================
    const renderStep1 = () => {
      return h("div", { style: { display: "flex", flexDirection: "column", gap: "1.25rem" } },
        // Dumpzone Quick Sources Overview
        h("div", { className: "auto-org-panel" },
          h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" } },
            h("h3", { style: { fontSize: "1.125rem", fontWeight: 700, display: "flex", alignItems: "center", gap: "0.5rem" } },
              h("span", null, "📥"),
              h("span", null, "Häufige Quellbereiche & Dumpzones (Ist-Stand)")
            ),
            h("span", { style: { fontSize: "0.8125rem", color: "#94a3b8" } },
              "Schnellauswahl zur gezielten Analyse & Regel-Erstellung"
            )
          ),
          h("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "0.75rem" } },
            [
              { name: "Downloads", path: "/home/mb/Downloads", icon: "⬇️", desc: "Sammelort für Webinhalte & Rechnungen" },
              { name: "Schreibtisch", path: "/home/mb/Schreibtisch", icon: "🖥️", desc: "Temporäre Arbeitsdateien & Notizen" },
              { name: "PrivatBüro", path: "/media/privat-data/10_PrivatBüro", icon: "📁", desc: "Privatdokumente & Belege" },
              { name: "Work Data", path: "/media/work-data", icon: "💼", desc: "Projektunterlagen & Archive" },
            ].map((src, i) =>
              h("div", {
                key: i,
                style: {
                  background: "rgba(15, 23, 42, 0.75)",
                  border: "1px solid #334155",
                  borderRadius: "0.375rem",
                  padding: "0.85rem 1rem",
                  display: "flex",
                  flexDirection: "column",
                  gap: "0.4rem"
                }
              },
                h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center" } },
                  h("span", { style: { fontWeight: 600, color: "#ffffff" } }, `${src.icon} ${src.name}`),
                  h("button", {
                    type: "button",
                    className: "auto-org-pill-btn",
                    onClick: () => handleSetRuleSource(src.path)
                  }, "Als Quelle wählen →")
                ),
                h("div", { style: { fontFamily: "monospace", fontSize: "0.75rem", color: "#93c5fd" } }, src.path),
                h("div", { style: { fontSize: "0.75rem", color: "#94a3b8" } }, src.desc)
              )
            )
          )
        ),

        // Google Drive <-> Local Sync Mappings Section
        h("div", { className: "auto-org-panel" },
          h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem", flexWrap: "wrap", gap: "0.5rem" } },
            h("div", null,
              h("h3", { style: { fontSize: "1.125rem", fontWeight: 700, display: "flex", alignItems: "center", gap: "0.5rem", color: "#ffffff" } },
                h("span", null, "☁️"),
                h("span", null, `Google Drive ↔ Lokaler Speicher: Sync-Ordner & Mappings (${syncMappings.length})`)
              ),
              h("p", { style: { fontSize: "0.8125rem", color: "#94a3b8", marginTop: "0.2rem" } },
                "Selektive Synchronisation zwischen Google Drive und Ihren lokalen Festplatten/Container-Mounts."
              )
            ),
            h("div", { style: { display: "flex", gap: "0.5rem" } },
              h("button", {
                type: "button",
                className: "auto-org-btn auto-org-btn-outline",
                onClick: () => setActiveModal("sync"),
                style: { fontSize: "0.75rem" }
              }, "⚙️ Sync-Manager öffnen"),
              h("button", {
                type: "button",
                className: "auto-org-btn auto-org-btn-primary",
                onClick: () => {
                  setShowNewSyncForm(true);
                  setActiveModal("sync");
                },
                style: { fontSize: "0.75rem" }
              }, "+ Neuer Sync-Ordner")
            )
          ),
          syncMappings.length === 0 ?
            h("div", { style: { textAlign: "center", padding: "1.5rem", color: "#94a3b8" } },
              "Noch keine Google Drive ↔ Lokale Sync-Ordner konfiguriert. Klicken Sie oben auf '+ Neuer Sync-Ordner'."
            ) :
            h("div", { className: "auto-org-sync-grid" },
              syncMappings.map((m) => {
                const isBi = m.direction === "bidirectional";
                const isPush = m.direction === "push";
                const dirLabel = isBi ? "⇄ Bidirektional" : (isPush ? "⬆️ Lokal ➔ Drive" : "⬇️ Drive ➔ Lokal");
                const mountOk = m.mount_check && m.mount_check.valid && !m.mount_check.read_only;
                return h("div", {
                  key: m.id,
                  className: `auto-org-sync-card ${m.is_active ? "" : "paused"}`
                },
                  h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center" } },
                    h("span", { style: { fontWeight: 700, fontSize: "0.95rem", color: "#ffffff" } }, m.name),
                    h("span", { className: "auto-org-sync-direction-badge" }, dirLabel)
                  ),
                  h("div", { style: { display: "flex", flexDirection: "column", gap: "0.35rem", fontSize: "0.8125rem" } },
                    h("div", { style: { display: "flex", alignItems: "center", gap: "0.4rem" } },
                      h("span", { style: { color: "#94a3b8", width: "3.5rem" } }, "Drive:"),
                      h("span", { style: { fontFamily: "monospace", color: "#60a5fa", wordBreak: "break-all" } }, `gdrive:${m.drive_folder_path}`)
                    ),
                    h("div", { style: { display: "flex", alignItems: "center", gap: "0.4rem" } },
                      h("span", { style: { color: "#94a3b8", width: "3.5rem" } }, "Lokal:"),
                      h("span", { style: { fontFamily: "monospace", color: "#4ade80", wordBreak: "break-all" } }, m.local_path)
                    )
                  ),
                  h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid #334155", paddingTop: "0.5rem", marginTop: "0.25rem" } },
                    h("div", { className: "auto-org-mount-status-tag" },
                      mountOk ?
                        h("span", { className: "auto-org-mount-status-ok" }, "✅ Gemountet & Schreibbar") :
                        h("span", { className: "auto-org-mount-status-warn", title: (m.mount_check && m.mount_check.warning) || "Mount prüfen" }, "⚠️ Host-Pfad (Prüfen)")
                    ),
                    h("div", { style: { display: "flex", gap: "0.4rem" } },
                      h("button", {
                        type: "button",
                        className: "auto-org-pill-btn",
                        onClick: () => {
                          setActiveModal("sync");
                          handleCalculateSyncPlan(m.id);
                        }
                      }, "Plan / Diff →"),
                      h("button", {
                        type: "button",
                        className: "auto-org-pill-btn",
                        style: { color: m.is_active ? "#facc15" : "#4ade80" },
                        onClick: () => handleToggleSyncMapping(m.id, m.is_active)
                      }, m.is_active ? "Pausieren" : "Aktivieren")
                    )
                  )
                );
              })
            )
        ),

        // Anomalies Inbox
        h("div", { className: "auto-org-panel" },
          h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" } },
            h("div", null,
              h("h3", { style: { fontSize: "1.125rem", fontWeight: 700, display: "flex", alignItems: "center", gap: "0.5rem", color: "#ffffff" } },
                h("span", null, "🚨"),
                h("span", null, `Erkannte Anomalien & Unsortierte Dateien (${anomalies.length})`)
              ),
              h("p", { style: { fontSize: "0.8125rem", color: "#94a3b8", marginTop: "0.2rem" } },
                "Dateien in Dump-Zonen oder chaotischer Ordnerstruktur, die der KI-Index als reorganisationsbedürftig markiert hat."
              )
            ),
            anomalies.length > 0 && h("button", {
              className: "auto-org-btn auto-org-btn-outline",
              onClick: () => setStep(2)
            }, "Zu Schritt 2: Ziel-Baum prüfen →")
          ),

          anomalies.length === 0 ?
            h("div", { style: { textAlign: "center", padding: "2.5rem 1rem" } },
              h("div", { style: { fontSize: "2rem", marginBottom: "0.5rem" } }, "🎉"),
              h("p", { style: { color: "#4ade80", fontWeight: 600, fontSize: "1rem" } }, "Alle Speicherwurzeln sind sauber strukturiert!"),
              h("p", { style: { color: "#94a3b8", fontSize: "0.875rem", marginTop: "0.25rem" } }, "Keine offenen Dump-Zone-Dateien oder verwaisten Elemente gefunden.")
            ) :
            h("table", { className: "auto-org-table" },
              h("thead", null,
                h("tr", null,
                  h("th", null, "Dateiname"),
                  h("th", null, "Aktueller Speicherort"),
                  h("th", null, "Größe"),
                  h("th", null, "Anomalie-Typ"),
                  h("th", null, "KI-Empfehlung"),
                  h("th", null, "Aktion")
                )
              ),
              h("tbody", null,
                anomalies.map((an) => h("tr", { key: an.id },
                  h("td", { style: { fontWeight: 600 } }, an.file_name),
                  h("td", { style: { fontFamily: "monospace", fontSize: "0.75rem", color: "#94a3b8" } },
                    an.relative_path || an.physical_path
                  ),
                  h("td", null, `${an.size_kb} KB`),
                  h("td", null,
                    h("span", {
                      className: an.anomaly_type === "dump_zone" ? "auto-org-badge auto-org-badge-yellow" : "auto-org-badge auto-org-badge-blue"
                    }, an.anomaly_type)
                  ),
                  h("td", { style: { fontFamily: "monospace", fontSize: "0.75rem", color: "#4ade80" } },
                    an.suggested_target || "Archiv / General"
                  ),
                  h("td", null,
                    h("button", {
                      type: "button",
                      className: "auto-org-btn auto-org-btn-outline",
                      style: { fontSize: "0.75rem", padding: "0.25rem 0.5rem" },
                      onClick: () => handleCreateRuleFromAnomaly(an)
                    }, "⚡ Regel dafür erstellen →")
                  )
                ))
              )
            )
        ),

        // Step 1 Footer
        h("div", { className: "auto-org-step-footer" },
          h("div", { style: { fontSize: "0.85rem", color: "#94a3b8" } },
            "Ist-Stand erfasst? Definieren und prüfen Sie als Nächstes das Ziel-Organisationssystem (den Verzeichnis-Baum)."
          ),
          h("button", {
            className: "auto-org-btn auto-org-btn-primary",
            style: { padding: "0.6rem 1.5rem", fontSize: "0.875rem" },
            onClick: () => setStep(2)
          }, "Weiter zu Schritt 2: Organisationssystem & Baum freigeben →")
        )
      );
    };

    // ==========================================
    // STEP 2: ORGANISATIONSSYSTEM & BAUM-FREIGABE
    // ==========================================
    const renderStep2 = () => {
      const treeNodes = (taxonomy && taxonomy.tree) || [];
      const isSystemApproved = taxonomy && taxonomy.system_approved;
      const approvedCount = (taxonomy && taxonomy.approved_nodes) || 0;
      const totalNodes = treeNodes.length;

      return h("div", { style: { display: "flex", flexDirection: "column", gap: "1.25rem" } },
        // Status and Approval Banner
        h("div", {
          className: "auto-org-tree-banner",
          style: {
            borderLeft: `5px solid ${isSystemApproved ? "#4ade80" : "#facc15"}`,
            background: isSystemApproved ? "rgba(34, 197, 94, 0.08)" : "rgba(234, 179, 8, 0.08)"
          }
        },
          h("div", null,
            h("div", { style: { fontSize: "1.1rem", fontWeight: 700, display: "flex", alignItems: "center", gap: "0.5rem", color: isSystemApproved ? "#4ade80" : "#facc15" } },
              h("span", null, isSystemApproved ? "✓" : "⏳"),
              h("span", null, isSystemApproved ? "Ziel-Organisationssystem vollständig freigegeben" : "Analyse & Freigabe des Organisationssystems erforderlich")
            ),
            h("p", { style: { fontSize: "0.8125rem", color: "#94a3b8", marginTop: "0.25rem" } },
              `Das Organisationssystem definiert die verbindliche Zielstruktur (S_ideal). Aktuell sind ${approvedCount} von ${totalNodes} Ordner-Ästen vom Benutzer freigegeben.`
            )
          ),
          h("div", { style: { display: "flex", gap: "0.5rem", flexWrap: "wrap" } },
            h("button", {
              type: "button",
              className: "auto-org-btn auto-org-btn-outline",
              onClick: () => setShowNewNodeForm(!showNewNodeForm)
            }, showNewNodeForm ? "Abbrechen" : "+ Neuer Ordner-Ast"),
            h("button", {
              type: "button",
              className: "auto-org-btn auto-org-btn-primary",
              style: { fontWeight: 700 },
              onClick: handleApproveAllTaxonomy,
              disabled: loading
            }, "🌳 Gesamten Baum jetzt freigeben")
          )
        ),

        // Optional Form to Add a Custom Taxonomy Branch
        showNewNodeForm && h("div", { className: "auto-org-panel", style: { border: "1px solid #3b82f6" } },
          h("h4", { style: { fontSize: "1rem", fontWeight: 700, marginBottom: "0.75rem" } }, "➕ Neuen Ordner-Ast im Organisationsbaum anlegen"),
          h("form", { onSubmit: handleAddTaxonomyNode, style: { display: "flex", flexDirection: "column", gap: "0.75rem" } },
            h("div", { style: { display: "grid", gridTemplateColumns: "100px 1fr 1fr", gap: "0.75rem" } },
              h("div", null,
                h("label", { style: { fontSize: "0.75rem", color: "#94a3b8", display: "block" } }, "Icon"),
                h("input", {
                  className: "auto-org-input",
                  style: { width: "100%", textAlign: "center", fontSize: "1.1rem" },
                  value: newNodeIcon,
                  onChange: (e) => setNewNodeIcon(e.target.value)
                })
              ),
              h("div", null,
                h("label", { style: { fontSize: "0.75rem", color: "#94a3b8", display: "block" } }, "Kategorie / Ast-Name"),
                h("input", {
                  className: "auto-org-input",
                  style: { width: "100%" },
                  placeholder: "z.B. 40_Personal & Verträge",
                  value: newNodeName,
                  onChange: (e) => setNewNodeName(e.target.value)
                })
              ),
              h("div", null,
                h("label", { style: { fontSize: "0.75rem", color: "#94a3b8", display: "block" } }, "Zielordner-Vorlage"),
                h("input", {
                  className: "auto-org-input",
                  style: { width: "100%", fontFamily: "monospace" },
                  placeholder: "/media/privat-data/10_PrivatBüro/Personal/{year}/",
                  value: newNodePath,
                  onChange: (e) => setNewNodePath(e.target.value)
                })
              )
            ),
            h("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" } },
              h("div", null,
                h("label", { style: { fontSize: "0.75rem", color: "#94a3b8", display: "block" } }, "Beschreibung / Zweck"),
                h("input", {
                  className: "auto-org-input",
                  style: { width: "100%" },
                  placeholder: "Gehaltsabrechnungen, Arbeitsverträge...",
                  value: newNodeDesc,
                  onChange: (e) => setNewNodeDesc(e.target.value)
                })
              ),
              h("div", null,
                h("label", { style: { fontSize: "0.75rem", color: "#94a3b8", display: "block" } }, "Schlagworte (Kommagetrennt)"),
                h("input", {
                  className: "auto-org-input",
                  style: { width: "100%" },
                  placeholder: "Gehalt, Lohn, Abrechnung, Vertrag",
                  value: newNodeKeywords,
                  onChange: (e) => setNewNodeKeywords(e.target.value)
                })
              )
            ),
            h("div", { style: { display: "flex", justifyContent: "flex-end", gap: "0.5rem", marginTop: "0.25rem" } },
              h("button", { type: "button", className: "auto-org-btn auto-org-btn-outline", onClick: () => setShowNewNodeForm(false) }, "Abbrechen"),
              h("button", { type: "submit", className: "auto-org-btn auto-org-btn-primary" }, "Ast speichern & in Baum aufnehmen")
            )
          )
        ),

        // Tree Nodes View
        h("div", { className: "auto-org-tree-container" },
          treeNodes.map((node) => {
            const isApproved = node.is_approved;
            const isExpanded = !!expandedSamples[node.id];

            return h("div", {
              key: node.id,
              className: `auto-org-tree-node ${isApproved ? "approved" : "draft"}`
            },
              // Header Row
              h("div", { className: "auto-org-tree-node-header" },
                h("div", { className: "auto-org-tree-node-title" },
                  h("span", { className: "auto-org-tree-node-icon" }, node.icon || "📁"),
                  h("span", null, node.name),
                  h("span", { className: `auto-org-badge ${isApproved ? "auto-org-badge-green" : "auto-org-badge-yellow"}` },
                    isApproved ? "✓ Freigegeben" : "⏳ Vorschlag / Entwurf"
                  ),
                  node.mount_valid ?
                    h("span", { className: "auto-org-badge auto-org-badge-green" }, "✓ In Docker RW") :
                    h("span", { className: "auto-org-badge auto-org-badge-red" }, "⚠️ Unmounted")
                ),
                h("div", { style: { display: "flex", gap: "0.4rem", alignItems: "center" } },
                  h("button", {
                    type: "button",
                    className: isApproved ? "auto-org-btn auto-org-btn-outline" : "auto-org-btn auto-org-btn-primary",
                    style: { fontSize: "0.75rem", padding: "0.3rem 0.65rem" },
                    onClick: () => handleToggleNodeApproval(node.id, isApproved)
                  }, isApproved ? "Pausieren" : "✓ Ast freigeben"),
                  h("button", {
                    type: "button",
                    className: "auto-org-btn auto-org-btn-outline",
                    style: { fontSize: "0.75rem", padding: "0.3rem 0.65rem", color: "#60a5fa" },
                    onClick: () => handleApplyTaxonomyBranchToRule(node)
                  }, "⚡ In Baukasten übernehmen →")
                )
              ),

              // Path & Details Row
              h("div", { className: "auto-org-tree-details" },
                h("div", { style: { display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" } },
                  h("span", { style: { color: "#94a3b8" } }, "Ziel-Pfad:"),
                  h("span", { className: "auto-org-tree-path-badge" }, node.target_path_template),
                  node.description && h("span", { style: { color: "#94a3b8" } }, `• ${node.description}`)
                ),
                h("div", { style: { display: "flex", alignItems: "center", gap: "0.5rem" } },
                  h("span", { style: { fontWeight: 600, color: "#f8fafc" } },
                    `${node.matched_files_count || 0} passende Dateien im Index`
                  ),
                  node.sample_files && node.sample_files.length > 0 && h("button", {
                    type: "button",
                    className: "auto-org-tag-btn",
                    onClick: () => toggleSampleExpand(node.id)
                  }, isExpanded ? "Beispiele ausblenden ▲" : "Beispiele anzeigen ▼")
                )
              ),

              // Keywords & Extensions Pills
              h("div", { style: { display: "flex", alignItems: "center", gap: "0.4rem", flexWrap: "wrap" } },
                h("span", { style: { fontSize: "0.75rem", color: "#94a3b8" } }, "Erkennungs-Kriterien:"),
                (node.keywords || []).map((kw, i) =>
                  h("span", { key: i, className: "auto-org-cond-badge" }, `🔍 ${kw}`)
                ),
                (node.extensions || []).map((ext, i) =>
                  h("span", { key: i, className: "auto-org-cond-badge" }, `📄 .${ext}`)
                )
              ),

              // Expanded Samples Table
              isExpanded && node.sample_files && h("div", {
                style: {
                  background: "rgba(15, 23, 42, 0.7)",
                  border: "1px solid #334155",
                  borderRadius: "0.375rem",
                  padding: "0.6rem 0.85rem",
                  marginTop: "0.25rem"
                }
              },
                h("div", { style: { fontSize: "0.75rem", fontWeight: 600, color: "#60a5fa", marginBottom: "0.4rem" } },
                  "Zugeordnete Beispieldateien für diesen Ast:"
                ),
                h("ul", { style: { margin: 0, paddingLeft: "1.2rem", fontSize: "0.75rem", color: "#f8fafc" } },
                  node.sample_files.map((s, idx) =>
                    h("li", { key: idx, style: { marginBottom: "0.2rem" } },
                      h("strong", null, s.file_name),
                      h("span", { style: { color: "#94a3b8", marginLeft: "0.4rem", fontFamily: "monospace" } }, `(${s.relative_path})`)
                    )
                  )
                )
              )
            );
          })
        ),

        // Step 2 Footer Navigation
        h("div", { className: "auto-org-step-footer" },
          h("button", {
            className: "auto-org-btn auto-org-btn-outline",
            onClick: () => setStep(1)
          }, "← Zurück zu Schritt 1: Quelle & Ist-Stand"),
          h("button", {
            className: "auto-org-btn auto-org-btn-primary",
            style: { padding: "0.6rem 1.5rem", fontSize: "0.875rem" },
            onClick: () => setStep(3)
          }, "Weiter zu Schritt 3: Filter-Regeln & Zuordnung →")
        )
      );
    };

    // ==========================================
    // STEP 3: FILTER-REGELN & ZUORDNUNG
    // ==========================================
    const renderRuleConditionBadges = (r) => {
      const cond = r.condition_json || {};
      const items = cond.conditions || [];
      const mode = (cond.match_mode || "all").toUpperCase();

      if (items.length === 0) {
        return h("span", { className: "auto-org-cond-badge" }, r.source_pattern || "*");
      }

      return h("div", { style: { display: "flex", flexWrap: "wrap", alignItems: "center" } },
        h("span", {
          style: {
            fontSize: "0.7rem",
            fontWeight: 700,
            color: mode === "ALL" ? "#60a5fa" : "#facc15",
            marginRight: "0.5rem"
          }
        }, mode === "ALL" ? "[UND]" : "[ODER]"),
        items.map((item, idx) => {
          let label = "";
          if (item.field === "source_folder") label = `📂 ${item.value}`;
          else if (item.field === "timeframe") label = `⏱️ >${item.value} Tage`;
          else if (item.field === "keyword") label = `🔍 '${item.value}'`;
          else if (item.field === "extension") label = `📄 .${item.value}`;
          else if (item.field === "file_size") label = `⚖️ >${item.value} MB`;
          else label = `${item.field}: ${item.value}`;

          return h("span", { key: idx, className: "auto-org-cond-badge" }, label);
        })
      );
    };

    const renderModularRuleBuilder = () => {
      return h("div", { className: "auto-org-builder-card" },
        h("div", { style: { borderBottom: "1px solid #334155", paddingBottom: "0.75rem" } },
          h("h3", { style: { fontSize: "1.125rem", fontWeight: 700, display: "flex", alignItems: "center", gap: "0.5rem" } },
            h("span", null, "⚡"),
            h("span", null, "Modularer Datei-Regel-Baukasten (Zuordnung in den Baum)")
          ),
          h("p", { style: { fontSize: "0.8125rem", color: "#94a3b8", marginTop: "0.25rem" } },
            "Definiere mehrstufige Sortierkriterien nach Quellordner, Alter, Schlagwörtern (Dateiname & OCR-Text) und Dateityp."
          )
        ),

        // Rule Name & Description
        h("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" } },
          h("div", null,
            h("label", { style: { fontSize: "0.75rem", color: "#94a3b8", display: "block", marginBottom: "0.25rem" } }, "Regel-Name"),
            h("input", {
              className: "auto-org-input",
              style: { width: "100%" },
              placeholder: "z.B. Rechnungen automatisch archivieren",
              value: ruleName,
              onChange: (e) => setRuleName(e.target.value)
            })
          ),
          h("div", null,
            h("label", { style: { fontSize: "0.75rem", color: "#94a3b8", display: "block", marginBottom: "0.25rem" } }, "Beschreibung / Notiz"),
            h("input", {
              className: "auto-org-input",
              style: { width: "100%" },
              placeholder: "z.B. Verschiebt PDFs mit 'Rechnung' älter als 14 Tage",
              value: ruleDesc,
              onChange: (e) => setRuleDesc(e.target.value)
            })
          )
        ),

        // Match Mode (AND / OR)
        h("div", { style: { display: "flex", alignItems: "center", gap: "1.5rem", background: "rgba(15, 23, 42, 0.4)", padding: "0.6rem 1rem", borderRadius: "0.375rem" } },
          h("span", { style: { fontSize: "0.8125rem", fontWeight: 600 } }, "Bedingungs-Verknüpfung:"),
          h("label", { style: { fontSize: "0.8125rem", display: "flex", alignItems: "center", gap: "0.35rem", cursor: "pointer" } },
            h("input", {
              type: "radio",
              name: "match_mode",
              checked: matchMode === "all",
              onChange: () => setMatchMode("all")
            }),
            h("span", null, "Erfülle ", h("strong", { style: { color: "#60a5fa" } }, "ALLE"), " Bedingungen (UND)")
          ),
          h("label", { style: { fontSize: "0.8125rem", display: "flex", alignItems: "center", gap: "0.35rem", cursor: "pointer" } },
            h("input", {
              type: "radio",
              name: "match_mode",
              checked: matchMode === "any",
              onChange: () => setMatchMode("any")
            }),
            h("span", null, "Erfülle ", h("strong", { style: { color: "#facc15" } }, "MINDESTENS EINE"), " Bedingung (ODER)")
          )
        ),

        // Conditions list
        h("div", { style: { display: "flex", flexDirection: "column", gap: "0.5rem" } },
          h("span", { style: { fontSize: "0.75rem", fontWeight: 600, color: "#94a3b8" } }, "WENN folgende Kriterien zutreffen:"),
          conditions.map((cond, idx) => {
            return h("div", { key: idx, className: "auto-org-condition-row" },
              // Field selector (Explicit high-contrast styling)
              h("select", {
                className: "auto-org-select",
                value: cond.field,
                onChange: (e) => handleConditionChange(idx, "field", e.target.value)
              },
                h("option", { value: "source_folder" }, "📂 Quellordner (Source Folder)"),
                h("option", { value: "timeframe" }, "⏱️ Zeitraum / Alter (Timeframe)"),
                h("option", { value: "keyword" }, "🔍 Schlagwort / Volltext (Keyword)"),
                h("option", { value: "extension" }, "📄 Dateityp / Endung (Extension)"),
                h("option", { value: "file_size" }, "⚖️ Dateigröße (Size)")
              ),

              // Operator selector
              cond.field === "source_folder" && h("select", {
                className: "auto-org-select",
                value: cond.operator,
                onChange: (e) => handleConditionChange(idx, "operator", e.target.value)
              },
                h("option", { value: "starts_with" }, "beginnt mit Pfad"),
                h("option", { value: "equals" }, "ist exakt Ordner"),
                h("option", { value: "contains" }, "enthält im Pfad")
              ),

              cond.field === "timeframe" && h("select", {
                className: "auto-org-select",
                value: cond.operator,
                onChange: (e) => handleConditionChange(idx, "operator", e.target.value)
              },
                h("option", { value: "older_than_days" }, "älter als (Tage)"),
                h("option", { value: "newer_than_days" }, "neuer als (Tage)")
              ),

              cond.field === "keyword" && h("select", {
                className: "auto-org-select",
                value: cond.operator,
                onChange: (e) => handleConditionChange(idx, "operator", e.target.value)
              },
                h("option", { value: "contains" }, "enthält Text")
              ),

              cond.field === "keyword" && h("select", {
                className: "auto-org-select",
                value: cond.scope || "both",
                onChange: (e) => handleConditionChange(idx, "scope", e.target.value)
              },
                h("option", { value: "both" }, "in Dateiname & OCR-Text"),
                h("option", { value: "filename" }, "nur in Dateiname"),
                h("option", { value: "content" }, "nur in OCR-Text")
              ),

              cond.field === "extension" && h("select", {
                className: "auto-org-select",
                value: cond.operator,
                onChange: (e) => handleConditionChange(idx, "operator", e.target.value)
              },
                h("option", { value: "is_one_of" }, "ist eine von"),
                h("option", { value: "is_not_one_of" }, "ist keine von")
              ),

              cond.field === "file_size" && h("select", {
                className: "auto-org-select",
                value: cond.operator,
                onChange: (e) => handleConditionChange(idx, "operator", e.target.value)
              },
                h("option", { value: "greater_than_mb" }, "größer als (MB)"),
                h("option", { value: "less_than_mb" }, "kleiner als (MB)")
              ),

              // Value Input
              h("input", {
                className: "auto-org-input",
                style: { flex: 1, minWidth: "160px" },
                placeholder: cond.field === "source_folder" ? "/home/mb/Downloads" :
                             cond.field === "timeframe" ? "30" :
                             cond.field === "keyword" ? "Rechnung" :
                             cond.field === "extension" ? "pdf, docx" : "50",
                value: cond.value,
                onChange: (e) => handleConditionChange(idx, "value", e.target.value)
              }),

              // Quick preset pills for source_folder
              cond.field === "source_folder" && h("div", { style: { display: "flex", gap: "0.25rem", flexWrap: "wrap", alignItems: "center" } },
                mountData && mountData.mounts ?
                  mountData.mounts.filter(m => m.category === "Dumpzone" || m.category === "Storage Root" || m.category === "Host Work").slice(0, 5).map(m =>
                    h("button", {
                      key: m.host_path,
                      type: "button",
                      className: "auto-org-tag-btn",
                      onClick: () => handleConditionChange(idx, "value", m.host_path)
                    }, m.label.split(" ")[0])
                  ) :
                  [
                    h("button", { key: "dl", type: "button", className: "auto-org-tag-btn", onClick: () => handleConditionChange(idx, "value", "/home/mb/Downloads") }, "Downloads"),
                    h("button", { key: "desk", type: "button", className: "auto-org-tag-btn", onClick: () => handleConditionChange(idx, "value", "/home/mb/Schreibtisch") }, "Desktop")
                  ]
              ),

              // Remove condition button
              h("button", {
                type: "button",
                className: "auto-org-btn auto-org-btn-outline",
                style: { padding: "0.3rem 0.6rem", color: "#f87171" },
                disabled: conditions.length <= 1,
                onClick: () => handleRemoveCondition(idx)
              }, "✕")
            );
          }),

          h("div", { style: { marginTop: "0.25rem" } },
            h("button", {
              type: "button",
              className: "auto-org-btn auto-org-btn-outline",
              onClick: handleAddCondition
            }, "+ Weitere Bedingung hinzufügen")
          )
        ),

        // Action Section (Target Folder & Safety Check)
        h("div", { style: { background: "rgba(15, 23, 42, 0.4)", padding: "1rem", borderRadius: "0.375rem", border: "1px solid #334155" } },
          h("div", { style: { display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" } },
            h("span", { style: { fontSize: "0.875rem", fontWeight: 700 } }, "DANN führe folgende Aktion aus:"),
            h("span", { className: "auto-org-badge auto-org-badge-green" }, "Verschieben nach Ziel-Ast (Move)")
          ),
          h("div", { style: { display: "flex", flexDirection: "column", gap: "0.5rem" } },
            h("label", { style: { fontSize: "0.75rem", color: "#94a3b8" } },
              "Zielordner / Pfad-Vorlage (wird auf Docker-Container RW-Mount geprüft):"
            ),
            h("input", {
              className: "auto-org-input",
              style: { width: "100%", fontFamily: "monospace" },
              value: targetTemplate,
              onChange: (e) => setTargetTemplate(e.target.value)
            }),
            // Live Container Mount Safety Check Indicator
            (() => {
              const matchedMount = mountData && mountData.mounts ?
                mountData.mounts.find(m => targetTemplate.startsWith(m.host_path) || targetTemplate.startsWith(m.container_path)) : null;
              if (matchedMount) {
                return h("div", { style: { display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.75rem", color: "#4ade80", background: "rgba(34, 197, 94, 0.1)", padding: "0.35rem 0.6rem", borderRadius: "0.25rem" } },
                  h("span", null, `✓ In Docker gemountet: ${matchedMount.label} → ${matchedMount.container_path}`),
                  h("span", { style: { color: "#94a3b8" } }, `(${matchedMount.free_gb} GB frei • RW)`)
                );
              } else if (targetTemplate.trim().length > 3) {
                return h("div", { style: { display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.75rem", color: "#f87171", background: "rgba(239, 68, 68, 0.1)", padding: "0.35rem 0.6rem", borderRadius: "0.25rem" } },
                  h("span", null, "⚠️ Warnung: Zielordner liegt außerhalb der Docker-Mounts! Hermes läuft im isolierten Container und kann hierhin nicht schreiben.")
                );
              }
              return null;
            })(),

            // Quick Select Pills from APPROVED TAXONOMY TREE
            h("div", { style: { display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap", marginTop: "0.25rem" } },
              h("span", { style: { fontSize: "0.75rem", color: "#94a3b8" } }, "Aus Organisationssystem (Schritt 2):"),
              taxonomy && taxonomy.tree ?
                taxonomy.tree.map(n =>
                  h("button", {
                    key: n.id,
                    type: "button",
                    className: "auto-org-tag-btn",
                    style: { borderStyle: n.is_approved ? "solid" : "dashed" },
                    onClick: () => setTargetTemplate(n.target_path_template)
                  }, `${n.icon || "📁"} ${n.name.split("/")[1] || n.name}`)
                ) :
                [
                  h("button", { key: "pb", type: "button", className: "auto-org-tag-btn", onClick: () => setTargetTemplate("/media/privat-data/10_PrivatBüro/Steuern/{year}/") }, "PrivatBüro"),
                  h("button", { key: "wd", type: "button", className: "auto-org-tag-btn", onClick: () => setTargetTemplate("/media/work-data/Archiv/{year}/") }, "Work-Data")
                ]
            ),

            // Placeholders
            h("div", { style: { display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap", marginTop: "0.25rem" } },
              h("span", { style: { fontSize: "0.75rem", color: "#94a3b8" } }, "Platzhalter einfügen:"),
              h("button", { type: "button", className: "auto-org-tag-btn", onClick: () => appendPlaceholder("{year}") }, "+ {year}"),
              h("button", { type: "button", className: "auto-org-tag-btn", onClick: () => appendPlaceholder("{month}") }, "+ {month}"),
              h("button", { type: "button", className: "auto-org-tag-btn", onClick: () => appendPlaceholder("{stem}") }, "+ {stem}"),
              h("button", { type: "button", className: "auto-org-tag-btn", onClick: () => appendPlaceholder("{ext}") }, "+ {ext}")
            )
          )
        ),

        // Action Buttons (Test Simulation + Save)
        h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "0.5rem" } },
          h("button", {
            type: "button",
            className: "auto-org-btn auto-org-btn-outline",
            style: { padding: "0.55rem 1.25rem", display: "flex", gap: "0.5rem" },
            onClick: handleTestRule,
            disabled: testing
          }, testing ? "Simuliere..." : "🔍 Regel an vorhandenen Dateien testen"),
          h("button", {
            type: "button",
            className: "auto-org-btn auto-org-btn-primary",
            style: { padding: "0.55rem 1.5rem", fontWeight: 700 },
            onClick: handleSaveModularRule,
            disabled: loading
          }, "💾 Regel speichern & aktivieren")
        ),

        // Live Test Simulation Results
        testResult && h("div", {
          style: {
            background: "rgba(15, 23, 42, 0.9)",
            border: "1px solid rgba(59, 130, 246, 0.4)",
            borderRadius: "0.375rem",
            padding: "1rem",
            marginTop: "0.5rem"
          }
        },
          h("div", { style: { display: "flex", justifyContent: "space-between", marginBottom: "0.5rem" } },
            h("span", { style: { fontWeight: 600, color: "#60a5fa" } },
              `Simulations-Ergebnis: ${testResult.matches_count} Dateien stimmen mit dieser Regel überein`
            ),
            h("button", {
              className: "auto-org-tag-btn",
              onClick: () => setTestResult(null)
            }, "Ausblenden")
          ),
          testResult.sample_matches && testResult.sample_matches.length > 0 ?
          h("table", { className: "auto-org-table" },
            h("thead", null,
              h("tr", null,
                h("th", null, "Dateiname"),
                h("th", null, "Aktueller Pfad"),
                h("th", null, "Geplantes Ziel"),
                h("th", null, "Größe")
              )
            ),
            h("tbody", null,
              testResult.sample_matches.map((m, i) => h("tr", { key: i },
                h("td", { style: { fontWeight: 600 } }, m.file_name),
                h("td", { style: { fontFamily: "monospace", fontSize: "0.75rem", color: "#f87171" } }, m.source_path),
                h("td", { style: { fontFamily: "monospace", fontSize: "0.75rem", color: "#4ade80" } }, m.destination_path),
                h("td", null, `${m.size_kb} KB`)
              ))
            )
          ) :
          h("p", { style: { color: "#94a3b8", fontSize: "0.8125rem" } }, "Keine indexierten Dateien gefunden, die derzeit auf diese Bedingungen zutreffen.")
        )
      );
    };

    const renderStep3 = () => {
      return h("div", { style: { display: "flex", flexDirection: "column", gap: "1.25rem" } },
        // 1. Modular Rule Builder
        renderModularRuleBuilder(),

        // 2. Existing Rules Matrix
        h("div", { className: "auto-org-panel" },
          h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" } },
            h("h3", { style: { fontSize: "1.125rem", fontWeight: 700 } },
              `Gespeicherte Regel-Matrix (${rules.length} definierte Regeln)`
            ),
            h("span", { style: { fontSize: "0.8125rem", color: "#94a3b8" } },
              "Regeln werden nach Priorität sortiert ausgeführt"
            )
          ),
          h("table", { className: "auto-org-table" },
            h("thead", null,
              h("tr", null,
                h("th", null, "Regelname"),
                h("th", null, "Modulare Kriterien (WENN)"),
                h("th", null, "Ziel-Ast im Baum (DANN)"),
                h("th", null, "Status"),
                h("th", null, "Aktionen")
              )
            ),
            h("tbody", null,
              rules.length === 0 ?
              h("tr", null, h("td", { colSpan: 5, style: { textAlign: "center", color: "#94a3b8" } }, "Noch keine Regeln eingerichtet. Nutzen Sie den Baukasten oben!")) :
              rules.map((r) => {
                const isApproved = r.state === "USER_APPROVED";
                return h("tr", { key: r.id },
                  h("td", { style: { fontWeight: 600 } },
                    h("div", null, r.name),
                    r.description && h("div", { style: { fontSize: "0.75rem", color: "#94a3b8" } }, r.description)
                  ),
                  h("td", null, renderRuleConditionBadges(r)),
                  h("td", { style: { fontFamily: "monospace", fontSize: "0.8125rem", color: "#4ade80" } }, r.target_template),
                  h("td", null,
                    h("span", {
                      className: isApproved ? "auto-org-badge auto-org-badge-green" : "auto-org-badge auto-org-badge-yellow"
                    }, isApproved ? "Aktiv" : "Pausiert")
                  ),
                  h("td", null,
                    h("div", { style: { display: "flex", gap: "0.5rem" } },
                      h("button", {
                        className: isApproved ? "auto-org-btn auto-org-btn-outline" : "auto-org-btn auto-org-btn-primary",
                        onClick: () => handleToggleRule(r.id, isApproved)
                      }, isApproved ? "Pausieren" : "Aktivieren"),
                      h("button", {
                        className: "auto-org-btn auto-org-btn-danger",
                        onClick: () => handleDeleteRule(r.id, r.name)
                      }, "Löschen")
                    )
                  )
                );
              })
            )
          )
        ),

        // Step 3 Footer Navigation
        h("div", { className: "auto-org-step-footer" },
          h("button", {
            className: "auto-org-btn auto-org-btn-outline",
            onClick: () => setStep(2)
          }, "← Zurück zu Schritt 2: Organisationssystem & Baum"),
          h("button", {
            className: "auto-org-btn auto-org-btn-primary",
            style: { padding: "0.6rem 1.5rem", fontSize: "0.875rem" },
            onClick: () => {
              handleRunDryRun();
              setStep(4);
            }
          }, "Weiter zu Schritt 4: Simulation & Reorganisation starten →")
        )
      );
    };

    // ==========================================
    // STEP 4: SIMULATION & REORGANISATION
    // ==========================================
    const renderStep4 = () => {
      return h("div", { style: { display: "flex", flexDirection: "column", gap: "1.25rem" } },
        // Dry-Run Simulation Card
        h("div", { className: "auto-org-panel" },
          h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "1rem" } },
            h("div", null,
              h("h3", { style: { fontWeight: 700, fontSize: "1.125rem" } },
                dryRun ? `⚡ Dry-Run Staging: ${dryRun.actions_count} geplante Datei-Verschiebungen` : "⚡ Reorganisations-Simulation"
              ),
              h("p", { style: { fontSize: "0.8125rem", color: "#94a3b8", marginTop: "0.2rem" } },
                dryRun ?
                  `Batch: ${dryRun.batch_id.slice(0, 12)} • Sicher zur Ausführung: ${dryRun.safe_count} • Kollisionen/Gesperrt: ${dryRun.collisions_count}` :
                  "Simulieren Sie die Reorganisation vor der Ausführung. Hermes prüft Schreibrechte, Docker-Mounts und Dateinamen-Kollisionen."
              )
            ),
            h("div", { style: { display: "flex", gap: "0.5rem" } },
              h("button", {
                className: "auto-org-btn auto-org-btn-outline",
                onClick: handleRunDryRun,
                disabled: loading
              }, loading ? "Simuliere..." : "🔄 Simulation neu starten"),
              dryRun && dryRun.safe_count > 0 && h("button", {
                className: "auto-org-btn auto-org-btn-primary",
                style: { padding: "0.6rem 1.5rem", fontWeight: 700 },
                onClick: handleExecuteDryRun,
                disabled: loading
              }, `⚡ Freigegebene Aktionen ausführen (${dryRun.safe_count})`)
            )
          ),

          !dryRun ?
            h("div", { style: { textAlign: "center", padding: "3rem 1rem" } },
              h("div", { style: { fontSize: "2.5rem", marginBottom: "0.75rem" } }, "🔍"),
              h("h4", { style: { fontWeight: 600, marginBottom: "0.5rem" } }, "Bereit für die Dry-Run Simulation"),
              h("p", { style: { color: "#94a3b8", fontSize: "0.875rem", marginBottom: "1.5rem", maxWidth: "500px", margin: "0 auto 1.5rem auto" } },
                "Die Simulation gleicht alle aktiven Filter-Regeln gegen den aktuellen Dateibestand ab und stellt geplante Verschiebungen zusammen."
              ),
              h("button", {
                className: "auto-org-btn auto-org-btn-primary",
                style: { padding: "0.6rem 2rem", fontSize: "0.95rem" },
                onClick: handleRunDryRun
              }, "Jetzt Dry-Run starten")
            ) :
            h("table", { className: "auto-org-table" },
              h("thead", null,
                h("tr", null,
                  h("th", null, "Datei"),
                  h("th", null, "Aktueller Pfad (S_now)"),
                  h("th", null, ""),
                  h("th", null, "Neues Ziel im Baum (S_ideal)"),
                  h("th", null, "Regel"),
                  h("th", null, "Docker Mount"),
                  h("th", null, "Sicherheits-Check")
                )
              ),
              h("tbody", null,
                dryRun.actions.length === 0 ?
                h("tr", null, h("td", { colSpan: 7, style: { textAlign: "center", color: "#94a3b8", padding: "2rem" } }, "Keine Verschiebungs-Aktionen für die aktuellen Regeln gefunden.")) :
                dryRun.actions.map((act, idx) => h("tr", { key: idx },
                  h("td", { style: { fontWeight: 600 } }, act.file_name),
                  h("td", null, h("span", { className: "auto-org-diff-source" }, act.source_path)),
                  h("td", null, h("span", { className: "auto-org-diff-arrow" }, "→")),
                  h("td", null, h("span", { className: "auto-org-diff-target" }, act.destination_path)),
                  h("td", null, h("span", { className: "auto-org-badge auto-org-badge-blue" }, act.rule_name || act.operation)),
                  h("td", null,
                    act.mount_valid !== false ?
                    h("span", { className: "auto-org-badge auto-org-badge-green" }, "✓ Mount RW") :
                    h("span", { className: "auto-org-badge auto-org-badge-red" }, "⚠️ Unmounted")
                  ),
                  h("td", null,
                    act.safe_to_execute ?
                    h("span", { className: "auto-org-badge auto-org-badge-green" }, "Bereit zur Ausführung") :
                    h("span", { className: "auto-org-badge auto-org-badge-red" }, act.mount_warning || (act.collision ? "Kollision erkannt" : "Gesperrt"))
                  )
                ))
              )
            )
        ),

        // Step 4 Footer Navigation
        h("div", { className: "auto-org-step-footer" },
          h("button", {
            className: "auto-org-btn auto-org-btn-outline",
            onClick: () => setStep(3)
          }, "← Zurück zu Schritt 3: Filter-Regeln anpassen"),
          h("div", { style: { display: "flex", gap: "0.5rem" } },
            h("button", {
              className: "auto-org-btn auto-org-btn-outline",
              onClick: () => setActiveModal("journal")
            }, "📜 Reorganisations-Journal & Rollback öffnen"),
            dryRun && dryRun.safe_count > 0 && h("button", {
              className: "auto-org-btn auto-org-btn-primary",
              onClick: handleExecuteDryRun,
              disabled: loading
            }, `⚡ Reorganisation ausführen (${dryRun.safe_count})`)
          )
        )
      );
    };

    // ==========================================
    // CONFIG MODALS: MOUNTS, ROOTS, JOURNAL
    // ==========================================
    const renderConfigModal = () => {
      if (!activeModal) return null;

      let title = "";
      let content = null;

      if (activeModal === "mounts") {
        title = "🐳 Docker Mounts, Freispeicher & Pfad-Prüfer";
        const mounts = (mountData && mountData.mounts) || [];
        content = h(React.Fragment, null,
          // Isolation Status Grid
          h("div", { className: "auto-org-stat-grid" },
            h("div", { className: "auto-org-stat-card" },
              h("div", { className: "auto-org-stat-label" }, "🐳 Container-Isolation"),
              h("div", { className: "auto-org-stat-value", style: { fontSize: "1.25rem", color: "#60a5fa" } },
                mountData && mountData.in_container ? "Docker Jail Aktiv" : "Host-Umgebung"
              ),
              h("div", { style: { fontSize: "0.75rem", color: "#94a3b8" } },
                "Dateizugriff auf gemountete Pfade unter /opt/data/... beschränkt"
              )
            ),
            h("div", { className: "auto-org-stat-card" },
              h("div", { className: "auto-org-stat-label" }, "Gemountete Bereiche"),
              h("div", { className: "auto-org-stat-value" }, `${mountData ? mountData.total_mounts : 0}`),
              h("div", { style: { fontSize: "0.75rem", color: "#4ade80" } },
                `${mountData ? mountData.writable_mounts : 0} beschreibbar (RW)`
              )
            ),
            h("div", { className: "auto-org-stat-card" },
              h("div", { className: "auto-org-stat-label" }, "Verfügbarer Freispeicher"),
              h("div", { className: "auto-org-stat-value", style: { color: "#4ade80" } },
                `${mountData ? mountData.total_free_gb : 0} GB`
              ),
              h("div", { style: { fontSize: "0.75rem", color: "#94a3b8" } },
                "über beschreibbare Docker-Mounts"
              )
            ),
            h("div", { className: "auto-org-stat-card" },
              h("div", { className: "auto-org-stat-label" }, "Host-System-Schutz"),
              h("div", { className: "auto-org-stat-value", style: { fontSize: "1.25rem", color: "#4ade80" } }, "Geschützt"),
              h("div", { style: { fontSize: "0.75rem", color: "#94a3b8" } },
                "Unmountete Pfade (/etc, /root) blockiert"
              )
            )
          ),

          // Interactive Path Inspector
          h("div", { className: "auto-org-checker-box" },
            h("div", null,
              h("h4", { style: { fontSize: "1rem", fontWeight: 700 } }, "🔍 Docker Pfad-Inspector & Übersetzer"),
              h("p", { style: { fontSize: "0.8125rem", color: "#94a3b8", marginTop: "0.15rem" } },
                "Prüfen Sie beliebige Pfade auf Container-Erreichbarkeit und Schreibrechte vor dem Erstellen von Regeln."
              )
            ),
            h("div", { style: { display: "flex", gap: "0.5rem" } },
              h("input", {
                className: "auto-org-input",
                style: { flex: 1, fontFamily: "monospace", fontSize: "0.875rem" },
                placeholder: "/home/mb/Downloads oder /media/privat-data/10_PrivatBüro/Archiv/...",
                value: pathCheckInput,
                onChange: (e) => setPathCheckInput(e.target.value),
                onKeyDown: (e) => { if (e.key === "Enter") handleCheckPath(); }
              }),
              h("button", {
                type: "button",
                className: "auto-org-btn auto-org-btn-primary",
                style: { padding: "0.5rem 1.25rem", fontWeight: 600 },
                onClick: () => handleCheckPath(),
                disabled: checkingPath || !pathCheckInput.trim()
              }, checkingPath ? "Prüfe..." : "Pfad analysieren")
            ),
            // Presets
            h("div", { style: { display: "flex", alignItems: "center", gap: "0.35rem", flexWrap: "wrap" } },
              h("span", { style: { fontSize: "0.75rem", color: "#94a3b8" } }, "Schnelltests:"),
              h("button", { type: "button", className: "auto-org-tag-btn", onClick: () => { setPathCheckInput("/home/mb/Downloads"); handleCheckPath("/home/mb/Downloads"); } }, "Downloads"),
              h("button", { type: "button", className: "auto-org-tag-btn", onClick: () => { setPathCheckInput("/home/mb/Schreibtisch"); handleCheckPath("/home/mb/Schreibtisch"); } }, "Desktop"),
              h("button", { type: "button", className: "auto-org-tag-btn", onClick: () => { setPathCheckInput("/media/privat-data/10_PrivatBüro"); handleCheckPath("/media/privat-data/10_PrivatBüro"); } }, "PrivatBüro"),
              h("button", { type: "button", className: "auto-org-tag-btn", onClick: () => { setPathCheckInput("/media/work-data"); handleCheckPath("/media/work-data"); } }, "Work-Data"),
              h("button", { type: "button", className: "auto-org-tag-btn", onClick: () => { setPathCheckInput("/media/xchg/jules-mcp-server"); handleCheckPath("/media/xchg/jules-mcp-server"); } }, "Jules (Read-Only)"),
              h("button", { type: "button", className: "auto-org-tag-btn", onClick: () => { setPathCheckInput("/etc/shadow"); handleCheckPath("/etc/shadow"); } }, "Unmounted (/etc/shadow)")
            ),
            // Result Display
            pathCheckResult && h("div", {
              style: {
                background: pathCheckResult.valid ? "rgba(34, 197, 94, 0.12)" : pathCheckResult.is_mounted ? "rgba(234, 179, 8, 0.12)" : "rgba(239, 68, 68, 0.12)",
                border: `1px solid ${pathCheckResult.valid ? "rgba(34, 197, 94, 0.3)" : pathCheckResult.is_mounted ? "rgba(234, 179, 8, 0.3)" : "rgba(239, 68, 68, 0.3)"}`,
                borderRadius: "0.375rem",
                padding: "0.85rem 1rem",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                flexWrap: "wrap",
                gap: "0.5rem"
              }
            },
              h("div", null,
                h("div", { style: { fontWeight: 600, color: pathCheckResult.valid ? "#4ade80" : pathCheckResult.is_mounted ? "#facc15" : "#f87171" } },
                  pathCheckResult.message
                ),
                pathCheckResult.container_path && h("div", { style: { fontFamily: "monospace", fontSize: "0.75rem", color: "#94a3b8", marginTop: "0.25rem" } },
                  `Container-Pfad: ${pathCheckResult.container_path} • Host-Pfad: ${pathCheckResult.host_path || "-"}`
                )
              ),
              pathCheckResult.valid && h("div", { style: { display: "flex", gap: "0.35rem" } },
                h("button", {
                  type: "button",
                  className: "auto-org-btn auto-org-btn-outline",
                  style: { fontSize: "0.75rem", padding: "0.25rem 0.5rem" },
                  onClick: () => handleSetRuleSource(pathCheckResult.host_path)
                }, "➡️ Als Regel-Quelle"),
                h("button", {
                  type: "button",
                  className: "auto-org-btn auto-org-btn-primary",
                  style: { fontSize: "0.75rem", padding: "0.25rem 0.5rem" },
                  onClick: () => handleSetRuleTarget(pathCheckResult.host_path)
                }, "🎯 Als Regel-Ziel")
              )
            )
          ),

          // Mounts Table
          h("div", null,
            h("h4", { style: { fontSize: "1rem", fontWeight: 700, marginBottom: "0.5rem" } }, "Aktive Container-Mounts:"),
            h("table", { className: "auto-org-table" },
              h("thead", null,
                h("tr", null,
                  h("th", null, "Speicherbereich / Name"),
                  h("th", null, "Host-Pfad (Host-Dateisystem)"),
                  h("th", null, "Container-Pfad (Hermes)"),
                  h("th", null, "Rechte"),
                  h("th", null, "Freier Speicher"),
                  h("th", null, "Regel-Aktion")
                )
              ),
              h("tbody", null,
                mounts.length === 0 ?
                h("tr", null, h("td", { colSpan: 6, style: { textAlign: "center", color: "#94a3b8" } }, "Keine Docker Mounts gefunden.")) :
                mounts.map((m, idx) => {
                  const isRW = m.rw && m.is_writable;
                  return h("tr", { key: idx },
                    h("td", { style: { fontWeight: 600 } },
                      h("div", null, m.label),
                      h("span", { className: `auto-org-badge ${m.category === "Dumpzone" ? "auto-org-badge-yellow" : m.category === "Storage Root" ? "auto-org-badge-green" : "auto-org-badge-blue"}`, style: { marginTop: "0.25rem" } }, m.category)
                    ),
                    h("td", { style: { fontFamily: "monospace", fontSize: "0.75rem", color: "#93c5fd" } }, m.host_path),
                    h("td", { style: { fontFamily: "monospace", fontSize: "0.75rem", color: "#4ade80" } }, m.container_path),
                    h("td", null,
                      h("span", { className: `auto-org-badge ${isRW ? "auto-org-badge-green" : "auto-org-badge-yellow"}` },
                        isRW ? "RW (Schreibbar)" : "RO (Nur Lesen)"
                      )
                    ),
                    h("td", null,
                      h("div", { style: { fontSize: "0.8125rem", fontWeight: 600 } }, `${m.free_gb} GB frei`),
                      h("div", { className: "auto-org-progress-container" },
                        h("div", {
                          className: "auto-org-progress-fill",
                          style: {
                            width: `${Math.min(m.used_percent, 100)}%`,
                            background: m.used_percent > 85 ? "#f87171" : m.used_percent > 65 ? "#facc15" : "#3b82f6"
                          }
                        })
                      ),
                      h("div", { style: { fontSize: "0.7rem", color: "#94a3b8", marginTop: "0.15rem" } },
                        `${m.total_gb} GB gesamt (${m.used_percent}% belegt)`
                      )
                    ),
                    h("td", null,
                      h("div", { style: { display: "flex", gap: "0.35rem" } },
                        h("button", {
                          type: "button",
                          className: "auto-org-btn auto-org-btn-outline",
                          style: { fontSize: "0.75rem", padding: "0.25rem 0.5rem" },
                          onClick: () => handleSetRuleSource(m.host_path)
                        }, "➡️ Quelle"),
                        isRW && h("button", {
                          type: "button",
                          className: "auto-org-btn auto-org-btn-primary",
                          style: { fontSize: "0.75rem", padding: "0.25rem 0.5rem" },
                          onClick: () => handleSetRuleTarget(m.host_path)
                        }, "🎯 Ziel")
                      )
                    )
                  );
                })
              )
            )
          )
        );
      } else if (activeModal === "roots") {
        title = "📁 Überwachte Speicherwurzeln";
        content = h("table", { className: "auto-org-table" },
          h("thead", null,
            h("tr", null,
              h("th", null, "Name"),
              h("th", null, "Typ"),
              h("th", null, "Dateien"),
              h("th", null, "Größe"),
              h("th", null, "Modus"),
              h("th", null, "Pfad / URI")
            )
          ),
          h("tbody", null,
            roots.length === 0 ?
            h("tr", null, h("td", { colSpan: 6, style: { textAlign: "center", color: "#94a3b8" } }, "Keine Speicherwurzeln registriert.")) :
            roots.map((r) => h("tr", { key: r.id },
              h("td", { style: { fontWeight: 600 } }, r.name),
              h("td", null, h("span", { className: "auto-org-badge auto-org-badge-blue" }, r.type)),
              h("td", null, r.file_count),
              h("td", null, `${r.size_mb} MB`),
              h("td", null, r.watch_mode),
              h("td", { style: { fontFamily: "monospace", fontSize: "0.75rem" } }, r.uri_path)
            ))
          )
        );
      } else if (activeModal === "journal") {
        title = "📜 Reorganisations-Journal & 1-Klick Rollback";
        content = batches.length === 0 ?
          h("p", { style: { color: "#94a3b8", fontSize: "0.875rem", padding: "2rem", textAlign: "center" } }, "Noch keine Reorganisationen protokolliert.") :
          h("table", { className: "auto-org-table" },
            h("thead", null,
              h("tr", null,
                h("th", null, "Batch ID"),
                h("th", null, "Zeitpunkt"),
                h("th", null, "Verschobene Dateien"),
                h("th", null, "Operator"),
                h("th", null, "Status"),
                h("th", null, "Rollback")
              )
            ),
            h("tbody", null,
              batches.map((b) => {
                const canRollback = b.state === "EXECUTED";
                return h("tr", { key: b.batch_id },
                  h("td", { style: { fontFamily: "monospace", fontSize: "0.8125rem" } }, b.batch_id.slice(0, 12)),
                  h("td", null, b.started_at ? new Date(b.started_at).toLocaleString() : "-"),
                  h("td", { style: { fontWeight: 600 } }, b.file_count),
                  h("td", null, b.operator),
                  h("td", null,
                    h("span", {
                      className: canRollback ? "auto-org-badge auto-org-badge-green" : "auto-org-badge auto-org-badge-yellow"
                    }, b.state)
                  ),
                  h("td", null,
                    canRollback ?
                    h("button", {
                      className: "auto-org-btn auto-org-btn-danger",
                      onClick: () => handleRollback(b.batch_id)
                    }, "↩️ Zurückrollen") :
                    h("span", { style: { color: "#94a3b8", fontSize: "0.75rem" } }, "Wiederhergestellt")
                  )
                );
              })
            )
          );
      } else if (activeModal === "sync") {
        title = "☁️ Google Drive ↔ Lokaler Speicher: Synchronisations-Manager";
        content = h("div", { style: { display: "flex", flexDirection: "column", gap: "1.25rem" } },
          // Info banner
          h("div", {
            style: {
              background: "rgba(15, 23, 42, 0.75)",
              border: "1px solid #334155",
              borderRadius: "0.5rem",
              padding: "1rem 1.25rem",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: "0.75rem"
            }
          },
            h("div", null,
              h("div", { style: { fontWeight: 700, color: "#ffffff", fontSize: "0.95rem" } },
                "Selektiver Synchronisations-Abgleich (Selective Sync)"
              ),
              h("div", { style: { fontSize: "0.8125rem", color: "#94a3b8", marginTop: "0.2rem" } },
                "Definieren Sie, welche Google Drive Verzeichnisse auf lokale Host- bzw. Container-Mounts gespiegelt oder abgeglichen werden."
              )
            ),
            h("button", {
              type: "button",
              className: "auto-org-btn auto-org-btn-primary",
              onClick: () => setShowNewSyncForm(!showNewSyncForm)
            }, showNewSyncForm ? "✕ Formular schließen" : "+ Neuer Sync-Ordner anlegen")
          ),

          // New Sync Mapping Form
          showNewSyncForm && h("form", {
            onSubmit: handleSaveSyncMapping,
            style: {
              background: "rgba(30, 41, 59, 0.75)",
              border: "1px solid #3b82f6",
              borderRadius: "0.5rem",
              padding: "1.25rem",
              display: "flex",
              flexDirection: "column",
              gap: "1rem"
            }
          },
            h("h4", { style: { fontSize: "1rem", fontWeight: 700, color: "#ffffff" } }, "➕ Neuer Google Drive ↔ Lokaler Sync-Ordner"),
            h("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "0.85rem" } },
              h("div", { style: { display: "flex", flexDirection: "column", gap: "0.3rem" } },
                h("label", { style: { fontSize: "0.75rem", fontWeight: 600, color: "#94a3b8" } }, "Name der Zuordnung"),
                h("input", {
                  type: "text",
                  className: "auto-org-input",
                  placeholder: "z.B. PrivatBüro Dokumente",
                  value: newSyncName,
                  onChange: (e) => setNewSyncName(e.target.value),
                  required: true
                })
              ),
              h("div", { style: { display: "flex", flexDirection: "column", gap: "0.3rem" } },
                h("label", { style: { fontSize: "0.75rem", fontWeight: 600, color: "#94a3b8" } }, "Google Drive Ordner-Pfad"),
                h("input", {
                  type: "text",
                  className: "auto-org-input",
                  placeholder: "z.B. /PrivatBüro oder /Work",
                  value: newSyncDrivePath,
                  onChange: (e) => setNewSyncDrivePath(e.target.value),
                  required: true
                })
              ),
              h("div", { style: { display: "flex", flexDirection: "column", gap: "0.3rem" } },
                h("label", { style: { fontSize: "0.75rem", fontWeight: 600, color: "#94a3b8" } }, "Lokaler Pfad (Host / Container-Mount)"),
                h("input", {
                  type: "text",
                  className: "auto-org-input",
                  placeholder: "z.B. /media/privat-data/10_PrivatBüro",
                  value: newSyncLocalPath,
                  onChange: (e) => setNewSyncLocalPath(e.target.value),
                  required: true
                })
              ),
              h("div", { style: { display: "flex", flexDirection: "column", gap: "0.3rem" } },
                h("label", { style: { fontSize: "0.75rem", fontWeight: 600, color: "#94a3b8" } }, "Synchronisations-Richtung"),
                h("select", {
                  className: "auto-org-select",
                  value: newSyncDirection,
                  onChange: (e) => setNewSyncDirection(e.target.value)
                },
                  h("option", { value: "bidirectional" }, "⇄ Bidirektional (Beidseitiger Abgleich)"),
                  h("option", { value: "push" }, "⬆️ Lokal ➔ GDrive (Upload zu Drive)"),
                  h("option", { value: "pull" }, "⬇️ GDrive ➔ Lokal (Download & Spiegeln)")
                )
              ),
              h("div", { style: { display: "flex", flexDirection: "column", gap: "0.3rem" } },
                h("label", { style: { fontSize: "0.75rem", fontWeight: 600, color: "#94a3b8" } }, "Einschlussfilter (Include Glob-Patterns)"),
                h("input", {
                  type: "text",
                  className: "auto-org-input",
                  placeholder: "*.pdf, *.docx, *.xlsx, *.txt, *.md",
                  value: newSyncInclude,
                  onChange: (e) => setNewSyncInclude(e.target.value)
                })
              ),
              h("div", { style: { display: "flex", flexDirection: "column", gap: "0.3rem" } },
                h("label", { style: { fontSize: "0.75rem", fontWeight: 600, color: "#94a3b8" } }, "Ausschlussfilter (Exclude Glob-Patterns)"),
                h("input", {
                  type: "text",
                  className: "auto-org-input",
                  placeholder: "*.tmp, ~*, .git/*",
                  value: newSyncExclude,
                  onChange: (e) => setNewSyncExclude(e.target.value)
                })
              )
            ),
            h("div", { style: { display: "flex", justifyContent: "flex-end", gap: "0.5rem" } },
              h("button", {
                type: "button",
                className: "auto-org-btn auto-org-btn-outline",
                onClick: () => setShowNewSyncForm(false)
              }, "Abbrechen"),
              h("button", {
                type: "submit",
                className: "auto-org-btn auto-org-btn-primary",
                disabled: loading
              }, loading ? "Speichere..." : "✓ Sync-Ordner speichern")
            )
          ),

          // Configured Mappings Table
          h("div", null,
            h("h4", { style: { fontSize: "1rem", fontWeight: 700, color: "#ffffff", marginBottom: "0.5rem" } },
              `Konfigurierte Sync-Pfade (${syncMappings.length})`
            ),
            h("table", { className: "auto-org-table" },
              h("thead", null,
                h("tr", null,
                  h("th", null, "Name & Status"),
                  h("th", null, "Google Drive Pfad"),
                  h("th", null, "Lokaler Host- / Container-Pfad"),
                  h("th", null, "Richtung"),
                  h("th", null, "Mount-Status"),
                  h("th", null, "Letzter Sync"),
                  h("th", null, "Aktionen")
                )
              ),
              h("tbody", null,
                syncMappings.length === 0 ?
                h("tr", null, h("td", { colSpan: 7, style: { textAlign: "center", color: "#94a3b8" } }, "Keine Sync-Ordner definiert.")) :
                syncMappings.map((m) => {
                  const isBi = m.direction === "bidirectional";
                  const isPush = m.direction === "push";
                  const dirBadge = isBi ? "⇄ Bidirektional" : (isPush ? "⬆️ Push" : "⬇️ Pull");
                  const mountOk = m.mount_check && m.mount_check.valid && !m.mount_check.read_only;
                  return h("tr", { key: m.id },
                    h("td", null,
                      h("div", { style: { fontWeight: 600, color: "#ffffff" } }, m.name),
                      h("span", {
                        className: `auto-org-badge ${m.is_active ? "auto-org-badge-green" : "auto-org-badge-yellow"}`,
                        style: { marginTop: "0.2rem" }
                      }, m.is_active ? "Aktiv" : "Pausiert")
                    ),
                    h("td", { style: { fontFamily: "monospace", fontSize: "0.8125rem", color: "#60a5fa" } },
                      `gdrive:${m.drive_folder_path}`
                    ),
                    h("td", { style: { fontFamily: "monospace", fontSize: "0.8125rem", color: "#4ade80" } },
                      m.local_path
                    ),
                    h("td", null,
                      h("span", { className: "auto-org-sync-direction-badge" }, dirBadge)
                    ),
                    h("td", null,
                      mountOk ?
                        h("span", { className: "auto-org-badge auto-org-badge-green", title: `Container: ${m.mount_check.container_path}` }, "✓ OK (RW)") :
                        h("span", { className: "auto-org-badge auto-org-badge-yellow", title: (m.mount_check && m.mount_check.warning) || "Mount prüfen" }, "⚠️ Prüfen")
                    ),
                    h("td", { style: { fontSize: "0.75rem", color: "#94a3b8" } },
                      m.last_sync_at ? new Date(m.last_sync_at).toLocaleString() : "Noch nie"
                    ),
                    h("td", null,
                      h("div", { style: { display: "flex", gap: "0.35rem" } },
                        h("button", {
                          type: "button",
                          className: "auto-org-btn auto-org-btn-outline",
                          style: { fontSize: "0.75rem", padding: "0.25rem 0.5rem" },
                          onClick: () => handleCalculateSyncPlan(m.id),
                          disabled: planningId === m.id
                        }, planningId === m.id ? "Berechne..." : "🔍 Diff"),
                        h("button", {
                          type: "button",
                          className: "auto-org-btn auto-org-btn-primary",
                          style: { fontSize: "0.75rem", padding: "0.25rem 0.5rem" },
                          onClick: () => handleExecuteSync(m.id),
                          disabled: syncingId === m.id
                        }, syncingId === m.id ? "Sync..." : "⚡ Sync"),
                        h("button", {
                          type: "button",
                          className: "auto-org-btn auto-org-btn-danger",
                          style: { fontSize: "0.75rem", padding: "0.25rem 0.4rem" },
                          onClick: () => handleDeleteSyncMapping(m.id, m.name)
                        }, "✕")
                      )
                    )
                  );
                })
              )
            )
          ),

          // Sync Plan Diff Preview (if loaded)
          syncPlan && h("div", {
            style: {
              background: "rgba(15, 23, 42, 0.85)",
              border: "1px solid #3b82f6",
              borderRadius: "0.5rem",
              padding: "1.25rem",
              display: "flex",
              flexDirection: "column",
              gap: "0.75rem"
            }
          },
            h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center" } },
              h("h4", { style: { fontSize: "1rem", fontWeight: 700, color: "#ffffff" } },
                `Abgleichs-Vorschau: ${syncPlan.mapping_name} (${syncPlan.summary.total_items} Dateien)`
              ),
              h("div", { style: { display: "flex", gap: "0.5rem" } },
                h("span", { className: "auto-org-badge auto-org-badge-blue" }, `Uploads: ${syncPlan.summary.to_upload}`),
                h("span", { className: "auto-org-badge auto-org-badge-green" }, `Downloads: ${syncPlan.summary.to_download}`),
                h("span", { className: "auto-org-badge auto-org-badge-yellow" }, `In Sync: ${syncPlan.summary.in_sync}`)
              )
            ),
            h("table", { className: "auto-org-table" },
              h("thead", null,
                h("tr", null,
                  h("th", null, "Relative Datei"),
                  h("th", null, "Geplante Aktion"),
                  h("th", null, "Grund")
                )
              ),
              h("tbody", null,
                syncPlan.items.slice(0, 10).map((item, idx) => h("tr", { key: idx },
                  h("td", { style: { fontFamily: "monospace", fontSize: "0.8125rem", color: "#f8fafc" } }, item.relative_path),
                  h("td", null,
                    h("span", {
                      className: `auto-org-badge ${item.action === "upload" ? "auto-org-badge-blue" : item.action === "download" ? "auto-org-badge-green" : "auto-org-badge-yellow"}`
                    }, item.action)
                  ),
                  h("td", { style: { fontSize: "0.8125rem", color: "#94a3b8" } }, item.reason)
                ))
              )
            ),
            h("div", { style: { display: "flex", justifyContent: "flex-end", marginTop: "0.5rem" } },
              h("button", {
                type: "button",
                className: "auto-org-btn auto-org-btn-primary",
                onClick: () => handleExecuteSync(syncPlan.mapping_id)
              }, "🚀 Synchronisation jetzt anwenden")
            )
          )
        );
      }

      return h("div", {
        className: "auto-org-modal-backdrop",
        onClick: (e) => { if (e.target === e.currentTarget) setActiveModal(null); }
      },
        h("div", { className: "auto-org-modal" },
          h("div", { className: "auto-org-modal-header" },
            h("div", { className: "auto-org-modal-title" }, title),
            h("button", {
              className: "auto-org-modal-close",
              onClick: () => setActiveModal(null)
            }, "✕")
          ),
          h("div", { className: "auto-org-modal-body" }, content)
        )
      );
    };

    // Main App Shell
    return h("div", { className: "auto-org-container" },
      renderHeader(),
      renderNotice(),
      renderStatsStrip(),
      renderStepper(),

      // Step Contents
      step === 1 && renderStep1(),
      step === 2 && renderStep2(),
      step === 3 && renderStep3(),
      step === 4 && renderStep4(),

      // Configuration Modal Overlay
      renderConfigModal()
    );
  }

  function HeaderStatus() {
    const [stats, setStats] = useState(null);
    useEffect(() => {
      apiCall("/stats").then(setStats).catch(() => null);
    }, []);

    if (!stats) return null;
    const hasAnomalies = stats.open_anomalies > 0;
    return h("div", {
      style: {
        display: "inline-flex",
        alignItems: "center",
        gap: "0.375rem",
        fontSize: "0.75rem",
        color: "#94a3b8"
      }
    },
      h("span", {
        style: {
          width: "8px",
          height: "8px",
          borderRadius: "9999px",
          backgroundColor: hasAnomalies ? "#facc15" : "#4ade80"
        }
      }),
      h("span", null, `Organizer: ${hasAnomalies ? `${stats.open_anomalies} offen` : "Sauber"}`)
    );
  }

  window.__HERMES_PLUGINS__.register("auto-organizer", AutoOrganizerApp);
  window.__HERMES_PLUGINS__.registerSlot("auto-organizer", "header-right", HeaderStatus);
})();
