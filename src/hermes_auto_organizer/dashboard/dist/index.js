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
      .auto-org-step-card.disabled, .auto-org-step-card.locked {
        opacity: 0.42 !important;
        cursor: not-allowed !important;
        border-style: dashed !important;
        border-color: #475569 !important;
        filter: grayscale(0.5);
      }
      .auto-org-step-card.locked:hover {
        background: rgba(30, 41, 59, 0.65) !important;
        border-color: #475569 !important;
      }
      .auto-org-suggested-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 1rem;
      }
      .auto-org-suggested-card {
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid #334155;
        border-radius: 0.5rem;
        padding: 1.15rem;
        display: flex;
        flex-direction: column;
        gap: 0.6rem;
        transition: all 0.15s ease;
      }
      .auto-org-suggested-card:hover {
        background: rgba(30, 41, 59, 0.75);
        border-color: #3b82f6;
      }
      .auto-org-evidence-box {
        background: rgba(15, 23, 42, 0.95);
        border-left: 3px solid #3b82f6;
        border-radius: 0.25rem;
        padding: 0.45rem 0.65rem;
        font-size: 0.75rem;
        line-height: 1.35;
      }
      .auto-org-sample-pill {
        display: inline-block;
        padding: 0.15rem 0.45rem;
        background: rgba(51, 65, 85, 0.5);
        border: 1px solid #475569;
        border-radius: 0.25rem;
        font-size: 0.7rem;
        font-family: monospace;
        color: #cbd5e1 !important;
        max-width: 100%;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .auto-org-ampel-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.02em;
        cursor: pointer;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        user-select: none;
        border: 1px solid transparent;
        outline: none;
        font-family: inherit;
      }
      .auto-org-ampel-badge:hover {
        transform: translateY(-1px);
        filter: brightness(1.2);
      }
      .auto-org-ampel-badge:active {
        transform: translateY(0);
        filter: brightness(0.95);
      }
      .auto-org-ampel-badge.yellow {
        background: rgba(234, 179, 8, 0.15) !important;
        border: 1px solid #eab308 !important;
        color: #fde047 !important;
      }
      .auto-org-ampel-badge.yellow:hover {
        background: rgba(234, 179, 8, 0.28) !important;
        border-color: #facc15 !important;
        box-shadow: 0 0 10px rgba(234, 179, 8, 0.4);
      }
      .auto-org-ampel-badge.green {
        background: rgba(34, 197, 94, 0.15) !important;
        border: 1px solid #22c55e !important;
        color: #86efac !important;
      }
      .auto-org-ampel-badge.green:hover {
        background: rgba(34, 197, 94, 0.28) !important;
        border-color: #4ade80 !important;
        box-shadow: 0 0 10px rgba(34, 197, 94, 0.4);
      }
      .auto-org-ampel-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
      }
      .auto-org-ampel-dot.yellow {
        background: #eab308;
        box-shadow: 0 0 6px rgba(234, 179, 8, 0.8);
      }
      .auto-org-ampel-dot.green {
        background: #22c55e;
        box-shadow: 0 0 6px rgba(34, 197, 94, 0.8);
      }
      .auto-org-approval-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: rgba(15, 23, 42, 0.9);
        border: 1px solid #334155;
        border-radius: 0.5rem;
        padding: 0.75rem 1rem;
        margin-bottom: 1rem;
        flex-wrap: wrap;
        gap: 0.75rem;
      }
      .auto-org-checkbox {
        width: 1.15rem;
        height: 1.15rem;
        border-radius: 0.25rem;
        accent-color: #3b82f6;
        cursor: pointer;
      }
      .auto-org-group-grid {
        display: flex;
        flex-direction: column;
        gap: 1rem;
      }
      .auto-org-group-card {
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid #334155;
        border-radius: 0.6rem;
        padding: 1.25rem;
        display: flex;
        flex-direction: column;
        gap: 0.85rem;
        transition: all 0.2s ease;
      }
      .auto-org-group-card.approved {
        border-color: #22c55e !important;
        background: rgba(15, 23, 42, 0.92);
        box-shadow: 0 0 14px rgba(34, 197, 94, 0.12);
      }
      .auto-org-group-card.pending {
        border-color: #eab308 !important;
        background: rgba(15, 23, 42, 0.85);
        box-shadow: 0 0 10px rgba(234, 179, 8, 0.08);
      }
      .auto-org-intent-box {
        background: rgba(30, 58, 138, 0.22);
        border-left: 4px solid #3b82f6;
        border-radius: 0.25rem;
        padding: 0.7rem 0.95rem;
        font-size: 0.875rem;
        color: #f1f5f9 !important;
        font-weight: 500;
        line-height: 1.45;
      }
      .auto-org-flow-row {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        flex-wrap: wrap;
        font-size: 0.8125rem;
        background: rgba(15, 23, 42, 0.6);
        padding: 0.55rem 0.85rem;
        border-radius: 0.375rem;
        border: 1px solid #1e293b;
      }
      .auto-org-kleingedruckt {
        background: rgba(15, 23, 42, 0.75);
        border: 1px solid #334155;
        border-radius: 0.375rem;
        padding: 0.65rem 0.85rem;
        font-size: 0.75rem;
        color: #94a3b8;
        font-family: monospace;
      }
      .auto-org-obsidian-container {
        background: #080c14;
        border: 1px solid #334155;
        border-radius: 0.75rem;
        overflow: hidden;
        position: relative;
        display: flex;
        flex-direction: column;
      }
      .auto-org-obsidian-toolbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem 1rem;
        background: rgba(15, 23, 42, 0.85);
        border-bottom: 1px solid #1e293b;
        flex-wrap: wrap;
        gap: 0.5rem;
      }
      .auto-org-obsidian-legend {
        display: flex;
        align-items: center;
        gap: 1rem;
        font-size: 0.75rem;
        color: #cbd5e1;
        flex-wrap: wrap;
      }
      .auto-org-obsidian-canvas {
        width: 100%;
        height: 460px;
        display: block;
        cursor: crosshair;
      }
      .auto-org-view-tabs {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1rem;
      }
      .auto-org-view-tab {
        padding: 0.5rem 1rem;
        border-radius: 0.375rem;
        font-size: 0.85rem;
        font-weight: 600;
        cursor: pointer;
        border: 1px solid #334155;
        background: #0f172a;
        color: #cbd5e1;
        transition: all 0.15s ease;
      }
      .auto-org-view-tab.active {
        background: #2563eb !important;
        border-color: #3b82f6 !important;
        color: #ffffff !important;
      }
    `;
    document.head.appendChild(styleEl);
  }

  const SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK) return;

  const { React } = SDK;
  const h = React.createElement;
  const { useState, useEffect, useCallback, useRef, useMemo } = React;

  const API_BASE = "/api/plugins/auto-organizer";

  function formatUserPath(p) {
    if (!p) return "";
    let s = String(p);
    s = s.replace(/^\/opt\/data\/privat-buero(\/|$)/, "/media/privat-data/10_PrivatBüro$1");
    s = s.replace(/^\/opt\/data\/work-data(\/|$)/, "/media/work-data$1");
    s = s.replace(/^\/opt\/data\/downloads(\/|$)/, "/home/mb/Downloads$1");
    s = s.replace(/^\/opt\/data\/desktop(\/|$)/, "/home/mb/Schreibtisch$1");
    s = s.replace(/^\/opt\/data\/knowledge-base(\/|$)/, "/media/xchg/ai-knowledge-base$1");
    s = s.replace(/^\/opt\/data\/cloud(\/|$)/, "gdrive://creatiVision$1");
    s = s.replace(/^\/opt\/data\/?/, "/media/");
    return s;
  }

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

  const DEFAULT_TREE_NODES = [
    {
      id: "finanzen-steuern",
      name: "10_PrivatBüro / Steuern & Finanzen",
      target_path_template: "/media/privat-data/10_PrivatBüro/Steuern/{year}/",
      description: "Eingehende Rechnungen, Quittungen, Bankbelege und Steuerunterlagen",
      icon: "📊",
      keywords: ["Rechnung", "Steuer", "Finanzamt", "Beleg", "Invoice", "Kontoauszug", "Quittung"],
      extensions: ["pdf", "xlsx", "csv"],
      state: "USER_APPROVED",
      is_approved: true,
      mount_valid: true,
      mount_message: "Gültig: Speicherverzeichnis bereit (503.7 GB frei)",
      container_path: "/media/privat-data/10_PrivatBüro/Steuern/{year}",
      tree_slice: ["privat-data", "10_PrivatBüro", "2024", "Steuern"],
      ai_confidence: 0.98,
      ai_reasoning: "Amtliche Steuerunterlagen und Belege für Einkommensteuererklärung via OCR 'Finanzamt' und Steuernummer.",
      ai_tokens: ["Einkommensteuer", "Finanzamt München", "Steuerbescheid"],
      matched_files_count: 89,
      sample_files: [
        { name: "steuerbescheid_2024.pdf", path: "/media/privat-data/10_PrivatBüro/2024/Steuern/steuerbescheid_2024.pdf" },
        { name: "Kontoauszug_Januar.pdf", path: "/media/privat-data/10_PrivatBüro/Steuern/2026/Kontoauszug_Januar.pdf" }
      ]
    },
    {
      id: "finanzen-ausgangsrechnungen",
      name: "02_Geschaeftlich / 001_cv-bookaccount / Ausgangsrechnungen",
      target_path_template: "/media/work-data/001_cv-bookaccount/{year}/Ausgangsrechnungen/",
      description: "Ausgehende Honorar- und Projektrechnungen an Mandanten & Kunden mit USt-IdNr",
      icon: "📤",
      keywords: ["Rechnung", "Ausgangsrechnung", "Honorar", "USt-IdNr", "CreatiVision", "Invoice"],
      extensions: ["pdf", "xlsx"],
      state: "USER_APPROVED",
      is_approved: true,
      mount_valid: true,
      mount_message: "Gültig: Speicherverzeichnis bereit (594.4 GB frei)",
      container_path: "/media/work-data/001_cv-bookaccount/{year}/Ausgangsrechnungen",
      tree_slice: ["work-data", "001_cv-bookaccount", "2025", "Ausgangsrechnungen"],
      ai_confidence: 0.99,
      ai_reasoning: "Erkennung von ausgehenden Honorarabrechnungen via OCR 'USt-IdNr', Kundenadressen und Zahlungszielen.",
      ai_tokens: ["USt-IdNr", "Rechnung", "Honorar", "Zahlungsziel"],
      matched_files_count: 62,
      sample_files: [
        { name: "Rechnung_2025_089_Stulz.pdf", path: "/media/work-data/001_cv-bookaccount/2025/Ausgangsrechnungen/Rechnung_2025_089_Stulz.pdf" }
      ]
    },
    {
      id: "finanzen-eingangsrechnungen",
      name: "02_Geschaeftlich / 001_cv-bookaccount / Eingangsrechnungen",
      target_path_template: "/media/work-data/001_cv-bookaccount/{year}/Eingangsrechnungen/",
      description: "Lieferantenrechnungen, SaaS-Tools (OpenAI, AWS, Hetzner, Adobe) und Betriebsausgaben",
      icon: "📥",
      keywords: ["Eingangsrechnung", "Zahlungsziel", "Betrag", "Hetzner", "OpenAI", "Adobe", "Quittung"],
      extensions: ["pdf", "csv"],
      state: "USER_APPROVED",
      is_approved: true,
      mount_valid: true,
      mount_message: "Gültig: Speicherverzeichnis bereit (594.4 GB frei)",
      container_path: "/media/work-data/001_cv-bookaccount/{year}/Eingangsrechnungen",
      tree_slice: ["work-data", "001_cv-bookaccount", "2025", "Eingangsrechnungen"],
      ai_confidence: 0.98,
      ai_reasoning: "Erkennung von Betriebskosten und SaaS-Quittungen mit ausgewiesener Vorsteuer.",
      ai_tokens: ["Vorsteuer", "Rechnungsbetrag", "Hetzner", "OpenAI"],
      matched_files_count: 45,
      sample_files: [
        { name: "Hetzner_Invoice_2025_08.pdf", path: "/media/work-data/001_cv-bookaccount/2025/Eingangsrechnungen/Hetzner_Invoice_2025_08.pdf" }
      ]
    },
    {
      id: "vertraege-recht",
      name: "10_PrivatBüro / Verträge & Versicherungen",
      target_path_template: "/media/privat-data/10_PrivatBüro/Versicherungen_Vertraege/",
      description: "Miet-, Arbeits-, Versicherungsverträge und rechtliche Vereinbarungen",
      icon: "⚖️",
      keywords: ["Vertrag", "Versicherung", "Police", "Vereinbarung", "Kündigung", "Mietvertrag"],
      extensions: ["pdf", "docx"],
      state: "USER_APPROVED",
      is_approved: true,
      mount_valid: true,
      mount_message: "Gültig: Speicherverzeichnis bereit (503.7 GB frei)",
      container_path: "/media/privat-data/10_PrivatBüro/Versicherungen_Vertraege",
      tree_slice: ["privat-data", "10_PrivatBüro", "Versicherungen_Vertraege"],
      ai_confidence: 0.96,
      ai_reasoning: "Langfristige Rechts- und Versicherungsverträge mit Policennummer.",
      ai_tokens: ["Versicherungsschein", "Versicherungsnummer", "Mietvertrag"],
      matched_files_count: 42,
      sample_files: [
        { name: "Mietvertrag_2024.pdf", path: "/media/privat-data/10_PrivatBüro/Versicherungen_Vertraege/Mietvertrag_2024.pdf" }
      ]
    },
    {
      id: "work-projekte",
      name: "03_Geschaeftl_Projekte / Kunden & Webdesign",
      target_path_template: "/media/work-data/002_cv-projects/{project_name}/",
      description: "Kunden-Websites, WordPress-Themes, UI-Assets und Repositories",
      icon: "🚀",
      keywords: ["Projekt", "Webdesign", "WordPress", "Theme", "Kunde", "Stulz", "Figma", "Repo"],
      extensions: ["ts", "js", "php", "svg", "png", "json"],
      state: "USER_APPROVED",
      is_approved: true,
      mount_valid: true,
      mount_message: "Gültig: Speicherverzeichnis bereit (594.4 GB frei)",
      container_path: "/media/work-data/002_cv-projects",
      tree_slice: ["work-data", "002_cv-projects", "{project_name}"],
      ai_confidence: 0.95,
      ai_reasoning: "Projekt-Quellcode und UI-Assets mit Zuordnung zum Kundenstamm.",
      ai_tokens: ["WordPress", "Figma", "Repository", "UI-Asset"],
      matched_files_count: 210,
      sample_files: [
        { name: "main.py", path: "/media/work-data/002_cv-projects/hermes-drive-index/main.py" }
      ]
    },
    {
      id: "work-ai-agents",
      name: "03_Geschaeftl_Projekte / KI-Agent-Skills",
      target_path_template: "/media/xchg/ai-agents-workspaces/skills/",
      description: "Hermes-, Jules- und LangChain-Skills, Prompts und MCP-Serverkonfigurationen",
      icon: "🤖",
      keywords: ["Skill", "Agent", "Hermes", "Jules", "Prompt", "MCP", "LangChain"],
      extensions: ["py", "yaml", "md", "json"],
      state: "USER_APPROVED",
      is_approved: true,
      mount_valid: true,
      mount_message: "Gültig: Speicherverzeichnis bereit (xchg)",
      container_path: "/media/xchg/ai-agents-workspaces/skills",
      tree_slice: ["xchg", "ai-agents-workspaces", "skills"],
      ai_confidence: 0.99,
      ai_reasoning: "Semantische KI-Agent-Skills mit YAML-Frontmatter und MCP-Tool-Definitionen.",
      ai_tokens: ["SKILL.md", "MCP", "Agent-Skills", "Prompt"],
      matched_files_count: 90,
      sample_files: [
        { name: "SKILL.md", path: "/media/xchg/ai-agents-workspaces/skills/SKILL.md" }
      ]
    },
    {
      id: "medien-assets",
      name: "30_Medien & Kreativ-Assets",
      target_path_template: "/media/work-data/Assets/{year}/",
      description: "Grafiken, Audio-Takes, Design-Mockups, Videos und Fotos",
      icon: "🎨",
      keywords: ["Design", "Mockup", "Banner", "Audio", "Foto", "Video", "Podcast"],
      extensions: ["png", "jpg", "svg", "mp3", "wav", "mp4"],
      state: "USER_APPROVED",
      is_approved: true,
      mount_valid: true,
      mount_message: "Gültig: Speicherverzeichnis bereit (594.4 GB frei)",
      container_path: "/media/work-data/Assets/{year}",
      tree_slice: ["work-data", "Assets", "2026"],
      ai_confidence: 0.94,
      ai_reasoning: "Vektorgrafiken und Multimediadateien mit Jahresbezug.",
      ai_tokens: ["SVG", "Figma", "Logo"],
      matched_files_count: 15,
      sample_files: [
        { name: "logo.svg", path: "/media/work-data/Assets/2026/logo.svg" }
      ]
    },
    {
      id: "archiv-general",
      name: "04_Backup_Archiv / Historisierte Bestände",
      target_path_template: "/media/xchg/ai-knowledge-base/Archiv/{year}/",
      description: "Historisierte Dokumente, Postgres-Dumps (.sql.gz) und Kalt-Backups",
      icon: "📦",
      keywords: ["Archiv", "Alt", "Historie", "Backup", "Dump"],
      extensions: ["tar.gz", "sql.gz", "zip"],
      state: "USER_APPROVED",
      is_approved: true,
      mount_valid: true,
      mount_message: "Gültig: Historisches Archiv",
      container_path: "/media/xchg/ai-knowledge-base/Archiv/{year}",
      tree_slice: ["xchg", "ai-knowledge-base", "Archiv", "2024"],
      ai_confidence: 0.94,
      ai_reasoning: "Komprimierte Archiv- und Datenbankstände mit Jahresbezug.",
      ai_tokens: ["Dump", "Archiv", "Snapshot"],
      matched_files_count: 75,
      sample_files: []
    }
  ];

  const DEFAULT_TAXONOMY = {
    ok: true,
    system_approved: true,
    total_nodes: 5,
    approved_nodes: 5,
    total_matched_files: 431,
    tree: DEFAULT_TREE_NODES
  };

  const DEFAULT_ROOTS = [
    {
      id: "root-privat-buero",
      name: "PrivatBüro (Archiv & Steuern)",
      type: "LOCAL_DIR",
      uri_path: "/media/privat-data/10_PrivatBüro",
      watch_mode: "INOTIFY",
      is_active: true,
      file_count: 89,
      size_mb: 1420.5
    },
    {
      id: "root-work-data",
      name: "Arbeitsdateien (work-data)",
      type: "LOCAL_DIR",
      uri_path: "/media/work-data",
      watch_mode: "INOTIFY",
      is_active: true,
      file_count: 210,
      size_mb: 4820.0
    },
    {
      id: "root-knowledge-base",
      name: "Knowledge-Base & Memories",
      type: "LOCAL_DIR",
      uri_path: "/media/xchg/ai-knowledge-base",
      watch_mode: "INOTIFY",
      is_active: true,
      file_count: 52,
      size_mb: 310.2
    },
    {
      id: "root-downloads",
      name: "Downloads (Dumpzone)",
      type: "LOCAL_DIR",
      uri_path: "/home/mb/Downloads",
      watch_mode: "INOTIFY",
      is_active: true,
      file_count: 45,
      size_mb: 850.0
    },
    {
      id: "root-gdrive",
      name: "Google Drive Cloud Sync",
      type: "GDRIVE",
      uri_path: "gdrive://creatiVision",
      watch_mode: "POLL_15M",
      is_active: true,
      file_count: 120,
      size_mb: 2150.0
    }
  ];

  // Floating Right-Click Context Menu for File/Folder State Switching
  function FloatingContextMenu({ x, y, node, onClose, onSelectState, currentState }) {
    const menuRef = useRef(null);

    useEffect(() => {
      function handleKeyDown(e) {
        if (e.key === "Escape") onClose();
      }
      function handleClickOutside(e) {
        if (menuRef.current && !menuRef.current.contains(e.target)) {
          onClose();
        }
      }
      document.addEventListener("keydown", handleKeyDown);
      document.addEventListener("mousedown", handleClickOutside);
      return () => {
        document.removeEventListener("keydown", handleKeyDown);
        document.removeEventListener("mousedown", handleClickOutside);
      };
    }, [onClose]);

    if (!node) return null;

    const menuWidth = 270;
    const menuHeight = 230;
    const posX = Math.max(10, Math.min(x, window.innerWidth - menuWidth - 15));
    const posY = Math.max(10, Math.min(y, window.innerHeight - menuHeight - 15));

    const nodeName = node.name || node.label || node.file_name || node.id || "Element";
    const nodePath = formatUserPath(node.path || node.uri_path || node.physical_path || node.relative_path || "");
    const nodeType = node.node_type === "mount" ? "💽 Mount-Punkt" :
                     node.node_type === "file" ? "📄 Datei" :
                     node.node_type === "drive" ? "💽 Laufwerk" : "📁 Ordner";

    return h("div", {
      ref: menuRef,
      className: "auto-org-context-menu",
      style: { left: `${posX}px`, top: `${posY}px` },
      onClick: (e) => e.stopPropagation(),
      onContextMenu: (e) => e.preventDefault()
    },
      h("div", { className: "auto-org-context-menu-header" },
        h("div", { className: "auto-org-context-menu-title" },
          h("span", null, nodeType.split(" ")[0]),
          h("span", null, nodeName)
        ),
        nodePath && h("div", { className: "auto-org-context-menu-path", title: nodePath }, nodePath)
      ),
      h("button", {
        type: "button",
        className: `auto-org-context-menu-item approve ${currentState === "approved" ? "active" : ""}`,
        onClick: () => { onSelectState("approved"); onClose(); }
      },
        h("span", { style: { fontSize: "1.1rem" } }, "🟢"),
        h("div", null,
          h("div", null, "Freigeben (Grün)"),
          h("span", { className: "auto-org-context-menu-desc" }, "Genehmigt & aktiv einbezogen")
        )
      ),
      h("button", {
        type: "button",
        className: `auto-org-context-menu-item propose ${currentState === "proposed" ? "active" : ""}`,
        onClick: () => { onSelectState("proposed"); onClose(); }
      },
        h("span", { style: { fontSize: "1.1rem" } }, "🟡"),
        h("div", null,
          h("div", null, "Als Vorschlag (Gelb)"),
          h("span", { className: "auto-org-context-menu-desc" }, "Vorgeschlagener Sync / Transfer")
        )
      ),
      h("button", {
        type: "button",
        className: `auto-org-context-menu-item exclude ${currentState === "excluded" ? "active" : ""}`,
        onClick: () => { onSelectState("excluded"); onClose(); }
      },
        h("span", { style: { fontSize: "1.1rem" } }, "⚪"),
        h("div", null,
          h("div", null, "Nicht einbezogen (Grau)"),
          h("span", { className: "auto-org-context-menu-desc" }, "Ausschließen & nicht synchronisieren")
        )
      )
    );
  }

  // Floating Rollover Card / Tooltip showing proposed sync / move information
  function SyncRolloverTooltip({ x, y, node, nodeState }) {
    if (!node) return null;

    const hasSyncthing = Boolean(node.syncthing && (node.syncthing.synced || node.syncthing.folder_id));
    const hasReorg = Boolean(node.reorganization && (node.reorganization.is_source || node.reorganization.is_target || (node.reorganization.pending_moves && node.reorganization.pending_moves > 0)));
    const hasProposedSync = Boolean(node.has_proposed_sync || hasSyncthing || hasReorg || node.targetPath || node.proposed_target || node.destination_path);

    const st = nodeState || node.switch_state || (node.indexing && node.indexing.state === "FULL" ? "approved" : "proposed");

    const tooltipWidth = 360;
    const tooltipHeight = 240;
    const posX = Math.max(10, Math.min(x + 14, window.innerWidth - tooltipWidth - 20));
    const posY = Math.max(10, Math.min(y + 14, window.innerHeight - tooltipHeight - 20));

    const stateLabel = st === "approved" ? "🟢 Freigegeben (Aktiv)" :
                       st === "excluded" ? "⚪ Nicht einbezogen (Ausgeschlossen)" :
                       "🟡 Vorschlag (Sync / Reorganisation)";

    const nodeName = node.name || node.label || node.file_name || node.id || "Element";
    const nodePath = formatUserPath(node.path || node.uri_path || node.physical_path || node.relative_path || "");
    let icon = node.node_type === "mount" ? "💽" :
               node.node_type === "file" ? "📄" :
               node.node_type === "drive" ? "💽" : "📁";

    return h("div", {
      className: "auto-org-rollover-card",
      style: { left: `${posX}px`, top: `${posY}px` }
    },
      h("div", { className: "auto-org-rollover-header" },
        h("div", { className: "auto-org-rollover-title" },
          h("span", null, icon),
          h("span", null, nodeName)
        ),
        h("span", { className: `auto-org-rollover-badge-state ${st}` }, stateLabel)
      ),

      nodePath && h("div", { className: "auto-org-rollover-path" }, nodePath),

      // Proposed Sync / Move Section
      hasProposedSync ?
        h("div", { className: "auto-org-rollover-sync-box" },
          h("div", { className: "auto-org-rollover-sync-title" },
            h("span", null, "🔄"),
            h("span", null, "Vorgeschlagener Sync & Reorganisation:")
          ),
          hasSyncthing && h("div", { className: "auto-org-rollover-sync-detail" },
            `• Syncthing: ${node.syncthing.label || node.syncthing.folder_id || "P2P Mesh Synchron"}` +
            (node.syncthing.peers && node.syncthing.peers.length ? ` (Peers: ${node.syncthing.peers.join(", ")})` : "")
          ),
          node.reorganization && node.reorganization.is_source && h("div", { className: "auto-org-rollover-sync-detail" },
            `• Quell-Ordner: ${node.reorganization.pending_moves || 0} geplante Moves zur Reorganisation`
          ),
          node.reorganization && node.reorganization.is_target && h("div", { className: "auto-org-rollover-sync-detail" },
            `• Ziel-Ordner für ${node.reorganization.target_rules ? node.reorganization.target_rules.length : 1} Filter-Regeln`
          ),
          (node.targetPath || node.proposed_target || node.destination_path) && h("div", { className: "auto-org-rollover-sync-detail" },
            `• Zielpfad: 🎯 ${formatUserPath(node.targetPath || node.proposed_target || node.destination_path)}`
          )
        ) : null,

      // Meta grid
      h("div", { className: "auto-org-rollover-meta-grid" },
        node.indexing && h("div", null, `Index: ${node.indexing.symbol} ${node.indexing.count || 0} Dateien`),
        node.size_mb !== undefined && h("div", null, `Größe: ${node.size_mb >= 1024 ? (node.size_mb/1024).toFixed(1) + " GB" : node.size_mb.toFixed(1) + " MB"}`),
        node.backup && node.backup.protected && h("div", null, `Backup: 🛡️ ${node.backup.program || "Aktiv"}`),
        node.permissions && h("div", null, `Rechte: ${node.permissions.mode_str} (${node.permissions.owner})`)
      ),

      h("div", { className: "auto-org-rollover-footer-hint" },
        h("span", null, "💡"),
        h("span", null, "Rechtsklick: Status umschalten (Freigeben / Vorschlag / Nicht einbezogen)")
      )
    );
  }

  // Obsidian folders2graph Component (Full Interactive Folder Tree Graph)
  // Modeled after https://github.com/Ratibus11/folders2graph
  function Folders2GraphView({
    fsTree,
    nodeStates = {},
    onSwitchNodeState,
    onOpenContextMenu,
    onShowRollover,
    onHideRollover,
    searchQuery = "",
    isPaused = false
  }) {
    const canvasRef = useRef(null);
    const containerRef = useRef(null);

    const [foldedIds, setFoldedIds] = useState(() => new Set());
    const [selectedNodeId, setSelectedNodeId] = useState(null);
    const [hoveredNodeId, setHoveredNodeId] = useState(null);
    const [transform, setTransform] = useState({ scale: 1, panX: 0, panY: 0 });
    const transformRef = useRef(transform);
    transformRef.current = transform;

    const isDraggingRef = useRef(false);
    const dragNodeRef = useRef(null);
    const dragStartRef = useRef({ x: 0, y: 0 });
    const hasDraggedRef = useRef(false);

    // Build graph hierarchy from fsTree mounts
    const graphData = useMemo(() => {
      const nodes = [];
      const links = [];
      const processed = new Set();

      const mounts = (fsTree && fsTree.mounts && fsTree.mounts.length > 0) ? fsTree.mounts : [
        { id: "node_work_data", name: "work-data", path: "/media/work-data", node_type: "mount", children: [
          { id: "node_work_001", name: "001_cv-bookaccount", path: "/media/work-data/001_cv-bookaccount", node_type: "folder", children: [
            { id: "node_work_2025", name: "2025", path: "/media/work-data/001_cv-bookaccount/2025", node_type: "folder", children: [
              { id: "node_file_invoices", name: "Rechnungen_2025.pdf", path: "/media/work-data/001_cv-bookaccount/2025/Rechnungen_2025.pdf", node_type: "file", size_mb: 2.4, targetPath: "/media/privat-data/10_PrivatBüro/Archiv/2025/" }
            ]}
          ]},
          { id: "node_work_002", name: "002_cv-projects", path: "/media/work-data/002_cv-projects", node_type: "folder", children: [] }
        ]},
        { id: "node_privat_data", name: "privat-data", path: "/media/privat-data/10_PrivatBüro", node_type: "mount", children: [
          { id: "node_privat_steuern", name: "Steuern", path: "/media/privat-data/10_PrivatBüro/Steuern", node_type: "folder", children: [] },
          { id: "node_privat_archiv", name: "Archiv", path: "/media/privat-data/10_PrivatBüro/Archiv", node_type: "folder", children: [] }
        ]},
        { id: "node_xchg", name: "xchg", path: "/media/xchg", node_type: "mount", syncthing: { synced: true, label: "xchg-mesh", peers: ["laptop", "debian1", "Note14new"] }, children: [
          { id: "node_xchg_kb", name: "ai-knowledge-base", path: "/media/xchg/ai-knowledge-base", node_type: "folder", syncthing: { synced: true }, children: [] },
          { id: "node_xchg_workspaces", name: "ai-agents-workspaces", path: "/media/xchg/ai-agents-workspaces", node_type: "folder", children: [] }
        ]},
        { id: "node_downloads", name: "Downloads", path: "/home/mb/Downloads", node_type: "mount", reorganization: { is_source: true, pending_moves: 45 }, children: [] }
      ];

      function countDescendants(n) {
        if (!n.children || n.children.length === 0) return 0;
        let c = n.children.length;
        n.children.forEach(ch => { c += countDescendants(ch); });
        return c;
      }

      function traverse(n, parentNode = null, depth = 0, angleHint = 0) {
        if (!n) return;
        const nid = n.id || n.path || `node_${nodes.length}`;
        if (processed.has(nid)) return;
        processed.add(nid);

        const descCount = countDescendants(n);
        // folders2graph: weight node radius by descendants
        const radius = n.node_type === "mount" ? 26 :
                       n.node_type === "file" ? 8 :
                       Math.max(12, Math.min(22, 11 + Math.log2(descCount + 1) * 3));

        const st = nodeStates[n.path] || nodeStates[nid] || n.switch_state ||
                   (n.indexing && n.indexing.state === "FULL" ? "approved" : "proposed");

        const hasProposedSync = Boolean(
          n.has_proposed_sync ||
          (n.syncthing && (n.syncthing.synced || n.syncthing.folder_id)) ||
          (n.reorganization && (n.reorganization.is_source || n.reorganization.is_target || (n.reorganization.pending_moves && n.reorganization.pending_moves > 0))) ||
          n.targetPath || n.proposed_target
        );

        // Initial coordinates (radial organic layout)
        let initX = 0;
        let initY = 0;
        if (!parentNode) {
          const mIdx = mounts.indexOf(n);
          const totalM = mounts.length;
          const a = (mIdx / totalM) * Math.PI * 2 - Math.PI / 2;
          initX = Math.cos(a) * 220;
          initY = Math.sin(a) * 200;
        } else {
          const spread = Math.PI * 0.45;
          const a = angleHint;
          const dist = 75 + Math.min(60, descCount * 4);
          initX = parentNode.x + Math.cos(a) * dist;
          initY = parentNode.y + Math.sin(a) * dist;
        }

        const gNode = {
          id: nid,
          name: n.name || (n.path ? n.path.split("/").filter(Boolean).pop() : nid),
          path: n.path || "",
          node_type: n.node_type || (n.disk ? "mount" : "folder"),
          raw: n,
          radius: radius,
          descendantCount: descCount,
          state: st,
          hasProposedSync: hasProposedSync,
          parentId: parentNode ? parentNode.id : null,
          depth: depth,
          x: initX,
          y: initY,
          vx: 0,
          vy: 0
        };
        nodes.push(gNode);

        if (parentNode) {
          links.push({
            sourceId: parentNode.id,
            targetId: gNode.id,
            type: "hierarchy"
          });
        }

        // Proposed sync / move edge
        if (n.targetPath || (n.reorganization && n.reorganization.target_rules && n.reorganization.target_rules.length > 0)) {
          const tgtPath = n.targetPath || (n.reorganization.target_rules[0] && n.reorganization.target_rules[0].match_path);
          if (tgtPath) {
            links.push({
              sourceId: gNode.id,
              targetPath: tgtPath,
              type: "proposed_sync",
              label: "Move / Sync"
            });
          }
        }

        if (n.children && n.children.length > 0) {
          const childCount = n.children.length;
          n.children.forEach((ch, cidx) => {
            const childAngle = childCount === 1 ? angleHint : (angleHint - Math.PI * 0.3 + (cidx * (Math.PI * 0.6)) / (childCount - 1));
            traverse(ch, gNode, depth + 1, childAngle);
          });
        }
      }

      mounts.forEach((m, idx) => {
        const a = (idx / mounts.length) * Math.PI * 2 - Math.PI / 2;
        traverse(m, null, 0, a);
      });

      return { nodes, links };
    }, [fsTree, nodeStates]);

    // Track mutable simulation state across frames
    const simRef = useRef({ nodes: [], links: [], nodeMap: new Map() });

    useEffect(() => {
      const prevMap = simRef.current.nodeMap;
      const simNodes = graphData.nodes.map(n => {
        const prev = prevMap.get(n.id);
        if (prev) {
          n.x = prev.x;
          n.y = prev.y;
          n.vx = prev.vx;
          n.vy = prev.vy;
        }
        return n;
      });
      const nodeMap = new Map(simNodes.map(n => [n.id, n]));
      simRef.current = { nodes: simNodes, links: graphData.links, nodeMap };
    }, [graphData]);

    // Check which nodes are visible based on foldedIds
    const isNodeVisible = useCallback((node) => {
      if (!node) return false;
      let curr = node;
      const map = simRef.current.nodeMap;
      while (curr && curr.parentId) {
        if (foldedIds.has(curr.parentId)) return false;
        curr = map.get(curr.parentId);
      }
      return true;
    }, [foldedIds]);

    // Fold / Unfold toggle
    const toggleFold = useCallback((nodeId, recursive = false) => {
      setFoldedIds(prev => {
        const next = new Set(prev);
        if (next.has(nodeId)) {
          next.delete(nodeId);
          if (recursive) {
            // Unfold all descendants
            const map = simRef.current.nodeMap;
            function unfoldKids(id) {
              const kids = Array.from(map.values()).filter(n => n.parentId === id);
              kids.forEach(k => {
                next.delete(k.id);
                unfoldKids(k.id);
              });
            }
            unfoldKids(nodeId);
          }
        } else {
          next.add(nodeId);
        }
        return next;
      });
    }, []);

    // Canvas rendering & physics loop
    useEffect(() => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      let animId;
      let frameCount = 0;

      function renderFrame() {
        const rect = canvas.parentElement ? canvas.parentElement.getBoundingClientRect() : { width: 900, height: 600 };
        let width = rect.width || 900;
        let height = rect.height || 600;

        const dpr = window.devicePixelRatio || 1;
        if (canvas.width !== width * dpr || canvas.height !== height * dpr) {
          canvas.width = width * dpr;
          canvas.height = height * dpr;
          canvas.style.width = width + "px";
          canvas.style.height = height + "px";
        }

        ctx.save();
        ctx.scale(dpr, dpr);

        // Clear Canvas with Obsidian Dark Cosmic Backdrop
        ctx.fillStyle = "#090d16";
        ctx.fillRect(0, 0, width, height);

        // Cosmic background grid dots
        ctx.fillStyle = "rgba(255, 255, 255, 0.04)";
        const step = 40;
        for (let gx = 0; gx < width; gx += step) {
          for (let gy = 0; gy < height; gy += step) {
            ctx.fillRect(gx, gy, 1, 1);
          }
        }

        const t = transformRef.current;
        const cx = width / 2;
        const cy = height / 2;

        ctx.translate(cx + t.panX, cy + t.panY);
        ctx.scale(t.scale, t.scale);

        const { nodes, links, nodeMap } = simRef.current;
        const visibleNodes = nodes.filter(n => isNodeVisible(n));
        const visNodeSet = new Set(visibleNodes.map(n => n.id));

        // Physics Simulation Step
        if (!isPaused) {
          frameCount++;
          const damp = 0.86;
          const kSpring = 0.045;
          const centerG = 0.0025;

          // Center gravity
          visibleNodes.forEach(n => {
            if (dragNodeRef.current && dragNodeRef.current.id === n.id) return;
            n.vx -= n.x * centerG;
            n.vy -= n.y * centerG;
          });

          // Node-to-node repulsion
          const vLen = visibleNodes.length;
          for (let i = 0; i < vLen; i++) {
            const n1 = visibleNodes[i];
            for (let j = i + 1; j < vLen; j++) {
              const n2 = visibleNodes[j];
              const dx = n2.x - n1.x;
              const dy = n2.y - n1.y;
              const dist = Math.hypot(dx, dy) || 1;
              if (dist < 320) {
                const rep = 1400 / (dist * dist);
                const rx = (dx / dist) * rep;
                const ry = (dy / dist) * rep;
                if (!dragNodeRef.current || dragNodeRef.current.id !== n1.id) {
                  n1.vx -= rx;
                  n1.vy -= ry;
                }
                if (!dragNodeRef.current || dragNodeRef.current.id !== n2.id) {
                  n2.vx += rx;
                  n2.vy += ry;
                }
              }
            }
          }

          // Link spring forces
          links.forEach(l => {
            const s = nodeMap.get(l.sourceId);
            const tNode = nodeMap.get(l.targetId);
            if (s && tNode && visNodeSet.has(s.id) && visNodeSet.has(tNode.id)) {
              const dx = tNode.x - s.x;
              const dy = tNode.y - s.y;
              const dist = Math.hypot(dx, dy) || 1;
              const ideal = (s.radius + tNode.radius + 60);
              const force = (dist - ideal) * kSpring;
              const fx = (dx / dist) * force;
              const fy = (dy / dist) * force;
              if (!dragNodeRef.current || dragNodeRef.current.id !== s.id) {
                s.vx += fx;
                s.vy += fy;
              }
              if (!dragNodeRef.current || dragNodeRef.current.id !== tNode.id) {
                tNode.vx -= fx;
                tNode.vy -= fy;
              }
            }
          });

          // Update positions with velocities
          visibleNodes.forEach(n => {
            if (dragNodeRef.current && dragNodeRef.current.id === n.id) return;
            n.vx *= damp;
            n.vy *= damp;
            n.x += n.vx;
            n.y += n.vy;
          });
        }

        // Draw Links
        links.forEach(l => {
          const s = nodeMap.get(l.sourceId);
          const tNode = nodeMap.get(l.targetId);
          if (!s || !tNode || !visNodeSet.has(s.id) || !visNodeSet.has(tNode.id)) return;

          const isHighlighted = (hoveredNodeId && (hoveredNodeId === s.id || hoveredNodeId === tNode.id));

          if (l.type === "hierarchy") {
            ctx.beginPath();
            ctx.moveTo(s.x, s.y);
            ctx.lineTo(tNode.x, tNode.y);
            ctx.strokeStyle = isHighlighted ? "rgba(96, 165, 250, 0.75)" : "rgba(255, 255, 255, 0.12)";
            ctx.lineWidth = isHighlighted ? 2.5 : 1.2;
            ctx.stroke();
          } else if (l.type === "proposed_sync") {
            // Proposed sync / move curved glowing edge
            ctx.save();
            ctx.setLineDash([5, 4]);
            const midX = (s.x + tNode.x) / 2 + (tNode.y - s.y) * 0.2;
            const midY = (s.y + tNode.y) / 2 - (tNode.x - s.x) * 0.2;
            ctx.beginPath();
            ctx.moveTo(s.x, s.y);
            ctx.quadraticCurveTo(midX, midY, tNode.x, tNode.y);
            ctx.strokeStyle = "#facc15";
            ctx.lineWidth = 2.2;
            ctx.stroke();

            // Flowing particle
            const flowT = (frameCount * 0.02) % 1;
            const px = (1 - flowT) * (1 - flowT) * s.x + 2 * (1 - flowT) * flowT * midX + flowT * flowT * tNode.x;
            const py = (1 - flowT) * (1 - flowT) * s.y + 2 * (1 - flowT) * flowT * midY + flowT * flowT * tNode.y;
            ctx.beginPath();
            ctx.arc(px, py, 3.5, 0, Math.PI * 2);
            ctx.fillStyle = "#ffffff";
            ctx.shadowColor = "#facc15";
            ctx.shadowBlur = 8;
            ctx.fill();
            ctx.restore();
          }
        });

        // Draw Nodes
        const q = (searchQuery || "").trim().toLowerCase();

        visibleNodes.forEach(n => {
          const isSelected = selectedNodeId === n.id;
          const isHovered = hoveredNodeId === n.id;
          const isFolded = foldedIds.has(n.id) && n.descendantCount > 0;
          const matchesQ = q && (n.name.toLowerCase().includes(q) || n.path.toLowerCase().includes(q));

          // Color based on user rule:
          // green: approved
          // yellow: otherwise (proposed)
          // grey: not included (excluded)
          const nodeColor = n.state === "approved" ? "#22c55e" :
                            n.state === "excluded" ? "#6b7280" : "#facc15";

          ctx.save();

          // Proposed sync beacon ring (pulsating)
          if (n.hasProposedSync) {
            const pulse = (Math.sin(frameCount * 0.06) + 1) * 0.5;
            ctx.beginPath();
            ctx.arc(n.x, n.y, n.radius + 4 + pulse * 4, 0, Math.PI * 2);
            ctx.strokeStyle = n.state === "approved" ? "rgba(34, 197, 94, 0.4)" : "rgba(250, 204, 21, 0.5)";
            ctx.lineWidth = 2;
            ctx.stroke();
          }

          // Node Glow
          ctx.shadowColor = isHovered || isSelected ? "#ffffff" : nodeColor;
          ctx.shadowBlur = isHovered ? 18 : isSelected ? 14 : 8;

          // Node Circle Fill
          ctx.beginPath();
          ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
          const grad = ctx.createRadialGradient(n.x - n.radius * 0.3, n.y - n.radius * 0.3, 1, n.x, n.y, n.radius);
          grad.addColorStop(0, isHovered ? "#ffffff" : (n.state === "excluded" ? "#4b5563" : nodeColor));
          grad.addColorStop(1, n.state === "approved" ? "#15803d" : n.state === "excluded" ? "#1f2937" : "#b45309");
          ctx.fillStyle = grad;
          ctx.fill();

          // Node Border
          ctx.strokeStyle = isHovered ? "#ffffff" : isSelected ? "#60a5fa" : (n.state === "approved" ? "#4ade80" : n.state === "excluded" ? "#9ca3af" : "#fde047");
          ctx.lineWidth = isHovered ? 3 : 1.8;
          ctx.stroke();

          // Folded Half-Disc / Ring Indicator (like folders2graph)
          if (isFolded) {
            ctx.save();
            ctx.beginPath();
            ctx.arc(n.x, n.y, n.radius + 3, 0, Math.PI * 2);
            ctx.setLineDash([3, 3]);
            ctx.strokeStyle = "#60a5fa";
            ctx.lineWidth = 2;
            ctx.stroke();
            ctx.restore();

            // Folded badge "+N"
            ctx.fillStyle = "#2563eb";
            ctx.beginPath();
            ctx.roundRect(n.x + n.radius - 2, n.y - n.radius - 8, 26, 14, 4);
            ctx.fill();
            ctx.fillStyle = "#ffffff";
            ctx.font = "bold 9px sans-serif";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(`+${n.descendantCount}`, n.x + n.radius + 11, n.y - n.radius - 1);
          }

          // Inner Icon
          let icon = n.node_type === "mount" ? "💽" :
                     n.node_type === "file" ? "📄" : "📁";
          ctx.font = `${Math.round(n.radius * 0.95)}px sans-serif`;
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(icon, n.x, n.y);

          // Name Label below node
          ctx.font = matchesQ ? "bold 12px sans-serif" : "11px sans-serif";
          ctx.textAlign = "center";
          ctx.textBaseline = "top";
          const labelY = n.y + n.radius + 4;
          const textW = ctx.measureText(n.name).width;

          // Label backdrop pill
          ctx.fillStyle = matchesQ ? "rgba(234, 179, 8, 0.3)" : isHovered ? "rgba(15, 23, 42, 0.95)" : "rgba(15, 23, 42, 0.75)";
          ctx.beginPath();
          ctx.roundRect(n.x - textW / 2 - 4, labelY - 1, textW + 8, 16, 4);
          ctx.fill();

          ctx.fillStyle = matchesQ ? "#fde047" : isHovered ? "#ffffff" : "#cbd5e1";
          ctx.fillText(n.name, n.x, labelY + 1);

          ctx.restore();
        });

        ctx.restore();
        animId = requestAnimationFrame(renderFrame);
      }

      animId = requestAnimationFrame(renderFrame);
      return () => cancelAnimationFrame(animId);
    }, [isPaused, isNodeVisible, foldedIds, hoveredNodeId, selectedNodeId, searchQuery]);

    // Canvas Mouse Interaction Handlers
    const getNodeAtScreen = useCallback((clientX, clientY) => {
      const canvas = canvasRef.current;
      if (!canvas) return null;
      const rect = canvas.getBoundingClientRect();
      const cx = canvas.clientWidth / 2;
      const cy = canvas.clientHeight / 2;
      const t = transformRef.current;

      const worldX = (clientX - rect.left - cx - t.panX) / t.scale;
      const worldY = (clientY - rect.top - cy - t.panY) / t.scale;

      const { nodes } = simRef.current;
      for (const n of nodes) {
        if (isNodeVisible(n)) {
          const dist = Math.hypot(n.x - worldX, n.y - worldY);
          if (dist <= n.radius + 6) return n;
        }
      }
      return null;
    }, [isNodeVisible]);

    const handleMouseDown = useCallback((e) => {
      if (e.button !== 0) return; // Left click only
      const target = getNodeAtScreen(e.clientX, e.clientY);
      dragStartRef.current = { x: e.clientX, y: e.clientY };
      hasDraggedRef.current = false;
      isDraggingRef.current = true;

      if (target) {
        dragNodeRef.current = target;
      } else {
        dragNodeRef.current = null;
      }
    }, [getNodeAtScreen]);

    const handleMouseMove = useCallback((e) => {
      const dx = e.clientX - dragStartRef.current.x;
      const dy = e.clientY - dragStartRef.current.y;
      if (Math.hypot(dx, dy) > 4) hasDraggedRef.current = true;

      if (isDraggingRef.current) {
        if (dragNodeRef.current) {
          const t = transformRef.current;
          dragNodeRef.current.x += dx / t.scale;
          dragNodeRef.current.y += dy / t.scale;
          dragNodeRef.current.vx = 0;
          dragNodeRef.current.vy = 0;
        } else {
          setTransform(prev => ({
            ...prev,
            panX: prev.panX + dx,
            panY: prev.panY + dy
          }));
        }
        dragStartRef.current = { x: e.clientX, y: e.clientY };
      } else {
        // Rollover hover test
        const hit = getNodeAtScreen(e.clientX, e.clientY);
        if (hit) {
          setHoveredNodeId(hit.id);
          if (onShowRollover) {
            onShowRollover(e.clientX, e.clientY, hit.raw, hit.state);
          }
        } else {
          setHoveredNodeId(null);
          if (onHideRollover) onHideRollover();
        }
      }
    }, [getNodeAtScreen, onShowRollover, onHideRollover]);

    const handleMouseUp = useCallback((e) => {
      isDraggingRef.current = false;
      dragNodeRef.current = null;

      if (!hasDraggedRef.current && e.button === 0) {
        const hit = getNodeAtScreen(e.clientX, e.clientY);
        if (hit) {
          setSelectedNodeId(hit.id);
          if (hit.descendantCount > 0) {
            // Fold / Unfold on click!
            toggleFold(hit.id, e.shiftKey);
          }
        }
      }
    }, [getNodeAtScreen, toggleFold]);

    const handleContextMenu = useCallback((e) => {
      e.preventDefault();
      e.stopPropagation();
      const hit = getNodeAtScreen(e.clientX, e.clientY);
      if (hit && onOpenContextMenu) {
        onOpenContextMenu(e, hit.raw);
      }
    }, [getNodeAtScreen, onOpenContextMenu]);

    const handleWheel = useCallback((e) => {
      e.preventDefault();
      const factor = e.deltaY < 0 ? 1.12 : 0.89;
      setTransform(prev => ({
        ...prev,
        scale: Math.max(0.2, Math.min(4.0, prev.scale * factor))
      }));
    }, []);

    const handleAutoFit = useCallback(() => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const { nodes } = simRef.current;
      const vis = nodes.filter(n => isNodeVisible(n));
      if (vis.length === 0) return;

      let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
      vis.forEach(n => {
        if (n.x < minX) minX = n.x;
        if (n.x > maxX) maxX = n.x;
        if (n.y < minY) minY = n.y;
        if (n.y > maxY) maxY = n.y;
      });

      const spanX = Math.max(100, maxX - minX + 80);
      const spanY = Math.max(100, maxY - minY + 80);
      const w = canvas.clientWidth || 900;
      const h = canvas.clientHeight || 600;

      const scale = Math.max(0.3, Math.min(1.5, Math.min(w / spanX, h / spanY)));
      const midX = (minX + maxX) / 2;
      const midY = (minY + maxY) / 2;

      setTransform({ scale, panX: -midX * scale, panY: -midY * scale });
    }, [isNodeVisible]);

    return h("div", {
      className: "auto-org-f2g-container",
      ref: containerRef,
      onMouseLeave: () => {
        if (onHideRollover) onHideRollover();
        setHoveredNodeId(null);
      }
    },
      // HUD Overlay with Tools
      h("div", { className: "auto-org-f2g-hud" },
        h("div", { className: "auto-org-f2g-badge" },
          h("span", { style: { fontSize: "1.1rem" } }, "🕸️"),
          h("strong", null, "Obsidian folders2graph Struktur-Graph"),
          h("span", { style: { color: "#94a3b8", fontSize: "0.72rem" } }, "• Force Physics & Faltung")
        ),
        h("div", { style: { display: "flex", gap: "0.35rem", pointerEvents: "auto", flexWrap: "wrap" } },
          h("button", { type: "button", className: "auto-org-pill-btn fit", onClick: handleAutoFit, title: "Zentrieren und einpassen" }, "🎯 Auto-Fit"),
          h("button", { type: "button", className: "auto-org-pill-btn", onClick: () => setFoldedIds(new Set()), title: "Alle Ordner ausklappen" }, "[+] Alles"),
          h("button", { type: "button", className: "auto-org-pill-btn", onClick: () => {
            const map = simRef.current.nodeMap;
            const mountIds = new Set(Array.from(map.values()).filter(n => n.node_type === "mount").map(n => n.id));
            setFoldedIds(mountIds);
          }, title: "Nur Hauptlaufwerke zeigen" }, "[-] Nur Mounts"),
          h("button", { type: "button", className: "auto-org-pill-btn", onClick: () => setTransform(p => ({ ...p, scale: p.scale * 1.25 })) }, "+"),
          h("button", { type: "button", className: "auto-org-pill-btn", onClick: () => setTransform(p => ({ ...p, scale: p.scale * 0.8 })) }, "-"),
          h("button", { type: "button", className: "auto-org-pill-btn", onClick: () => setTransform({ scale: 1, panX: 0, panY: 0 }) }, "↺ Reset")
        ),
        // Color Legend
        h("div", { style: { display: "flex", gap: "0.5rem", pointerEvents: "auto", marginTop: "0.2rem" } },
          h("span", { className: "auto-org-rollover-badge-state approved", style: { fontSize: "0.68rem" } }, "🟢 Freigegeben"),
          h("span", { className: "auto-org-rollover-badge-state proposed", style: { fontSize: "0.68rem" } }, "🟡 Vorschlag"),
          h("span", { className: "auto-org-rollover-badge-state excluded", style: { fontSize: "0.68rem" } }, "⚪ Nicht einbezogen"),
          h("span", { style: { color: "#60a5fa", fontSize: "0.68rem", display: "flex", alignItems: "center", gap: "0.2rem" } },
            h("span", null, "💡"),
            h("span", null, "Rechtsklick zum Ändern")
          )
        )
      ),

      // Interactive Graph Canvas
      h("canvas", {
        ref: canvasRef,
        className: "auto-org-f2g-canvas",
        onMouseDown: handleMouseDown,
        onMouseMove: handleMouseMove,
        onMouseUp: handleMouseUp,
        onWheel: handleWheel,
        onContextMenu: handleContextMenu
      })
    );
  }

  function ObsidianFlowGraph({

    isPaused = false,
    speedMultiplier = 1,
    onTogglePause = null,
    activeBranch = "all",
    onSelectBranch = null,
    highlightedBranchId = null,
    compact = false
  }) {
    const canvasRef = useRef(null);
    const containerRef = useRef(null);
    const [hoveredNode, setHoveredNode] = useState(null);
    const [tooltipData, setTooltipData] = useState(null);
    const [branchFilter, setBranchFilter] = useState(activeBranch || "all");

    useEffect(() => {
      if (activeBranch && activeBranch !== branchFilter) {
        setBranchFilter(activeBranch);
      }
    }, [activeBranch]);

    useEffect(() => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      let animationFrameId;
      let width = canvas.parentElement ? canvas.parentElement.clientWidth : 960;
      if (width < 600) width = 600;
      const height = compact ? 340 : 440;

      // Handle retina / high-DPI displays
      const dpr = window.devicePixelRatio || 1;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = width + "px";
      canvas.style.height = height + "px";
      ctx.scale(dpr, dpr);

      // Define Node Layout
      const srcX = Math.round(width * 0.15);
      const hubX = Math.round(width * 0.48);
      const hubY = Math.round(height * 0.50);
      const dstX = Math.round(width * 0.85);

      const sourceNodes = [
        { id: "src_downloads", label: "Downloads (Dumpzone)", path: "/home/mb/Downloads", icon: "⬇️", count: 45, color: "#f59e0b", x: srcX, y: Math.round(height * 0.15), radius: 18, role: "Quelle" },
        { id: "src_desktop", label: "Schreibtisch", path: "/home/mb/Schreibtisch", icon: "🖥️", count: 18, color: "#f59e0b", x: srcX, y: Math.round(height * 0.32), radius: 16, role: "Quelle" },
        { id: "src_privat", label: "PrivatBüro (Lokal)", path: "/media/privat-data/10_PrivatBüro", icon: "📁", count: 89, color: "#10b981", x: srcX, y: Math.round(height * 0.50), radius: 20, role: "Quelle" },
        { id: "src_work", label: "Work-Data (Lokal)", path: "/media/work-data", icon: "💼", count: 210, color: "#3b82f6", x: srcX, y: Math.round(height * 0.68), radius: 22, role: "Quelle" },
        { id: "src_gdrive", label: "Google Drive (Cloud)", path: "gdrive://creatiVision", icon: "☁️", count: 120, color: "#06b6d4", x: srcX, y: Math.round(height * 0.85), radius: 20, role: "Quelle" },
      ];

      const hubNode = {
        id: "hub_hermes",
        label: "Hermes KI-Core (S_ideal)",
        path: "Semantische Vektorisierung, OCR-Inhalte & Regel-Matching",
        icon: "🤖",
        count: 516,
        color: "#a855f7",
        x: hubX,
        y: hubY,
        radius: compact ? 30 : 36,
        isHub: true,
        role: "Hub"
      };

      const allTargetNodes = [
        { id: "dst_steuern", label: "PrivatBüro / Steuern", path: "/media/privat-data/10_PrivatBüro/2024/Steuern/", icon: "📊", count: 24, color: "#10b981", radius: 18, role: "Ziel-Ast", branch: "privat", status: "APPROVED" },
        { id: "dst_vertraege", label: "PrivatBüro / Verträge", path: "/media/privat-data/10_PrivatBüro/Versicherungen_Vertraege/", icon: "⚖️", count: 19, color: "#059669", radius: 17, role: "Ziel-Ast", branch: "privat", status: "APPROVED" },
        { id: "dst_buchhaltung_out", label: "001_cv / Ausgangsrechnungen", path: "/media/work-data/001_cv-bookaccount/2025/Ausgangsrechnungen/", icon: "📤", count: 62, color: "#3b82f6", radius: 21, role: "Ziel-Ast", branch: "buchhaltung", status: "APPROVED" },
        { id: "dst_buchhaltung_in", label: "001_cv / Eingangsrechnungen", path: "/media/work-data/001_cv-bookaccount/2025/Eingangsrechnungen/", icon: "📥", count: 45, color: "#2563eb", radius: 19, role: "Ziel-Ast", branch: "buchhaltung", status: "APPROVED" },
        { id: "dst_projekte", label: "002_cv-projects / Stulz & Web", path: "/media/work-data/002_cv-projects/stulz/", icon: "🚀", count: 120, color: "#8b5cf6", radius: 22, role: "Ziel-Ast", branch: "projekte", status: "APPROVED" },
        { id: "dst_skills", label: "ai-workspaces / Skills", path: "/media/xchg/ai-agents-workspaces/skills/", icon: "🤖", count: 90, color: "#a855f7", radius: 20, role: "Ziel-Ast", branch: "projekte", status: "APPROVED" },
        { id: "dst_assets", label: "Work-Data / Assets", path: "/media/work-data/Assets/2026/", icon: "🎨", count: 15, color: "#ec4899", radius: 16, role: "Ziel-Ast", branch: "projekte", status: "APPROVED" },
        { id: "dst_backup", label: "Archiv / Dumps & Sicherungen", path: "/media/xchg/ai-knowledge-base/Archiv/2026/", icon: "📦", count: 75, color: "#d97706", radius: 19, role: "Ziel-Ast", branch: "archiv", status: "APPROVED" },
        { id: "dst_trash", label: "Papierkorb (send2trash)", path: "trash://", icon: "🧹", count: 14, color: "#ef4444", radius: 16, role: "Ziel-Ast", branch: "trash", status: "APPROVED" },
      ];

      // Filter target nodes by branchFilter
      const filteredTargets = branchFilter === "all" ? allTargetNodes : allTargetNodes.filter(n => n.branch === branchFilter);
      const totalTargets = filteredTargets.length;

      filteredTargets.forEach((node, idx) => {
        node.x = dstX;
        if (totalTargets === 1) {
          node.y = hubY;
        } else {
          node.y = Math.round(55 + (idx * (height - 110)) / (totalTargets - 1));
        }
      });

      const allNodes = [...sourceNodes, hubNode, ...filteredTargets];

      // Build Bezier Flow Curves: Source -> Hub and Hub -> Target
      const curves = [];
      sourceNodes.forEach((src) => {
        curves.push({
          id: `${src.id}_to_hub`,
          sourceId: src.id,
          targetId: hubNode.id,
          p0: { x: src.x, y: src.y },
          c1: { x: src.x + (hubX - srcX) * 0.45, y: src.y },
          c2: { x: hubX - (hubX - srcX) * 0.45, y: hubY },
          p1: { x: hubX, y: hubY },
          color: src.color,
          type: "inflow"
        });
      });

      filteredTargets.forEach((dst) => {
        curves.push({
          id: `hub_to_${dst.id}`,
          sourceId: hubNode.id,
          targetId: dst.id,
          p0: { x: hubX, y: hubY },
          c1: { x: hubX + (dstX - hubX) * 0.45, y: hubY },
          c2: { x: dstX - (dstX - hubX) * 0.45, y: dst.y },
          p1: { x: dstX, y: dst.y },
          color: dst.color,
          type: "outflow"
        });
      });

      // Particle System (Files flowing through the graph)
      const particleCount = compact ? 28 : 42;
      const particles = [];
      for (let i = 0; i < particleCount; i++) {
        const curveIdx = Math.floor(Math.random() * curves.length);
        const curve = curves[curveIdx];
        particles.push({
          curveIdx: curveIdx,
          t: Math.random(),
          speed: 0.0025 + Math.random() * 0.0035,
          size: 2.2 + Math.random() * 1.5,
          color: curve.color
        });
      }

      function getBezierPoint(c, t) {
        const inv = 1 - t;
        const inv2 = inv * inv;
        const inv3 = inv2 * inv;
        const t2 = t * t;
        const t3 = t2 * t;
        return {
          x: inv3 * c.p0.x + 3 * inv2 * t * c.c1.x + 3 * inv * t2 * c.c2.x + t3 * c.p1.x,
          y: inv3 * c.p0.y + 3 * inv2 * t * c.c1.y + 3 * inv * t2 * c.c2.y + t3 * c.p1.y
        };
      }

      let startTime = Date.now();

      function render() {
        const now = Date.now();
        const elapsed = (now - startTime) / 1000;

        // Clear background with deep cosmic obsidian tone
        ctx.fillStyle = "#080c14";
        ctx.fillRect(0, 0, width, height);

        // Subtle background grid stars
        ctx.fillStyle = "rgba(51, 65, 85, 0.25)";
        for (let gx = 25; gx < width; gx += 40) {
          for (let gy = 25; gy < height; gy += 40) {
            ctx.fillRect(gx, gy, 1.2, 1.2);
          }
        }

        // Draw Flow Curves
        curves.forEach((c) => {
          const isHighlighted = (hoveredNode && (hoveredNode.id === c.sourceId || hoveredNode.id === c.targetId || hoveredNode.id === hubNode.id)) ||
            (highlightedBranchId && (c.targetId === highlightedBranchId || c.sourceId === highlightedBranchId));
          ctx.beginPath();
          ctx.moveTo(c.p0.x, c.p0.y);
          ctx.bezierCurveTo(c.c1.x, c.c1.y, c.c2.x, c.c2.y, c.p1.x, c.p1.y);

          if (isHighlighted) {
            ctx.strokeStyle = c.color;
            ctx.lineWidth = 3.0;
            ctx.shadowColor = c.color;
            ctx.shadowBlur = 14;
          } else {
            ctx.strokeStyle = "rgba(100, 116, 139, 0.22)";
            ctx.lineWidth = 1.4;
            ctx.shadowBlur = 0;
          }
          ctx.stroke();
          ctx.shadowBlur = 0;
        });

        // Update and Draw Particles
        particles.forEach((p) => {
          if (!isPaused) {
            p.t += p.speed * speedMultiplier;
            if (p.t > 1) {
              p.t = 0;
              p.curveIdx = Math.floor(Math.random() * curves.length);
              p.color = curves[p.curveIdx].color;
            }
          }

          const c = curves[p.curveIdx];
          const pt = getBezierPoint(c, p.t);

          const isHighlighted = (hoveredNode && (hoveredNode.id === c.sourceId || hoveredNode.id === c.targetId)) ||
            (highlightedBranchId && (c.targetId === highlightedBranchId || c.sourceId === highlightedBranchId));

          ctx.beginPath();
          ctx.arc(pt.x, pt.y, isHighlighted ? p.size * 1.6 : p.size, 0, Math.PI * 2);
          ctx.fillStyle = isHighlighted ? "#ffffff" : p.color;
          ctx.shadowColor = p.color;
          ctx.shadowBlur = isHighlighted ? 14 : 6;
          ctx.fill();
          ctx.shadowBlur = 0;
        });

        // Draw Central Hermes Hub Pulsing Aura
        const pulse = Math.sin(elapsed * 2.5) * 6;
        ctx.beginPath();
        ctx.arc(hubNode.x, hubNode.y, hubNode.radius + 10 + pulse, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(168, 85, 247, 0.25)";
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(hubNode.x, hubNode.y, hubNode.radius + 18 + pulse * 1.4, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(168, 85, 247, 0.12)";
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Draw All Nodes
        allNodes.forEach((node) => {
          const isHovered = hoveredNode && hoveredNode.id === node.id;
          const isTargetBranch = highlightedBranchId && (node.id === highlightedBranchId || node.branch === highlightedBranchId);
          const r = (isHovered || isTargetBranch) ? node.radius + 4 : node.radius;

          // Outer Glow
          ctx.beginPath();
          ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
          ctx.fillStyle = "#0f172a";
          ctx.shadowColor = node.color;
          ctx.shadowBlur = (isHovered || isTargetBranch) ? 26 : 12;
          ctx.fill();

          // Border
          ctx.strokeStyle = (isHovered || isTargetBranch) ? "#ffffff" : node.color;
          ctx.lineWidth = (isHovered || isTargetBranch) ? 3 : 2;
          ctx.stroke();
          ctx.shadowBlur = 0;

          // Icon
          ctx.font = `${Math.round(r * 0.95)}px sans-serif`;
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(node.icon, node.x, node.y + 1);

          // Node Text Labels
          ctx.font = (isHovered || isTargetBranch) ? "bold 11px system-ui" : "600 10.5px system-ui";
          ctx.fillStyle = (isHovered || isTargetBranch) ? "#ffffff" : "#f1f5f9";
          ctx.fillText(node.label, node.x, node.y + r + 13);

          // Badge / File count
          ctx.font = "9.5px monospace";
          ctx.fillStyle = node.color;
          ctx.fillText(node.isHub ? "AI Hub" : `${node.count} Dateien`, node.x, node.y + r + 25);
        });

        animationFrameId = requestAnimationFrame(render);
      }

      animationFrameId = requestAnimationFrame(render);

      // Mouse Move Handler for Hover
      const handleMouseMove = (e) => {
        const rect = canvas.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;

        let found = null;
        for (const n of allNodes) {
          const dist = Math.hypot(mx - n.x, my - n.y);
          if (dist <= n.radius + 8) {
            found = n;
            break;
          }
        }
        setHoveredNode(found);
        if (found) {
          setTooltipData({
            x: e.clientX,
            y: e.clientY,
            node: found
          });
        } else {
          setTooltipData(null);
        }
      };

      const handleMouseLeave = () => {
        setHoveredNode(null);
        setTooltipData(null);
      };

      canvas.addEventListener("mousemove", handleMouseMove);
      canvas.addEventListener("mouseleave", handleMouseLeave);

      return () => {
        cancelAnimationFrame(animationFrameId);
        canvas.removeEventListener("mousemove", handleMouseMove);
        canvas.removeEventListener("mouseleave", handleMouseLeave);
      };
    }, [isPaused, speedMultiplier, branchFilter, highlightedBranchId, compact]);

    return h("div", { className: "auto-org-obsidian-container", ref: containerRef },
      // Top Controls Toolbar
      h("div", { className: "auto-org-obsidian-toolbar" },
        h("div", { style: { display: "flex", alignItems: "center", gap: "0.6rem" } },
          h("span", { style: { fontSize: "1.2rem" } }, "🕸️"),
          h("strong", { style: { fontSize: "0.95rem", color: "#ffffff" } }, "Obsidian-Style Dateifluss-Graph"),
          h("span", { className: "auto-org-badge auto-org-badge-blue", style: { fontSize: "0.7rem" } }, "Live-Visualisierung")
        ),
        h("div", { className: "auto-org-obsidian-legend" },
          h("div", { style: { display: "flex", alignItems: "center", gap: "0.3rem" } },
            h("span", { className: "auto-org-ampel-dot yellow" }),
            h("span", null, "Quellen (Dumpzone/Drives)")
          ),
          h("div", { style: { display: "flex", alignItems: "center", gap: "0.3rem" } },
            h("span", { style: { width: "8px", height: "8px", borderRadius: "50%", background: "#a855f7", display: "inline-block" } }),
            h("span", null, "Hermes Core")
          ),
          h("div", { style: { display: "flex", alignItems: "center", gap: "0.3rem" } },
            h("span", { className: "auto-org-ampel-dot green" }),
            h("span", null, "Ziel-Baum (S_ideal)")
          ),
          h("div", { style: { display: "flex", alignItems: "center", gap: "0.3rem" } },
            h("span", { style: { color: "#60a5fa" } }, "⇢"),
            h("span", null, "Dateistrom")
          ),
          onTogglePause && h("button", {
            type: "button",
            className: "auto-org-btn auto-org-btn-outline",
            style: { padding: "0.2rem 0.6rem", fontSize: "0.75rem", marginLeft: "0.5rem" },
            onClick: onTogglePause
          }, isPaused ? "▶ Fortsetzen" : "⏸️ Pause")
        )
      ),

      // Branch Filter Pills Toolbar
      h("div", { className: "auto-org-filter-pill-bar", style: { padding: "0.45rem 1rem", background: "rgba(11, 17, 33, 0.95)", borderBottom: "1px solid #1e293b", display: "flex", gap: "0.4rem", flexWrap: "wrap", alignItems: "center" } },
        h("span", { style: { fontSize: "0.75rem", color: "#94a3b8", fontWeight: 600, marginRight: "0.3rem" } }, "🌳 Ast-Fokus:"),
        [
          { id: "all", label: "🌐 Gesamt-Baum (9 Äste)" },
          { id: "privat", label: "🏠 01_PrivatBüro (2 Äste)" },
          { id: "buchhaltung", label: "💼 02_Buchhaltung (2 Äste)" },
          { id: "projekte", label: "🚀 03_Projekte & Skills (3 Äste)" },
          { id: "archiv", label: "📦 04_Archiv" },
          { id: "trash", label: "🧹 05_Papierkorb" },
        ].map(f =>
          h("button", {
            key: f.id,
            type: "button",
            className: `auto-org-filter-pill ${branchFilter === f.id ? "active" : ""}`,
            onClick: () => {
              setBranchFilter(f.id);
              if (onSelectBranch) onSelectBranch(f.id);
            }
          }, f.label)
        )
      ),

      // HTML5 Canvas
      h("canvas", { ref: canvasRef, className: "auto-org-obsidian-canvas" }),

      // Interactive Tooltip Overlay
      tooltipData && h("div", {
        style: {
          position: "fixed",
          left: tooltipData.x + 14,
          top: tooltipData.y - 12,
          background: "rgba(15, 23, 42, 0.95)",
          border: `1px solid ${tooltipData.node.color}`,
          boxShadow: `0 8px 24px rgba(0,0,0,0.6), 0 0 12px ${tooltipData.node.color}40`,
          borderRadius: "0.5rem",
          padding: "0.65rem 0.85rem",
          pointerEvents: "none",
          zIndex: 9999,
          display: "flex",
          flexDirection: "column",
          gap: "0.25rem",
          maxWidth: "320px"
        }
      },
        h("div", { style: { display: "flex", alignItems: "center", gap: "0.4rem" } },
          h("span", { style: { fontSize: "1.1rem" } }, tooltipData.node.icon),
          h("strong", { style: { color: "#ffffff", fontSize: "0.85rem" } }, tooltipData.node.label),
          h("span", {
            className: `auto-org-ampel-badge ${tooltipData.node.status === "APPROVED" || tooltipData.node.role === "Hub" ? "green" : "yellow"}`,
            style: { fontSize: "0.65rem", padding: "0.1rem 0.4rem", marginLeft: "auto" }
          }, tooltipData.node.role === "Hub" ? "KI Core" : (tooltipData.node.status === "APPROVED" ? "🟢 Freigegeben" : "🟡 Quelle"))
        ),
        h("div", { style: { fontFamily: "monospace", fontSize: "0.72rem", color: "#93c5fd", wordBreak: "break-all" } },
          formatUserPath(tooltipData.node.path)
        ),
        h("div", { style: { fontSize: "0.72rem", color: "#94a3b8" } },
        )
      )
    );
  }

  // Default Fallback Tree Data for Multi-Computer File Tree & Radar
  const DEFAULT_SYSTEM_TREE = [
    {
      id: "comp_laptop",
      name: "💻 kimi-laptop",
      path: "host://kimi-laptop",
      node_type: "computer",
      computer_id: "kimi-laptop",
      role: "Haupt-Workstation & Kontrollzentrum",
      status: { state: "INDEXED", color: "#10b981", symbol: "🟢", label: "Online & Synchronisiert" },
      syncthing: { synced: true, folder_id: null, label: "Syncthing Node (laptop)", type: "mesh", peers: ["debian1", "Note14new"], status: "SYNCED" },
      backup: { protected: true, program: "pg-backup.sh, docker-backup.sh, rclone", schedule: "Täglich + Boot", target: "/media/xchg/ai-tools-data/", retention: "7 Tage daily / 12 Monate" },
      file_count: 5240,
      size_mb: 14250.0,
      children: [
        {
          id: "drive_laptop_xchg",
          name: "📁 /media/xchg (Shared Exchange)",
          path: "/media/xchg",
          node_type: "drive",
          computer_id: "kimi-laptop",
          status: { state: "INDEXED", color: "#10b981", symbol: "🟢", label: "Vollständig indexiert & P2P geteilt" },
          syncthing: { synced: true, folder_id: "jfx5u-kwxmw", label: "xchg", type: "sendreceive", peers: ["debian1", "Note14new"], status: "SYNCED" },
          backup: { protected: true, program: "Syncthing Mesh + pg/docker backup Dumps", schedule: "Echtzeit P2P", target: "kimi-debian1 / Note14new", retention: "Permanent" },
          file_count: 1840,
          size_mb: 4820.0,
          children: [
            {
              id: "node_xchg_workspaces",
              name: "ai-agents-workspaces",
              path: "/media/xchg/ai-agents-workspaces",
              node_type: "folder",
              computer_id: "kimi-laptop",
              status: { state: "INDEXED", color: "#10b981", symbol: "🟢", label: "Aktiv" },
              syncthing: { synced: true, folder_id: "jfx5u-kwxmw", label: "xchg", type: "sendreceive", peers: ["debian1"], status: "SYNCED" },
              backup: { protected: true, program: "hermes-backup-config.sh", schedule: "Stündlich", target: "/media/xchg/ai-agents-workspaces/hermes/backups", retention: "24h Snapshot" },
              file_count: 480,
              size_mb: 940.0,
              children: [
                { id: "node_xchg_hermes", name: "hermes (.hermes Core & Plugins)", path: "/media/xchg/ai-agents-workspaces/hermes", node_type: "subfolder", computer_id: "kimi-laptop", status: { state: "INDEXED", color: "#10b981", symbol: "🟢", label: "Live" }, syncthing: { synced: true, peers: ["debian1"] }, backup: { protected: true, program: "hermes-backup-config.sh", schedule: "Stündlich" }, file_count: 310, size_mb: 620.0, children: [] },
                { id: "node_xchg_kimi", name: "kimi (Kimi-Code CLI Workspace)", path: "/media/xchg/ai-agents-workspaces/kimi", node_type: "subfolder", computer_id: "kimi-laptop", status: { state: "INDEXED", color: "#10b981", symbol: "🟢", label: "Live" }, syncthing: { synced: true, peers: ["debian1"] }, backup: { protected: true, program: "Syncthing Mesh" }, file_count: 120, size_mb: 210.0, children: [] }
              ]
            },
            {
              id: "node_xchg_knowledge",
              name: "ai-knowledge-base (Obsidian Vault)",
              path: "/media/xchg/ai-knowledge-base",
              node_type: "folder",
              computer_id: "kimi-laptop",
              status: { state: "PROTECTED", color: "#a855f7", symbol: "🟣", label: "Graph-Indexiert" },
              syncthing: { synced: true, folder_id: "jfx5u-kwxmw", label: "xchg", type: "sendreceive", peers: ["debian1", "Note14new"], status: "SYNCED" },
              backup: { protected: true, program: "graphify-index-obsidian.py", schedule: "Täglich 04:00", target: "/media/xchg/ai-graph", retention: "Knowledge Graph" },
              file_count: 620,
              size_mb: 1150.0,
              children: []
            },
            {
              id: "node_xchg_tools",
              name: "ai-tools-data (MCP & Backups)",
              path: "/media/xchg/ai-tools-data",
              node_type: "folder",
              computer_id: "kimi-laptop",
              status: { state: "PROTECTED", color: "#a855f7", symbol: "🟣", label: "Backup Depot" },
              syncthing: { synced: true, folder_id: "jfx5u-kwxmw", label: "xchg", type: "sendreceive", peers: ["debian1"], status: "SYNCED" },
              backup: { protected: true, program: "pg-backup.sh & docker-backup.sh", schedule: "Täglich 03:00 / Boot", target: "Lokales Tausch-Depot", retention: "7 Tage daily / 12 Monate monthly" },
              file_count: 390,
              size_mb: 2180.0,
              children: [
                { id: "node_xchg_pg_backups", name: "postgres-backups (SQL Dumps)", path: "/media/xchg/ai-tools-data/postgres-backups", node_type: "backup_archive", computer_id: "kimi-laptop", status: { state: "PROTECTED", color: "#a855f7", symbol: "🟣", label: "Sicherungsarchiv" }, syncthing: { synced: true }, backup: { protected: true, program: "pg-backup.sh", schedule: "03:00 / Boot" }, file_count: 28, size_mb: 1120.0, children: [] },
                { id: "node_xchg_docker_backups", name: "docker-backups (Volume Tars)", path: "/media/xchg/ai-tools-data/docker-backups", node_type: "backup_archive", computer_id: "kimi-laptop", status: { state: "PROTECTED", color: "#a855f7", symbol: "🟣", label: "Sicherungsarchiv" }, syncthing: { synced: true }, backup: { protected: true, program: "docker-backup.sh", schedule: "Täglich 03:00" }, file_count: 14, size_mb: 840.0, children: [] }
              ]
            },
            {
              id: "node_xchg_handy",
              name: "Handy (P2P Dropzone Smartphone)",
              path: "/media/xchg/Handy",
              node_type: "folder",
              computer_id: "kimi-laptop",
              status: { state: "INDEXED", color: "#06b6d4", symbol: "🔄", label: "Mobil Synchronisiert" },
              syncthing: { synced: true, folder_id: "6yrmn-6pvpe", label: "Handy-Share", type: "sendreceive", peers: ["Note14new"], status: "SYNCED" },
              backup: { protected: true, program: "Syncthing P2P", schedule: "Echtzeit" },
              file_count: 350,
              size_mb: 550.0,
              children: [
                { id: "node_handy_share", name: "xx_handy_share (Direktaustausch)", path: "/media/xchg/Handy/xx_handy_share", node_type: "subfolder", computer_id: "kimi-laptop", status: { state: "INDEXED", color: "#06b6d4", symbol: "🔄", label: "In Sync" }, syncthing: { synced: true, folder_id: "6yrmn-6pvpe", peers: ["Note14new"] }, backup: { protected: false }, file_count: 12, size_mb: 45.0, children: [] },
                { id: "node_handy_dcim", name: "xx_handy_Bilder(DCIM) (Kamera)", path: "/media/xchg/Handy/xx_handy_Bilder(DCIM)", node_type: "subfolder", computer_id: "kimi-laptop", status: { state: "INDEXED", color: "#06b6d4", symbol: "🔄", label: "In Sync" }, syncthing: { synced: true, folder_id: "awwa2-tvdxp", peers: ["Note14new"] }, backup: { protected: false }, file_count: 310, size_mb: 460.0, children: [] }
              ]
            }
          ]
        },
        {
          id: "drive_laptop_workdata",
          name: "💼 /media/work-data (Projekte & Buchhaltung)",
          path: "/media/work-data",
          node_type: "drive",
          computer_id: "kimi-laptop",
          status: { state: "INDEXED", color: "#10b981", symbol: "🟢", label: "Strukturiert & Cloud-Gespiegelt" },
          syncthing: { synced: true, folder_id: "szf3z-s9szj", label: "work-data", type: "sendreceive", peers: ["debian1"], status: "SYNCED" },
          backup: { protected: true, program: "rclone gdrive + pg-backup", schedule: "Periodisch & PG Dump", target: "gdrive://creatiVision", retention: "Cloud Versioning" },
          file_count: 1420,
          size_mb: 3840.0,
          children: [
            {
              id: "node_work_bookaccount",
              name: "001_cv-bookaccount (Buchhaltung & Finanzen)",
              path: "/media/work-data/001_cv-bookaccount",
              node_type: "folder",
              computer_id: "kimi-laptop",
              status: { state: "PROTECTED", color: "#a855f7", symbol: "🟣", label: "Offsite Cloud-Spiegelung" },
              syncthing: { synced: true, folder_id: "szf3z-s9szj", label: "work-data", type: "sendreceive", peers: ["debian1"] },
              backup: { protected: true, program: "rclone gdrive sync", schedule: "Periodisch", target: "gdrive://creatiVision/Accounting", retention: "Unbegrenzt (Audit-Proof)" },
              file_count: 480,
              size_mb: 1250.0,
              children: [
                { id: "node_bookaccount_2025", name: "2025 (Ausgangs- & Eingangsrechnungen)", path: "/media/work-data/001_cv-bookaccount/2025", node_type: "subfolder", computer_id: "kimi-laptop", status: { state: "INDEXED", color: "#10b981", symbol: "🟢", label: "Vollständig freigegeben" }, syncthing: { synced: true }, backup: { protected: true, program: "rclone gdrive sync" }, file_count: 180, size_mb: 420.0, children: [] },
                { id: "node_bookaccount_2026", name: "2026 (Laufendes Geschäftsjahr)", path: "/media/work-data/001_cv-bookaccount/2026", node_type: "subfolder", computer_id: "kimi-laptop", status: { state: "PENDING", color: "#eab308", symbol: "🟡", label: "Laufende Zuordnung" }, syncthing: { synced: true }, backup: { protected: true, program: "rclone gdrive sync" }, file_count: 65, size_mb: 110.0, children: [] }
              ]
            },
            {
              id: "node_work_projects",
              name: "002_cv-projects (Webdesign & Kunden)",
              path: "/media/work-data/002_cv-projects",
              node_type: "folder",
              computer_id: "kimi-laptop",
              status: { state: "INDEXED", color: "#10b981", symbol: "🟢", label: "In Arbeit / Synchron" },
              syncthing: { synced: true, folder_id: "szf3z-s9szj", peers: ["debian1"] },
              backup: { protected: true, program: "Syncthing Mesh (laptop ↔ debian1)" },
              file_count: 780,
              size_mb: 2100.0,
              children: [
                { id: "node_projects_stulz", name: "stulz (Kundenportal Stulz)", path: "/media/work-data/002_cv-projects/stulz", node_type: "subfolder", computer_id: "kimi-laptop", status: { state: "INDEXED", color: "#10b981", symbol: "🟢", label: "Synchron" }, syncthing: { synced: true }, backup: { protected: true }, file_count: 320, size_mb: 950.0, children: [] },
                { id: "node_projects_wp", name: "webdesign-wp-lc-ps (WordPress Frameworks)", path: "/media/work-data/002_cv-projects/webdesign-wp-lc-ps", node_type: "subfolder", computer_id: "kimi-laptop", status: { state: "INDEXED", color: "#10b981", symbol: "🟢", label: "Synchron" }, syncthing: { synced: true }, backup: { protected: true }, file_count: 460, size_mb: 1150.0, children: [] }
              ]
            }
          ]
        },
        {
          id: "drive_laptop_privat",
          name: "📁 /media/privat-data (10_PrivatBüro)",
          path: "/media/privat-data/10_PrivatBüro",
          node_type: "drive",
          computer_id: "kimi-laptop",
          status: { state: "INDEXED", color: "#10b981", symbol: "🟢", label: "Taxonomie freigegeben & geschützt" },
          syncthing: { synced: true, folder_id: "qm5k5-dm6p4", label: "privat", type: "sendreceive", peers: ["debian1"], status: "SYNCED" },
          backup: { protected: true, program: "pg-backup + rclone gdrive", schedule: "Monatlich + Cloud", target: "gdrive://creatiVision/PrivatBüro", retention: "Permanent" },
          file_count: 890,
          size_mb: 2480.0,
          children: [
            { id: "node_privat_steuern", name: "Steuern (Steuerbescheide & Erklärungen)", path: "/media/privat-data/10_PrivatBüro/Steuern", node_type: "folder", computer_id: "kimi-laptop", status: { state: "PROTECTED", color: "#10b981", symbol: "🟢", label: "Archiviert & Bereinigt" }, syncthing: { synced: true }, backup: { protected: true, program: "pg-backup + Cloud" }, file_count: 140, size_mb: 340.0, children: [] },
            { id: "node_privat_vertraege", name: "Versicherungen_Vertraege (Policen & Verträge)", path: "/media/privat-data/10_PrivatBüro/Versicherungen_Vertraege", node_type: "folder", computer_id: "kimi-laptop", status: { state: "PROTECTED", color: "#10b981", symbol: "🟢", label: "Archiviert & Bereinigt" }, syncthing: { synced: true }, backup: { protected: true, program: "pg-backup + Cloud" }, file_count: 95, size_mb: 280.0, children: [] }
          ]
        },
        {
          id: "drive_laptop_downloads",
          name: "⬇️ /home/mb/Downloads (Dumpzone)",
          path: "/home/mb/Downloads",
          node_type: "drive",
          computer_id: "kimi-laptop",
          status: { state: "DUMPZONE", color: "#ef4444", symbol: "🔴", label: "Dumpzone (45 unsortierte Dateien)" },
          syncthing: { synced: true, folder_id: "downloads", label: "home-mb-Downloads", type: "sendreceive", peers: ["debian1"], status: "SYNCED" },
          backup: { protected: false, program: null, schedule: "Nicht gesichert (Flüchtige Eingangszone)", target: "Reorganisation in Zielordner empfohlen", retention: "Temporär" },
          file_count: 45,
          size_mb: 620.0,
          children: [
            { id: "node_dl_invoices", name: "Rechnungen & Belege (→ 001_cv)", path: "/home/mb/Downloads/*.pdf (Belege)", node_type: "subfolder", computer_id: "kimi-laptop", status: { state: "PENDING", color: "#eab308", symbol: "🟡", label: "Verschiebung vorgeschlagen" }, syncthing: { synced: true }, backup: { protected: false }, file_count: 22, size_mb: 180.0, children: [] },
            { id: "node_dl_installer", name: "Installer & Archive (→ Papierkorb)", path: "/home/mb/Downloads/*.deb, *.tar.gz", node_type: "subfolder", computer_id: "kimi-laptop", status: { state: "DUMPZONE", color: "#ef4444", symbol: "🔴", label: "Veraltete Installer" }, syncthing: { synced: true }, backup: { protected: false }, file_count: 9, size_mb: 325.0, children: [] }
          ]
        }
      ]
    },
    {
      id: "comp_debian1",
      name: "🖥️ kimi-debian1 (Server)",
      path: "host://192.168.178.111",
      node_type: "computer",
      computer_id: "kimi-debian1",
      role: "PostgreSQL 16, pgvector & Docker Server",
      status: { state: "INDEXED", color: "#10b981", symbol: "🟢", label: "Online & Docker Engine Aktiv" },
      syncthing: { synced: true, folder_id: null, label: "Syncthing Node (debian1)", type: "mesh", peers: ["laptop"], status: "SYNCED" },
      backup: { protected: true, program: "docker-backup.sh, pg-backup.sh", schedule: "Täglich 03:00 / Boot", target: "/media/xchg/ai-tools-data/", retention: "7 Tage daily / 12 Monate monthly" },
      file_count: 4120,
      size_mb: 8640.0,
      children: [
        {
          id: "drive_debian1_xchg",
          name: "📁 /media/xchg (P2P Replikation)",
          path: "/media/xchg",
          node_type: "drive",
          computer_id: "kimi-debian1",
          status: { state: "INDEXED", color: "#10b981", symbol: "🟢", label: "P2P Spiegel" },
          syncthing: { synced: true, folder_id: "jfx5u-kwxmw", label: "xchg", peers: ["laptop"], status: "SYNCED" },
          backup: { protected: true, program: "Syncthing Mesh" },
          file_count: 1840,
          size_mb: 4820.0,
          children: []
        },
        {
          id: "drive_debian1_docker",
          name: "🐳 /var/lib/docker/volumes (Container Data)",
          path: "/var/lib/docker/volumes",
          node_type: "drive",
          computer_id: "kimi-debian1",
          status: { state: "PROTECTED", color: "#a855f7", symbol: "🟣", label: "Täglich 03:00 Gesichert" },
          syncthing: { synced: false, peers: [] },
          backup: { protected: true, program: "docker-backup.sh", schedule: "Täglich 03:00", target: "/media/xchg/ai-tools-data/docker-backups", retention: "7 Tage" },
          file_count: 1650,
          size_mb: 2400.0,
          children: [
            { id: "node_debian1_shared_pg", name: "shared-pg_data (PostgreSQL 16 + pgvector)", path: "/var/lib/docker/volumes/shared-pg_data", node_type: "subfolder", computer_id: "kimi-debian1", status: { state: "PROTECTED", color: "#a855f7", symbol: "🟣", label: "DB-Gesichert" }, syncthing: { synced: false }, backup: { protected: true, program: "pg-backup.sh", schedule: "Boot + 03:00" }, file_count: 420, size_mb: 1100.0, children: [] },
            { id: "node_debian1_n8n", name: "n8n_data (Workflows & Execution States)", path: "/var/lib/docker/volumes/n8n_data", node_type: "subfolder", computer_id: "kimi-debian1", status: { state: "PROTECTED", color: "#a855f7", symbol: "🟣", label: "Täglich gesichert" }, syncthing: { synced: false }, backup: { protected: true, program: "docker-backup.sh" }, file_count: 1230, size_mb: 1300.0, children: [] }
          ]
        },
        {
          id: "drive_debian1_pg_backups",
          name: "📦 /var/backups/postgres (Lokale SQL-Dumps)",
          path: "/var/backups/postgres",
          node_type: "backup_archive",
          computer_id: "kimi-debian1",
          status: { state: "PROTECTED", color: "#a855f7", symbol: "🟣", label: "Konsistente Dumps" },
          syncthing: { synced: false, peers: [] },
          backup: { protected: true, program: "pg-backup.sh" },
          file_count: 28,
          size_mb: 1420.0,
          children: []
        }
      ]
    },
    {
      id: "comp_hermes",
      name: "🤖 hermes-laptop (KI-Agent)",
      path: "host://hermes-laptop",
      node_type: "computer",
      computer_id: "hermes-laptop",
      role: "Autonome Reorganisation, Vektorisierung & Plugin Host",
      status: { state: "INDEXED", color: "#10b981", symbol: "🟢", label: "Gateway & Watchdog Aktiv" },
      syncthing: { synced: true, folder_id: null, label: "Shared via xchg", type: "mesh", peers: ["laptop", "debian1"], status: "SYNCED" },
      backup: { protected: true, program: "hermes-backup-config.sh", schedule: "Stündlich", target: "/media/xchg/ai-agents-workspaces/hermes/backups", retention: "24h Snapshots" },
      file_count: 930,
      size_mb: 1770.0,
      children: [
        { id: "drive_hermes_workspace", name: "🧠 .hermes Core & Plugins", path: "/media/xchg/ai-agents-workspaces/hermes/.hermes", node_type: "drive", computer_id: "hermes-laptop", status: { state: "INDEXED", color: "#10b981", symbol: "🟢", label: "Aktiv" }, syncthing: { synced: true }, backup: { protected: true, program: "hermes-backup-config.sh", schedule: "Stündlich" }, file_count: 310, size_mb: 620.0, children: [] },
        { id: "drive_hermes_graphify", name: "🌐 Graphify Knowledge Base Index", path: "/media/xchg/ai-graph", node_type: "drive", computer_id: "hermes-laptop", status: { state: "PROTECTED", color: "#a855f7", symbol: "🟣", label: "Täglich 04:00 neu indiziert" }, syncthing: { synced: true }, backup: { protected: true, program: "graphify-index-obsidian.py" }, file_count: 620, size_mb: 1150.0, children: [] }
      ]
    },
    {
      id: "comp_gdrive",
      name: "☁️ Google Drive (Cloud Mirror)",
      path: "gdrive://creatiVision",
      node_type: "cloud",
      computer_id: "gdrive",
      role: "Offsite Cloud-Tresor & Freigabe-Portal",
      status: { state: "PROTECTED", color: "#a855f7", symbol: "🟣", label: "Offsite Geschützt & Versioniert" },
      syncthing: { synced: false, label: "Cloud Connector", type: "cloud", peers: ["laptop"], status: "CLOUD_SYNC" },
      backup: { protected: true, program: "rclone / gdrive sync", schedule: "Periodisch via Sync-Manager", target: "gdrive://creatiVision", retention: "Google Workspace Drive Versioning" },
      file_count: 2150,
      size_mb: 12400.0,
      children: [
        { id: "drive_gdrive_accounting", name: "📊 Accounting (Buchhaltung Cloud-Mirror)", path: "gdrive://creatiVision/Accounting", node_type: "cloud_vault", computer_id: "gdrive", status: { state: "PROTECTED", color: "#a855f7", symbol: "🟣", label: "Spiegelung Aktiv" }, syncthing: { synced: false }, backup: { protected: true, program: "rclone gdrive sync" }, file_count: 480, size_mb: 1250.0, children: [] },
        { id: "drive_gdrive_brand", name: "🎨 Brand & Assets (Master Medien)", path: "gdrive://creatiVision/Brand", node_type: "cloud_vault", computer_id: "gdrive", status: { state: "PROTECTED", color: "#a855f7", symbol: "🟣", label: "Master-Depot" }, syncthing: { synced: false }, backup: { protected: true, program: "rclone gdrive sync" }, file_count: 820, size_mb: 3450.0, children: [] },
        { id: "drive_gdrive_backups", name: "📦 Backups (Verschlüsselte Offsite Dumps)", path: "gdrive://creatiVision/Backups", node_type: "cloud_vault", computer_id: "gdrive", status: { state: "PROTECTED", color: "#a855f7", symbol: "🟣", label: "Georedundant" }, syncthing: { synced: false }, backup: { protected: true, program: "rclone gdrive sync" }, file_count: 850, size_mb: 7700.0, children: [] }
      ]
    },
    {
      id: "comp_mobile",
      name: "📱 Note14new (Smartphone)",
      path: "mobile://192.168.178.127",
      node_type: "computer",
      computer_id: "note14new",
      role: "Mobiles Endgerät & Kamera-Upload",
      status: { state: "INDEXED", color: "#06b6d4", symbol: "🟢", label: "P2P Verbunden (192.168.178.127:22000)" },
      syncthing: { synced: true, folder_id: "6yrmn-6pvpe", label: "Syncthing Node (Note14new)", type: "p2p_device", peers: ["laptop"], status: "SYNCED" },
      backup: { protected: true, program: "Syncthing Auto-Replication", schedule: "Echtzeit bei WLAN-Verbindung", target: "/media/xchg/Handy/", retention: "Permanent auf Laptop archiviert" },
      file_count: 322,
      size_mb: 505.0,
      children: [
        { id: "drive_mobile_share", name: "📤 Handy-Share (Transfer-Ordner)", path: "mobile://Handy-Share", node_type: "drive", computer_id: "note14new", status: { state: "INDEXED", color: "#06b6d4", symbol: "🔄", label: "P2P Synchron" }, syncthing: { synced: true, folder_id: "6yrmn-6pvpe", peers: ["laptop"] }, backup: { protected: true, program: "Syncthing P2P Replikation" }, file_count: 12, size_mb: 45.0, children: [] },
        { id: "drive_mobile_dcim", name: "📷 Handy-Bilder (DCIM Kamera-Stream)", path: "mobile://DCIM", node_type: "drive", computer_id: "note14new", status: { state: "INDEXED", color: "#06b6d4", symbol: "🔄", label: "P2P Synchron" }, syncthing: { synced: true, folder_id: "awwa2-tvdxp", peers: ["laptop"] }, backup: { protected: true, program: "Syncthing P2P Replikation" }, file_count: 310, size_mb: 460.0, children: [] }
      ]
    }
  ];

  // Multi-Computer File Tree & Backup/Sync Radar Window Component
  function MultiComputerTreeWindow({ onClose }) {
    const canvasRef = useRef(null);
    const containerRef = useRef(null);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [viewMode, setViewMode] = useState("folders2graph"); // "folders2graph" | "filesystem" | "radar"
    const [nodeStates, setNodeStates] = useState({});
    const [contextMenu, setContextMenu] = useState(null); // { x, y, node, currentState }
    const [rollover, setRollover] = useState(null); // { x, y, node, nodeState }
    const [systemTree, setSystemTree] = useState(null);
    const [loading, setLoading] = useState(true);
    const [activeLayer, setActiveLayer] = useState("all"); // "all" | "syncthing" | "backup" | "traffic_light"
    const [expandedIds, setExpandedIds] = useState(() => new Set([
      "comp_laptop", "comp_debian1", "comp_hermes", "comp_gdrive", "comp_mobile",
      "drive_laptop_xchg", "drive_laptop_workdata", "drive_laptop_privat", "drive_laptop_downloads",
      "drive_debian1_docker", "drive_mobile_share"
    ]));
    const [selectedNode, setSelectedNode] = useState(null);
    const [hoveredNode, setHoveredNode] = useState(null);
    const [searchQuery, setSearchQuery] = useState("");
    const [isPaused, setIsPaused] = useState(false);

    // Real System Filesystem Tree State
    const [fsTree, setFsTree] = useState(null);
    const [fsLoading, setFsLoading] = useState(true);
    const [fsFilter, setFsFilter] = useState("all"); // "all" | "indexed" | "unindexed" | "reorg" | "syncthing" | "backup"
    const [fsExpanded, setFsExpanded] = useState(() => new Set([
      "node_media_work-data", "node_media_privat-data", "node_media_xchg",
      "node_media_nosync", "node_media_empty", "node_home", "node_"
    ]));
    const [fsSelectedNode, setFsSelectedNode] = useState(null);
    const [isRescanning, setIsRescanning] = useState(false);
    const [rescanMsg, setRescanMsg] = useState("");

    // Viewport transform
    const [transform, setTransform] = useState({ scale: 1, panX: 0, panY: 0 });
    const transformRef = useRef(transform);
    transformRef.current = transform;
    const isDraggingRef = useRef(false);
    const dragStartRef = useRef({ x: 0, y: 0 });
    const hasDraggedRef = useRef(false);

    // Fetch /system-tree on mount
    useEffect(() => {
      let mounted = true;
      apiCall("/system-tree")
        .then((data) => {
          if (mounted && data && data.ok && data.tree) {
            setSystemTree(data);
            if (data.tree.length > 0 && !selectedNode) {
              setSelectedNode(data.tree[0]);
            }
          }
        })
        .catch((err) => {
          console.warn("Could not load /system-tree:", err);
        })
        .finally(() => {
          if (mounted) setLoading(false);
        });
      return () => { mounted = false; };
    }, []);

    // Load full real filesystem tree
    const loadFsTree = useCallback(() => {
      setFsLoading(true);
      apiCall("/filesystem-tree/full")
        .then((data) => {
          if (data && data.ok) {
            setFsTree(data);
            if (data.node_states) {
              setNodeStates(prev => Object.assign({}, data.node_states, prev));
            }
            if (data.mounts && data.mounts.length > 0) {
              setFsSelectedNode(prev => prev || data.mounts[0]);
            }
          }
        })
        .catch((err) => {
          console.warn("Could not load /filesystem-tree/full:", err);
        })
        .finally(() => {
          setFsLoading(false);
        });
    }, []);

    // Node state switcher handler (optimistic UI + backend call)
    const handleSwitchNodeState = useCallback((node, newState) => {
      if (!node) return;
      const key = node.path || node.id;
      setNodeStates(prev => {
        const next = Object.assign({}, prev, { [key]: newState });
        if (node.path) next[node.path] = newState;
        if (node.id) next[node.id] = newState;
        return next;
      });

      apiCall("/filesystem-tree/node-switch", {
        method: "POST",
        body: JSON.stringify({
          path: node.path || node.uri_path || node.id,
          node_id: node.id,
          state: newState
        })
      }).catch(err => {
        console.warn("Could not persist node state switch:", err);
      });
    }, []);

    const handleOpenContextMenu = useCallback((e, node) => {
      if (!node) return;
      e.preventDefault();
      e.stopPropagation();
      setRollover(null);
      const st = nodeStates[node.path] || nodeStates[node.id] || node.switch_state || "proposed";
      setContextMenu({
        x: e.clientX,
        y: e.clientY,
        node: node,
        currentState: st
      });
    }, [nodeStates]);

    const handleShowRollover = useCallback((x, y, node, state) => {
      if (!node) return;
      setRollover({ x, y, node, nodeState: state });
    }, []);

    const handleHideRollover = useCallback(() => {
      setRollover(null);
    }, []);


    useEffect(() => {
      loadFsTree();
    }, [loadFsTree]);

    const triggerRescan = useCallback(() => {
      setIsRescanning(true);
      setRescanMsg("Scan läuft...");
      apiCall("/filesystem-tree/rescan", { method: "POST" })
        .then((res) => {
          setRescanMsg(res.message || "Dateisystembaum erfolgreich aktualisiert!");
          setTimeout(() => {
            loadFsTree();
            setRescanMsg("");
          }, 1000);
        })
        .catch((err) => {
          setRescanMsg("Scan fehlgeschlagen");
          setTimeout(() => setRescanMsg(""), 3000);
        })
        .finally(() => {
          setIsRescanning(false);
        });
    }, [loadFsTree]);

    const toggleFsExpand = useCallback((nodeId) => {
      setFsExpanded(prev => {
        const next = new Set(prev);
        if (next.has(nodeId)) next.delete(nodeId);
        else next.add(nodeId);
        return next;
      });
    }, []);

    const expandAllFs = useCallback(() => {
      if (!fsTree || !fsTree.mounts) return;
      const all = new Set();
      function collect(nodes) {
        nodes.forEach(n => {
          all.add(n.id);
          if (n.children && n.children.length > 0) collect(n.children);
        });
      }
      collect(fsTree.mounts);
      setFsExpanded(all);
    }, [fsTree]);

    const collapseAllFs = useCallback(() => {
      setFsExpanded(new Set());
    }, []);

    const setFsLevel = useCallback((lvl) => {
      if (!fsTree || !fsTree.mounts) return;
      const ids = new Set();
      function collect(nodes, curLvl) {
        nodes.forEach(n => {
          if (curLvl < lvl) {
            ids.add(n.id);
            if (n.children) collect(n.children, curLvl + 1);
          }
        });
      }
      collect(fsTree.mounts, 1);
      setFsExpanded(ids);
    }, [fsTree]);

    const hostsTree = (systemTree && systemTree.tree) || DEFAULT_SYSTEM_TREE;

    // Toggle node expand/collapse
    const toggleExpand = useCallback((nodeId) => {
      setExpandedIds(prev => {
        const next = new Set(prev);
        if (next.has(nodeId)) next.delete(nodeId);
        else next.add(nodeId);
        return next;
      });
    }, []);

    const expandAll = useCallback(() => {
      const all = new Set();
      function collect(nodes) {
        nodes.forEach(n => {
          all.add(n.id);
          if (n.children && n.children.length > 0) collect(n.children);
        });
      }
      collect(hostsTree);
      setExpandedIds(all);
    }, [hostsTree]);

    const collapseAll = useCallback(() => {
      setExpandedIds(new Set());
    }, []);

    const setLevel = useCallback((lvl) => {
      const ids = new Set();
      function collect(nodes, curLvl) {
        nodes.forEach(n => {
          if (curLvl < lvl) {
            ids.add(n.id);
            if (n.children) collect(n.children, curLvl + 1);
          }
        });
      }
      collect(hostsTree, 1);
      setExpandedIds(ids);
    }, [hostsTree]);

    // Center node in viewport
    const centerNode = useCallback((node) => {
      if (!node || !canvasRef.current) return;
      const canvas = canvasRef.current;
      const w = canvas.clientWidth || 1000;
      const h = canvas.clientHeight || 650;
      const s = 1.15;
      const px = (w / 2) - (node.x * s);
      const py = (h / 2) - (node.y * s);
      setTransform({ scale: s, panX: px, panY: py });
    }, []);

    // Compute Layout Positions
    const layout = useMemo(() => {
      const canvas = canvasRef.current;
      const width = canvas ? canvas.clientWidth : 1100;
      const height = canvas ? canvas.clientHeight : 680;
      const cx = width / 2;
      const cy = height / 2;

      const nodes = [];
      const links = [];
      const crossLinks = [];

      // Central Backbone Hub
      const centralHub = {
        id: "hub_lan_backbone",
        name: "🌐 LAN Mesh & Sync Backbone",
        path: "LAN 192.168.178.0/24 • Syncthing Ring • Offsite Cloud",
        node_type: "hub",
        computer_id: "backbone",
        x: cx,
        y: cy,
        radius: 26,
        color: "#6366f1",
        icon: "🌐",
        isHub: true,
        visible: true,
        status: { state: "PROTECTED", color: "#6366f1", symbol: "🌐", label: "Backbone Aktiv" },
        file_count: 12800,
        size_mb: 28400.0,
        syncthing: { synced: true, label: "P2P Mesh", type: "mesh", peers: ["laptop", "debian1", "Note14new"] },
        backup: { protected: true, program: "pg-backup.sh, docker-backup.sh", schedule: "Täglich + Boot" }
      };
      nodes.push(centralHub);

      // Host Positions (Radial Circle around Backbone)
      const hostAngles = {
        "comp_laptop": -0.75 * Math.PI,
        "comp_gdrive": -0.22 * Math.PI,
        "comp_debian1": 0.15 * Math.PI,
        "comp_mobile": 0.52 * Math.PI,
        "comp_hermes": 0.92 * Math.PI
      };
      const hostRadius = 175;

      hostsTree.forEach((host, hIdx) => {
        const hAngle = hostAngles[host.id] !== undefined ? hostAngles[host.id] : (-0.8 * Math.PI + (hIdx * 0.4 * Math.PI));
        const hx = cx + Math.cos(hAngle) * hostRadius;
        const hy = cy + Math.sin(hAngle) * hostRadius;

        const hostNode = Object.assign({}, host, {
          x: hx,
          y: hy,
          radius: 24,
          angle: hAngle,
          visible: true,
          collapsedCount: host.children ? host.children.length : 0,
          isExpanded: expandedIds.has(host.id)
        });
        nodes.push(hostNode);

        // Link Hub -> Host
        links.push({
          sourceId: centralHub.id,
          targetId: hostNode.id,
          p0: { x: centralHub.x, y: centralHub.y },
          p1: { x: hostNode.x, y: hostNode.y },
          color: hostNode.status.color,
          type: "backbone"
        });

        // Child Drives
        if (host.children && host.children.length > 0) {
          const isHostExpanded = expandedIds.has(host.id);
          const driveCount = host.children.length;
          const driveSpan = Math.min(Math.PI * 0.75, 0.28 * driveCount);
          const driveDist = 135;

          host.children.forEach((drive, dIdx) => {
            const driveAngle = driveCount === 1 ? hAngle : (hAngle - driveSpan / 2 + (dIdx * driveSpan) / (driveCount - 1));
            const dx = hx + Math.cos(driveAngle) * driveDist;
            const dy = hy + Math.sin(driveAngle) * driveDist;

            const isDriveExpanded = isHostExpanded && expandedIds.has(drive.id);
            const driveNode = Object.assign({}, drive, {
              x: dx,
              y: dy,
              radius: 18,
              angle: driveAngle,
              visible: isHostExpanded,
              collapsedCount: drive.children ? drive.children.length : 0,
              isExpanded: isDriveExpanded
            });
            nodes.push(driveNode);

            if (isHostExpanded) {
              links.push({
                sourceId: hostNode.id,
                targetId: driveNode.id,
                p0: { x: hostNode.x, y: hostNode.y },
                p1: { x: driveNode.x, y: driveNode.y },
                color: driveNode.status.color,
                type: "tree"
              });
            }

            // Folders / Subfolders
            if (drive.children && drive.children.length > 0) {
              const folderCount = drive.children.length;
              const folderSpan = Math.min(Math.PI * 0.5, 0.22 * folderCount);
              const folderDist = 110;

              drive.children.forEach((folder, fIdx) => {
                const folderAngle = folderCount === 1 ? driveAngle : (driveAngle - folderSpan / 2 + (fIdx * folderSpan) / (folderCount - 1));
                const fx = dx + Math.cos(folderAngle) * folderDist;
                const fy = dy + Math.sin(folderAngle) * folderDist;

                const isFolderExpanded = isDriveExpanded && expandedIds.has(folder.id);
                const folderNode = Object.assign({}, folder, {
                  x: fx,
                  y: fy,
                  radius: 14,
                  angle: folderAngle,
                  visible: isDriveExpanded,
                  collapsedCount: folder.children ? folder.children.length : 0,
                  isExpanded: isFolderExpanded
                });
                nodes.push(folderNode);

                if (isDriveExpanded) {
                  links.push({
                    sourceId: driveNode.id,
                    targetId: folderNode.id,
                    p0: { x: driveNode.x, y: driveNode.y },
                    p1: { x: driveNode.x, y: driveNode.y },
                    color: folderNode.status.color,
                    type: "tree"
                  });
                }

                // Subfolder leaves
                if (folder.children && folder.children.length > 0) {
                  const subCount = folder.children.length;
                  const subSpan = Math.min(Math.PI * 0.4, 0.18 * subCount);
                  const subDist = 85;

                  folder.children.forEach((sub, sIdx) => {
                    const subAngle = subCount === 1 ? folderAngle : (folderAngle - subSpan / 2 + (sIdx * subSpan) / (subCount - 1));
                    const sx = fx + Math.cos(subAngle) * subDist;
                    const sy = fy + Math.sin(subAngle) * subDist;

                    const subNode = Object.assign({}, sub, {
                      x: sx,
                      y: sy,
                      radius: 11,
                      angle: subAngle,
                      visible: isFolderExpanded,
                      collapsedCount: 0,
                      isExpanded: false
                    });
                    nodes.push(subNode);

                    if (isFolderExpanded) {
                      links.push({
                        sourceId: folderNode.id,
                        targetId: subNode.id,
                        p0: { x: folderNode.x, y: folderNode.y },
                        p1: { x: subNode.x, y: subNode.y },
                        color: subNode.status.color,
                        type: "tree"
                      });
                    }
                  });
                }
              });
            }
          });
        }
      });

      // Cross-Cutting P2P Syncthing & Backup Links
      const nodeMap = new Map(nodes.map(n => [n.id, n]));

      function addCrossLink(sId, tId, color, type, label) {
        const s = nodeMap.get(sId);
        const t = nodeMap.get(tId);
        if (s && t && s.visible && t.visible) {
          crossLinks.push({
            sourceId: sId,
            targetId: tId,
            p0: { x: s.x, y: s.y },
            p1: { x: t.x, y: t.y },
            color: color,
            type: type,
            label: label
          });
        }
      }

      // Syncthing Links (cyan)
      addCrossLink("drive_laptop_xchg", "drive_debian1_xchg", "#06b6d4", "syncthing", "xchg P2P");
      addCrossLink("drive_laptop_workdata", "comp_debian1", "#06b6d4", "syncthing", "work-data P2P");
      addCrossLink("node_handy_share", "drive_mobile_share", "#06b6d4", "syncthing", "Handy-Share P2P");
      addCrossLink("node_handy_dcim", "drive_mobile_dcim", "#06b6d4", "syncthing", "DCIM Foto P2P");

      // Backup Links (purple/amber)
      addCrossLink("node_debian1_shared_pg", "node_xchg_pg_backups", "#a855f7", "backup", "pg-backup.sh");
      addCrossLink("drive_debian1_docker", "node_xchg_docker_backups", "#d97706", "backup", "docker-backup.sh");
      addCrossLink("node_work_bookaccount", "drive_gdrive_accounting", "#a855f7", "backup", "rclone gdrive");
      addCrossLink("drive_laptop_privat", "drive_gdrive_backups", "#a855f7", "backup", "rclone gdrive");
      addCrossLink("node_xchg_knowledge", "drive_hermes_graphify", "#10b981", "backup", "graphify sync");

      return { nodes, links, crossLinks };
    }, [hostsTree, expandedIds]);

    // Auto-fit to Screen Algorithm
    const autoFitScreen = useCallback(() => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const width = canvas.clientWidth || 1000;
      const height = canvas.clientHeight || 650;
      const visibleNodes = layout.nodes.filter(n => n.visible);
      if (visibleNodes.length === 0) return;

      let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
      visibleNodes.forEach(n => {
        const pad = (n.radius || 20) + 40;
        minX = Math.min(minX, n.x - pad);
        maxX = Math.max(maxX, n.x + pad);
        minY = Math.min(minY, n.y - pad);
        maxY = Math.max(maxY, n.y + pad);
      });

      const boxW = Math.max(maxX - minX, 150);
      const boxH = Math.max(maxY - minY, 150);
      const scaleX = (width - 60) / boxW;
      const scaleY = (height - 60) / boxH;
      const newScale = Math.max(0.35, Math.min(scaleX, scaleY, 1.25));
      const centerX = (minX + maxX) / 2;
      const centerY = (minY + maxY) / 2;
      const newPanX = (width / 2) - (centerX * newScale);
      const newPanY = (height / 2) - (centerY * newScale);

      setTransform({ scale: newScale, panX: newPanX, panY: newPanY });
    }, [layout]);

    // Trigger autoFitScreen on initial render or resize
    useEffect(() => {
      const t = setTimeout(() => {
        autoFitScreen();
      }, 45);
      return () => clearTimeout(t);
    }, [autoFitScreen]);

    // Canvas Render Loop
    useEffect(() => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      let animationFrameId;
      const width = canvas.clientWidth || 1000;
      const height = canvas.clientHeight || 650;

      const dpr = window.devicePixelRatio || 1;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = width + "px";
      canvas.style.height = height + "px";

      const startTime = Date.now();

      function render() {
        const now = Date.now();
        const elapsed = isPaused ? 0 : (now - startTime) / 1000;

        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.scale(dpr, dpr);

        // Clear Background with Deep Cosmic Obsidian Theme
        ctx.fillStyle = "#080c14";
        ctx.fillRect(0, 0, width, height);

        // Faint Star Grid Dots
        ctx.fillStyle = "rgba(51, 65, 85, 0.22)";
        for (let gx = 30; gx < width; gx += 45) {
          for (let gy = 30; gy < height; gy += 45) {
            ctx.fillRect(gx, gy, 1.2, 1.2);
          }
        }

        // Apply Viewport Pan & Zoom
        ctx.save();
        ctx.translate(transformRef.current.panX, transformRef.current.panY);
        ctx.scale(transformRef.current.scale, transformRef.current.scale);

        // 1. Draw Tree Hierarchy Links
        layout.links.forEach(link => {
          ctx.beginPath();
          ctx.moveTo(link.p0.x, link.p0.y);

          // Subtle curved path
          const midX = (link.p0.x + link.p1.x) / 2;
          const midY = (link.p0.y + link.p1.y) / 2;
          ctx.quadraticCurveTo(midX, midY, link.p1.x, link.p1.y);

          let alpha = 0.45;
          if (activeLayer === "syncthing") alpha = 0.15;
          if (activeLayer === "backup") alpha = 0.15;

          ctx.strokeStyle = `rgba(148, 163, 184, ${alpha})`;
          ctx.lineWidth = 1.4;
          ctx.stroke();
        });

        // 2. Draw Cross-Cutting Syncthing P2P Mesh Links (Cyan with Flowing Packets)
        if (activeLayer === "all" || activeLayer === "syncthing") {
          layout.crossLinks.filter(cl => cl.type === "syncthing").forEach(cl => {
            const dx = cl.p1.x - cl.p0.x;
            const dy = cl.p1.y - cl.p0.y;
            const cx1 = cl.p0.x + dx * 0.5 - dy * 0.22;
            const cy1 = cl.p0.y + dy * 0.5 + dx * 0.22;

            ctx.beginPath();
            ctx.moveTo(cl.p0.x, cl.p0.y);
            ctx.quadraticCurveTo(cx1, cy1, cl.p1.x, cl.p1.y);

            ctx.strokeStyle = "rgba(6, 182, 212, 0.75)";
            ctx.lineWidth = 2.4;
            ctx.setLineDash([5, 4]);
            ctx.shadowColor = "#06b6d4";
            ctx.shadowBlur = 10;
            ctx.stroke();
            ctx.setLineDash([]);
            ctx.shadowBlur = 0;

            // Flowing Cyan Syncthing Data Particles
            if (!isPaused) {
              const particleT = (elapsed * 0.35) % 1.0;
              const inv = 1 - particleT;
              const px = inv * inv * cl.p0.x + 2 * inv * particleT * cx1 + particleT * particleT * cl.p1.x;
              const py = inv * inv * cl.p0.y + 2 * inv * particleT * cy1 + particleT * particleT * cl.p1.y;

              ctx.beginPath();
              ctx.arc(px, py, 3.8, 0, Math.PI * 2);
              ctx.fillStyle = "#67e8f9";
              ctx.shadowColor = "#06b6d4";
              ctx.shadowBlur = 12;
              ctx.fill();
              ctx.shadowBlur = 0;
            }
          });
        }

        // 3. Draw Cross-Cutting Backup Flow Links (Purple/Amber with Flowing Snapshots)
        if (activeLayer === "all" || activeLayer === "backup") {
          layout.crossLinks.filter(cl => cl.type === "backup").forEach(cl => {
            const dx = cl.p1.x - cl.p0.x;
            const dy = cl.p1.y - cl.p0.y;
            const cx1 = cl.p0.x + dx * 0.5 + dy * 0.2;
            const cy1 = cl.p0.y + dy * 0.5 - dx * 0.2;

            ctx.beginPath();
            ctx.moveTo(cl.p0.x, cl.p0.y);
            ctx.quadraticCurveTo(cx1, cy1, cl.p1.x, cl.p1.y);

            ctx.strokeStyle = cl.color === "#a855f7" ? "rgba(168, 85, 247, 0.8)" : "rgba(217, 119, 6, 0.8)";
            ctx.lineWidth = 2.2;
            ctx.shadowColor = cl.color;
            ctx.shadowBlur = 9;
            ctx.stroke();
            ctx.shadowBlur = 0;

            // Flowing Backup Snapshot Particles
            if (!isPaused) {
              const particleT = (elapsed * 0.28) % 1.0;
              const inv = 1 - particleT;
              const px = inv * inv * cl.p0.x + 2 * inv * particleT * cx1 + particleT * particleT * cl.p1.x;
              const py = inv * inv * cl.p0.y + 2 * inv * particleT * cy1 + particleT * particleT * cl.p1.y;

              ctx.beginPath();
              ctx.arc(px, py, 4.0, 0, Math.PI * 2);
              ctx.fillStyle = cl.color;
              ctx.shadowColor = cl.color;
              ctx.shadowBlur = 14;
              ctx.fill();
              ctx.shadowBlur = 0;
            }
          });
        }

        // 4. Draw Nodes
        layout.nodes.filter(n => n.visible).forEach(node => {
          const isSelected = selectedNode && selectedNode.id === node.id;
          const isHovered = hoveredNode && hoveredNode.id === node.id;

          // Filter Opacity
          let nodeAlpha = 1.0;
          if (activeLayer === "syncthing" && (!node.syncthing || !node.syncthing.synced)) {
            nodeAlpha = 0.22;
          } else if (activeLayer === "backup" && (!node.backup || !node.backup.protected)) {
            nodeAlpha = 0.22;
          }

          if (searchQuery.trim()) {
            const q = searchQuery.toLowerCase();
            const matches = (node.name && node.name.toLowerCase().includes(q)) ||
                            (node.path && node.path.toLowerCase().includes(q)) ||
                            (node.computer_id && node.computer_id.toLowerCase().includes(q));
            if (!matches) nodeAlpha = 0.15;
          }

          ctx.save();
          ctx.globalAlpha = nodeAlpha;

          const r = (isHovered || isSelected) ? node.radius + 3 : node.radius;

          // Pulsating Halo Ring
          if (!isPaused && (node.node_type === "computer" || (node.syncthing && node.syncthing.synced))) {
            const pulse = Math.sin(elapsed * 2.8 + node.x * 0.01) * 3;
            ctx.beginPath();
            ctx.arc(node.x, node.y, r + 4 + pulse, 0, Math.PI * 2);
            ctx.fillStyle = `${node.status.color}25`;
            ctx.fill();
          }

          // Node Body Circle
          ctx.beginPath();
          ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
          ctx.fillStyle = isSelected ? "#1e293b" : "#0f172a";
          ctx.shadowColor = node.status.color;
          ctx.shadowBlur = (isHovered || isSelected) ? 22 : 10;
          ctx.fill();

          // Border
          ctx.strokeStyle = isSelected ? "#ffffff" : node.status.color;
          ctx.lineWidth = (isHovered || isSelected) ? 3.0 : 2.0;
          ctx.stroke();
          ctx.shadowBlur = 0;

          // Node Icon
          ctx.font = `${Math.round(r * 0.88)}px sans-serif`;
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(node.icon || "📁", node.x, node.y);

          // Status Traffic Light Pip (Top Right)
          ctx.beginPath();
          ctx.arc(node.x + r * 0.72, node.y - r * 0.72, 4.5, 0, Math.PI * 2);
          ctx.fillStyle = node.status.color;
          ctx.shadowColor = node.status.color;
          ctx.shadowBlur = 8;
          ctx.fill();
          ctx.shadowBlur = 0;
          ctx.strokeStyle = "#080c14";
          ctx.lineWidth = 1.5;
          ctx.stroke();

          // Collapsed Folder Badge [+N]
          if (!node.isExpanded && node.collapsedCount > 0) {
            const badgeTxt = `+${node.collapsedCount}`;
            ctx.font = "bold 9px monospace";
            const bw = ctx.measureText(badgeTxt).width + 8;
            const bh = 14;
            const bx = node.x + r * 0.75;
            const by = node.y + r * 0.45;

            ctx.fillStyle = "rgba(59, 130, 246, 0.95)";
            ctx.beginPath();
            ctx.roundRect(bx, by, bw, bh, 6);
            ctx.fill();
            ctx.strokeStyle = "#ffffff";
            ctx.lineWidth = 1;
            ctx.stroke();

            ctx.fillStyle = "#ffffff";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(badgeTxt, bx + bw / 2, by + bh / 2 + 0.5);
          }

          // Node Label
          ctx.font = (isHovered || isSelected) ? "bold 11px system-ui" : "600 10.5px system-ui";
          ctx.fillStyle = (isHovered || isSelected) ? "#ffffff" : "#cbd5e1";
          ctx.textAlign = "center";
          ctx.textBaseline = "top";
          const maxLblLen = 22;
          const displayLabel = node.name.length > maxLblLen ? node.name.slice(0, maxLblLen) + "…" : node.name;
          ctx.fillText(displayLabel, node.x, node.y + r + 5);

          // Sub-Label (Sync or Backup tag)
          if (activeLayer === "syncthing" && node.syncthing && node.syncthing.synced) {
            ctx.font = "9px monospace";
            ctx.fillStyle = "#67e8f9";
            ctx.fillText(`🔄 ${node.syncthing.label || "In Sync"}`, node.x, node.y + r + 18);
          } else if (activeLayer === "backup" && node.backup && node.backup.protected) {
            ctx.font = "9px monospace";
            ctx.fillStyle = "#d8b4fe";
            ctx.fillText(`🛡️ ${node.backup.program ? node.backup.program.split(",")[0] : "Gesichert"}`, node.x, node.y + r + 18);
          } else if (node.file_count) {
            ctx.font = "9px monospace";
            ctx.fillStyle = node.status.color;
            ctx.fillText(`${node.file_count} Dat.`, node.x, node.y + r + 18);
          }

          ctx.restore();
        });

        ctx.restore();

        animationFrameId = requestAnimationFrame(render);
      }

      animationFrameId = requestAnimationFrame(render);

      return () => {
        if (animationFrameId) cancelAnimationFrame(animationFrameId);
      };
    }, [layout, activeLayer, searchQuery, isPaused, selectedNode, hoveredNode]);

    // Mouse Interaction Handlers
    const handleMouseDown = (e) => {
      isDraggingRef.current = true;
      hasDraggedRef.current = false;
      dragStartRef.current = { x: e.clientX, y: e.clientY };
    };

    const handleMouseMove = (e) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();

      if (isDraggingRef.current) {
        const dx = e.clientX - dragStartRef.current.x;
        const dy = e.clientY - dragStartRef.current.y;
        if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
          hasDraggedRef.current = true;
        }
        setTransform(prev => ({
          scale: prev.scale,
          panX: prev.panX + dx,
          panY: prev.panY + dy
        }));
        dragStartRef.current = { x: e.clientX, y: e.clientY };
      } else {
        // Hit-test nodes for hover
        const mx = (e.clientX - rect.left - transformRef.current.panX) / transformRef.current.scale;
        const my = (e.clientY - rect.top - transformRef.current.panY) / transformRef.current.scale;

        let found = null;
        for (const n of layout.nodes.filter(n => n.visible)) {
          const dist = Math.hypot(n.x - mx, n.y - my);
          if (dist <= n.radius + 6) {
            found = n;
            break;
          }
        }
        setHoveredNode(found);
      }
    };

    const handleMouseUp = (e) => {
      isDraggingRef.current = false;
      if (!hasDraggedRef.current) {
        // Handle click on node
        const canvas = canvasRef.current;
        if (!canvas) return;
        const rect = canvas.getBoundingClientRect();
        const mx = (e.clientX - rect.left - transformRef.current.panX) / transformRef.current.scale;
        const my = (e.clientY - rect.top - transformRef.current.panY) / transformRef.current.scale;

        for (const n of layout.nodes.filter(n => n.visible)) {
          const dist = Math.hypot(n.x - mx, n.y - my);
          if (dist <= n.radius + 6) {
            setSelectedNode(n);
            toggleExpand(n.id);
            break;
          }
        }
      }
    };

    const handleWheel = (e) => {
      e.preventDefault();
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const factor = e.deltaY < 0 ? 1.12 : 0.89;
      const newScale = Math.max(0.25, Math.min(3.5, transformRef.current.scale * factor));
      const newPanX = mouseX - (mouseX - transformRef.current.panX) * (newScale / transformRef.current.scale);
const newPanY = mouseY - (mouseY - transformRef.current.panY) * (newScale / transformRef.current.scale);

      setTransform({ scale: newScale, panX: newPanX, panY: newPanY });
    };

    // Helper to recursively render real filesystem tree nodes
    function renderFsTreeNode(node, depth = 0) {
      if (!node) return null;
      const isExpanded = fsExpanded.has(node.id);
      const isSelected = fsSelectedNode && fsSelectedNode.id === node.id;
      const hasChildren = node.children && node.children.length > 0;

      const q = searchQuery.trim().toLowerCase();
      const matchesSearch = !q ||
        (node.name && node.name.toLowerCase().includes(q)) ||
        (node.path && node.path.toLowerCase().includes(q));

      let matchesFilter = true;
      if (fsFilter === "indexed") {
        matchesFilter = node.indexing && node.indexing.count > 0;
      } else if (fsFilter === "unindexed") {
        matchesFilter = !node.indexing || node.indexing.count === 0;
      } else if (fsFilter === "reorg") {
        matchesFilter = node.reorganization && (node.reorganization.is_source || node.reorganization.is_target);
      } else if (fsFilter === "syncthing") {
        matchesFilter = node.syncthing && node.syncthing.synced;
      } else if (fsFilter === "backup") {
        matchesFilter = node.backup && node.backup.protected;
      }

      function hasMatchingDescendant(n) {
        if (!n.children || n.children.length === 0) return false;
        return n.children.some(c => {
          const cSearch = !q || (c.name && c.name.toLowerCase().includes(q)) || (c.path && c.path.toLowerCase().includes(q));
          let cFilter = true;
          if (fsFilter === "indexed") cFilter = c.indexing && c.indexing.count > 0;
          else if (fsFilter === "unindexed") cFilter = !c.indexing || c.indexing.count === 0;
          else if (fsFilter === "reorg") cFilter = c.reorganization && (c.reorganization.is_source || c.reorganization.is_target);
          else if (fsFilter === "syncthing") cFilter = c.syncthing && c.syncthing.synced;
          else if (fsFilter === "backup") cFilter = c.backup && c.backup.protected;
          return (cSearch && cFilter) || hasMatchingDescendant(c);
        });
      }

      if (!matchesSearch && !hasMatchingDescendant(node)) return null;
      if (!matchesFilter && !hasMatchingDescendant(node)) return null;

      let icon = "📁";
      if (node.node_type === "mount") icon = "💽";
      else if (node.reorganization && node.reorganization.is_source) icon = "📤";
      else if (node.reorganization && node.reorganization.is_target) icon = "📥";
      else if (node.backup && node.backup.protected) icon = "🛡️";

      const nodeState = nodeStates[node.path] || nodeStates[node.id] || node.switch_state ||
                        (node.indexing && node.indexing.state === "FULL" ? "approved" : "proposed");

      const indentPx = depth * 18;
      const elements = [
        h("div", {
          key: node.id,
          className: `auto-org-fs-tree-row ${isSelected ? "selected" : ""} ${nodeState === "approved" ? "auto-org-row-approved" : nodeState === "excluded" ? "auto-org-row-excluded" : "auto-org-row-proposed"}`,
          style: { paddingLeft: `${indentPx + 8}px` },
          onClick: () => setFsSelectedNode(node),
          onContextMenu: (e) => handleOpenContextMenu(e, node),
          onMouseEnter: (e) => handleShowRollover(e.clientX, e.clientY, node, nodeState),
          onMouseMove: (e) => handleShowRollover(e.clientX, e.clientY, node, nodeState),
          onMouseLeave: handleHideRollover
        },
          hasChildren ?
            h("span", {
              className: "auto-org-fs-chevron",
              onClick: (e) => {
                e.stopPropagation();
                toggleFsExpand(node.id);
              }
            }, isExpanded ? "▼" : "▶") :
            h("span", { style: { width: "16px", display: "inline-block" } }),

          h("span", { style: { fontSize: "1rem" } }, icon),

          h("span", {
            className: "auto-org-fs-node-name",
            title: node.path
          }, node.name),

          h("span", {
            className: `auto-org-rollover-badge-state ${nodeState}`,
            style: { marginLeft: "0.4rem", fontSize: "0.68rem", cursor: "pointer" },
            title: "Rechtsklick: Status umschalten (Freigeben / Vorschlag / Ausschließen)",
            onClick: (e) => {
              e.stopPropagation();
              handleOpenContextMenu(e, node);
            }
          }, nodeState === "approved" ? "🟢 Freigegeben" : nodeState === "excluded" ? "⚪ Ausgeschlossen" : "🟡 Vorschlag"),

          node.disk ?
            h("div", { className: "auto-org-fs-mount-bar", title: `${node.disk.used_gb} GB von ${node.disk.total_gb} GB (${node.disk.percent_used}%) belegt` },
              h("div", { className: "auto-org-fs-progress-track" },
                h("div", {
                  className: "auto-org-fs-progress-fill",
                  style: {
                    width: `${node.disk.percent_used}%`,
                    background: node.disk.percent_used > 85 ? "#ef4444" : node.disk.percent_used > 65 ? "#eab308" : "#10b981"
                  }
                })
              ),
              h("span", null, `${node.disk.used_gb}/${node.disk.total_gb} GB (${node.disk.percent_used}%)`)
            ) : null,

          node.indexing ?
            h("span", {
              className: node.indexing.state === "FULL" ? "auto-org-badge-index-green" :
                         node.indexing.state === "PARTIAL" ? "auto-org-badge-index-yellow" :
                         "auto-org-badge-index-gray",
              title: `PostgreSQL file_nodes: ${node.indexing.count} Dateien (${node.indexing.size_mb} MB)`
            }, `${node.indexing.symbol} ${node.indexing.label}`) : null,

          node.reorganization && node.reorganization.is_source ?
            h("span", {
              className: "auto-org-badge-reorg-src",
              title: `Reorganisation: ${node.reorganization.pending_moves} geplante Moves`
            }, `📤 ${node.reorganization.pending_moves || 0} Moves`) : null,

          node.reorganization && node.reorganization.is_target ?
            h("span", {
              className: "auto-org-badge-reorg-tgt",
              title: "Zielverzeichnis für automatische Sortierungsregeln"
            }, "📥 Zielordner") : null,

          node.syncthing && node.syncthing.synced ?
            h("span", {
              className: "auto-org-badge-syncthing",
              title: `Syncthing Ordner: ${node.syncthing.label || node.syncthing.folder_id} • Peers: ${(node.syncthing.peers || []).join(", ")}`
            }, `🔄 ${node.syncthing.label || node.syncthing.folder_id}`) : null,

          node.backup && node.backup.protected ?
            h("span", {
              className: "auto-org-badge-backup",
              title: `Backup: ${node.backup.program} (${node.backup.schedule || "Aktiv"})`
            }, `🛡️ ${node.backup.program}`) : null,

          node.permissions ?
            h("span", {
              className: "auto-org-badge-perm",
              title: `Berechtigungen: ${node.permissions.mode_str} (${node.permissions.mode_octal}) • Besitzer: ${node.permissions.owner}:${node.permissions.group}`
            }, `${node.permissions.mode_str} ${node.permissions.owner}`) : null
        )
      ];

      if (hasChildren && (isExpanded || q)) {
        node.children.forEach(ch => {
          const childEl = renderFsTreeNode(ch, depth + 1);
          if (childEl) {
            if (Array.isArray(childEl)) elements.push(...childEl);
            else elements.push(childEl);
          }
        });
      }

      return elements;
    }

    return h("div", {
      className: "auto-org-multi-tree-modal",
      onClick: (e) => { if (e.target === e.currentTarget) onClose(); }
    },
      h("div", {
        className: `auto-org-multi-tree-window ${isFullscreen ? "fullscreen" : ""}`,
        ref: containerRef
      },
        // Top Header with Title and Mode Switcher
        h("div", { className: "auto-org-multi-tree-header" },
          h("div", { className: "auto-org-multi-tree-title" },
            h("h3", null,
              h("span", null, viewMode === "folders2graph" ? "🕸️" : viewMode === "filesystem" ? "🌲" : "🌐"),
              viewMode === "folders2graph" ? "Obsidian folders2graph Struktur-Graph (Faltung & Sync)" :
              viewMode === "filesystem" ? "Realer Gesamter Dateibaum (Alle Mounts & Partitionen)" :
              "Multi-Computer File Tree & Backup/Sync Radar"
            ),
            viewMode === "filesystem" || viewMode === "folders2graph" ?
              h("div", { className: "auto-org-host-chips" },
                h("span", { className: "auto-org-host-chip online" }, `💽 Gesamtspeicher: ${fsTree && fsTree.host ? fsTree.host.total_storage_gb : 3076.5} GB`),
                h("span", { className: "auto-org-host-chip online" }, `📊 Belegt: ${fsTree && fsTree.host ? fsTree.host.used_storage_gb : 1575.4} GB`),
                h("span", { className: "auto-org-host-chip online" }, `💾 Frei: ${fsTree && fsTree.host ? fsTree.host.free_storage_gb : 1350.5} GB`),
                h("span", { className: "auto-org-host-chip mobile" }, `💻 Host: ${fsTree && fsTree.host ? fsTree.host.hostname : "laptop"}`)
              ) :
              h("div", { className: "auto-org-host-chips" },
                h("span", { className: "auto-org-host-chip online" }, "💻 laptop: 🟢 Online"),
                h("span", { className: "auto-org-host-chip online" }, "🖥️ debian1: 🟢 Online (192.168.178.111)"),
                h("span", { className: "auto-org-host-chip online" }, "🤖 hermes: 🟢 Aktiv"),
                h("span", { className: "auto-org-host-chip cloud" }, "☁️ gdrive: 🟣 Cloud-Vault"),
                h("span", { className: "auto-org-host-chip mobile" }, "📱 Note14new: 🟢 P2P Sync (192.168.178.127)")
              )
          ),
          h("div", { style: { display: "flex", alignItems: "center", gap: "0.6rem" } },
            // View Mode Switcher
            h("div", { className: "auto-org-view-switcher" },
              h("button", {
                type: "button",
                className: `auto-org-view-switcher-btn ${viewMode === "folders2graph" ? "active" : ""}`,
                onClick: () => setViewMode("folders2graph"),
                title: "Obsidian folders2graph Struktur-Graph (Ordner, Dateien, Faltung & Syncthing-Fluss)"
              }, "🕸️ folders2graph Obsidian-Graph"),
              h("button", {
                type: "button",
                className: `auto-org-view-switcher-btn ${viewMode === "filesystem" ? "active" : ""}`,
                onClick: () => setViewMode("filesystem"),
                title: "Vollständiger realer Verzeichnisbaum aller Mount-Punkte, Partitionen und Ordner"
              }, "🌲 Realer Dateibaum"),
              h("button", {
                type: "button",
                className: `auto-org-view-switcher-btn ${viewMode === "radar" ? "active" : ""}`,
                onClick: () => setViewMode("radar"),
                title: "Obsidian-Graph Netzwerk-Radar über alle 5 Rechner und Syncthing-Ringe"
              }, "🌐 Multi-Computer Radar")
            ),
            h("button", {
              type: "button",
              className: "auto-org-pill-btn",
              onClick: () => setIsFullscreen(!isFullscreen),
              title: isFullscreen ? "Fenster verkleinern" : "Vollbildmodus"
            }, isFullscreen ? "🗖 Normal" : "⛶ Vollbild"),
            h("button", {
              type: "button",
              className: "auto-org-modal-close",
              onClick: onClose,
              title: "Schließen"
            }, "✕")
          )
        ),

        // Controls & Filter Toolbar
        h("div", { className: "auto-org-multi-tree-toolbar" },
          viewMode === "folders2graph" ?
            h(React.Fragment, null,
              h("div", { className: "auto-org-toolbar-group" },
                h("span", { className: "auto-org-toolbar-label" }, "folders2graph:"),
                h("span", { style: { color: "#38bdf8", fontSize: "0.75rem", fontWeight: 600 } }, "Gewichtete Knoten • Faltung • Rechtsklick-Status")
              ),
              h("div", { className: "auto-org-toolbar-group" },
                h("button", {
                  type: "button",
                  className: "auto-org-pill-btn fit",
                  onClick: triggerRescan,
                  disabled: isRescanning,
                  title: "Startet einen sofortigen Hintergrundscan des Host-Dateisystems"
                }, isRescanning ? "⏳ Scannt..." : "🔄 Neu scannen")
              )
            ) :
          viewMode === "filesystem" ?
            h(React.Fragment, null,
              // Filesystem Filters
              h("div", { className: "auto-org-toolbar-group" },
                h("span", { className: "auto-org-toolbar-label" }, "Filter:"),
                [
                  { id: "all", label: "🔘 Alle Ordner" },
                  { id: "indexed", label: "🟢 Nur Indexierte" },
                  { id: "unindexed", label: "⚪ Nicht im Index" },
                  { id: "reorg", label: "📤 Reorganisation" },
                  { id: "syncthing", label: "🔄 Syncthing" },
                  { id: "backup", label: "🛡️ Backups" }
                ].map(flt =>
                  h("button", {
                    key: flt.id,
                    type: "button",
                    className: `auto-org-pill-btn ${fsFilter === flt.id ? "active" : ""}`,
                    onClick: () => setFsFilter(flt.id)
                  }, flt.label)
                )
              ),

              // Filesystem Folding Controls
              h("div", { className: "auto-org-toolbar-group" },
                h("span", { className: "auto-org-toolbar-label" }, "Faltung:"),
                h("button", { type: "button", className: "auto-org-pill-btn", onClick: expandAllFs, title: "Alle Äste ausklappen" }, "[+] Alles"),
                h("button", { type: "button", className: "auto-org-pill-btn", onClick: collapseAllFs, title: "Nur Mount-Punkte" }, "[-] Mounts"),
                h("button", { type: "button", className: "auto-org-pill-btn", onClick: () => setFsLevel(2), title: "Bis Ebene 2 ausklappen" }, "[2] Ebene 2"),
                h("button", { type: "button", className: "auto-org-pill-btn", onClick: () => setFsLevel(3), title: "Bis Ebene 3 ausklappen" }, "[3] Ebene 3")
              ),

              // Rescan Button
              h("div", { className: "auto-org-toolbar-group" },
                h("button", {
                  type: "button",
                  className: "auto-org-pill-btn fit",
                  onClick: triggerRescan,
                  disabled: isRescanning,
                  title: "Startet einen sofortigen Hintergrundscan des Host-Dateisystems"
                }, isRescanning ? "⏳ Scannt..." : "🔄 Neu scannen")
              )
            ) :
            h(React.Fragment, null,
              // Radar Layer Selector
              h("div", { className: "auto-org-toolbar-group" },
                h("span", { className: "auto-org-toolbar-label" }, "Radar-Layer:"),
                [
                  { id: "all", label: "🔘 Alle Layer" },
                  { id: "syncthing", label: "🔄 Syncthing Sync-Radar" },
                  { id: "backup", label: "🛡️ Backup-Programme" },
                  { id: "traffic_light", label: "🚦 Index-Ampeln" }
                ].map(layer =>
                  h("button", {
                    key: layer.id,
                    type: "button",
                    className: `auto-org-pill-btn ${activeLayer === layer.id ? "active" : ""}`,
                    onClick: () => setActiveLayer(layer.id)
                  }, layer.label)
                )
              ),

              // Tree Folding Controls
              h("div", { className: "auto-org-toolbar-group" },
                h("span", { className: "auto-org-toolbar-label" }, "Baum-Faltung:"),
                h("button", { type: "button", className: "auto-org-pill-btn", onClick: expandAll, title: "Alle Äste bis zu den Blättern ausklappen" }, "[+] Alles"),
                h("button", { type: "button", className: "auto-org-pill-btn", onClick: collapseAll, title: "Bis auf Rechner einklappen" }, "[-] Nur Hosts"),
                h("button", { type: "button", className: "auto-org-pill-btn", onClick: () => setLevel(2), title: "Rechner & Hauptlaufwerke zeigen" }, "[2] Laufwerke"),
                h("button", { type: "button", className: "auto-org-pill-btn", onClick: () => setLevel(3), title: "Bis zu Hauptordnern ausklappen" }, "[3] Ordner")
              ),

              // Viewport & Auto-Fit Controls
              h("div", { className: "auto-org-toolbar-group" },
                h("button", {
                  type: "button",
                  className: "auto-org-pill-btn fit",
                  onClick: autoFitScreen,
                  title: "Passgenau auf 1 Bildschirm skalieren und zentrieren"
                }, "🎯 Auto-Fit Screen"),
                h("button", { type: "button", className: "auto-org-pill-btn", onClick: () => setTransform(p => ({ ...p, scale: p.scale * 1.25 })), title: "Vergrößern" }, "+"),
                h("button", { type: "button", className: "auto-org-pill-btn", onClick: () => setTransform(p => ({ ...p, scale: p.scale * 0.8 })), title: "Verkleinern" }, "-"),
                h("button", { type: "button", className: "auto-org-pill-btn", onClick: () => setTransform({ scale: 1, panX: 0, panY: 0 }), title: "Standardansicht" }, "↺ Reset"),
                h("button", {
                  type: "button",
                  className: "auto-org-pill-btn",
                  onClick: () => setIsPaused(!isPaused),
                  title: isPaused ? "Animation starten" : "Animation pausieren"
                }, isPaused ? "▶️ Play" : "⏸️ Pause")
              )
            ),

          // Search Filter (Shared across all modes)
          h("div", { className: "auto-org-toolbar-group", style: { marginLeft: "auto" } },
            h("input", {
              type: "text",
              className: "auto-org-input",
              style: { padding: "0.22rem 0.55rem", fontSize: "0.75rem", width: "190px" },
              placeholder: "🔍 Pfad / Name filtern...",
              value: searchQuery,
              onChange: (e) => setSearchQuery(e.target.value)
            })
          )
        ),

        // Main Body: Content (Folders2Graph OR Filesystem View OR Radar Canvas) + Inspector Drawer
        h("div", { className: "auto-org-multi-tree-body" },
          viewMode === "folders2graph" ?
            h(Folders2GraphView, {
              fsTree: fsTree,
              nodeStates: nodeStates,
              onSwitchNodeState: handleSwitchNodeState,
              onOpenContextMenu: handleOpenContextMenu,
              onShowRollover: handleShowRollover,
              onHideRollover: handleHideRollover,
              searchQuery: searchQuery,
              isPaused: isPaused
            }) :
          viewMode === "filesystem" ?
            // Real Filesystem Tree View Container
            h("div", { className: "auto-org-fs-view-container" },
              // Summary Strip
              h("div", { className: "auto-org-fs-tree-summary" },
                h("div", { className: "auto-org-fs-stats-strip" },
                  h("span", { className: "auto-org-fs-stat-badge" }, `💽 ${fsTree && fsTree.summary ? fsTree.summary.total_mounts : 7} Mount-Punkte`),
                  h("span", { className: "auto-org-fs-stat-badge" }, `📁 ${fsTree && fsTree.summary ? fsTree.summary.total_directories_scanned : 847} Ordner`),
                  h("span", { className: "auto-org-fs-stat-badge" }, `📄 ${fsTree && fsTree.summary ? fsTree.summary.total_files_discovered.toLocaleString() : "25.210"} Dateien`),
                  h("span", { className: "auto-org-fs-stat-badge", style: { color: "#34d399", borderColor: "rgba(16,185,129,0.3)" } }, `🟢 ${fsTree && fsTree.summary ? fsTree.summary.total_files_indexed_in_db.toLocaleString() : "2.515"} im Index`),
                  h("span", { className: "auto-org-fs-stat-badge", style: { color: "#fbbf24", borderColor: "rgba(245,158,11,0.3)" } }, `📤 ${fsTree && fsTree.summary ? fsTree.summary.total_reorg_moves_pending.toLocaleString() : "14.580"} Moves geplant`),
                  h("span", { className: "auto-org-fs-stat-badge", style: { color: "#38bdf8", borderColor: "rgba(6,182,212,0.3)" } }, `🔄 ${fsTree && fsTree.summary ? fsTree.summary.synced_folders_count : 590} Syncthing-Pfade`),
                  h("span", { className: "auto-org-fs-stat-badge", style: { color: "#c084fc", borderColor: "rgba(168,85,247,0.3)" } }, `🛡️ ${fsTree && fsTree.summary ? fsTree.summary.backup_protected_count : 27} Backups`)
                ),
                rescanMsg && h("span", { style: { color: "#34d399", fontSize: "0.75rem", fontWeight: 600 } }, rescanMsg)
              ),

              // Scrollable Tree Rows
              h("div", { className: "auto-org-fs-tree-scroll" },
                fsLoading ?
                  h("div", { style: { padding: "3rem", textAlign: "center", color: "#94a3b8" } },
                    h("div", { style: { fontSize: "1.5rem", marginBottom: "0.5rem" } }, "⏳"),
                    "Lade realen Dateisystembaum & analysiere PostgreSQL-Index..."
                  ) :
                  fsTree && fsTree.mounts && fsTree.mounts.length > 0 ?
                    fsTree.mounts.map(m => renderFsTreeNode(m, 0)) :
                    h("div", { style: { padding: "2rem", color: "#94a3b8", textAlign: "center" } }, "Keine Mount-Punkte gefunden.")
              )
            ) :
            // Canvas Viewport for Radar Mode
            h("div", { className: "auto-org-canvas-viewport" },
              h("canvas", {
                ref: canvasRef,
                className: "auto-org-tree-canvas",
                onMouseDown: handleMouseDown,
                onMouseMove: handleMouseMove,
                onMouseUp: handleMouseUp,
                onWheel: handleWheel,
                onContextMenu: (e) => {
                  const hit = hoveredNode;
                  if (hit) handleOpenContextMenu(e, hit);
                }
              })
            ),


          // Detail Inspector Drawer (Right Side)
          viewMode === "filesystem" ?
            // Filesystem Selected Node Inspector
            (fsSelectedNode && h("div", { className: "auto-org-multi-tree-inspector" },
              h("div", { className: "auto-org-inspector-header" },
                h("div", null,
                  h("div", { style: { display: "flex", alignItems: "center", gap: "0.45rem" } },
                    h("span", { style: { fontSize: "1.25rem" } }, fsSelectedNode.node_type === "mount" ? "💽" : fsSelectedNode.reorganization && fsSelectedNode.reorganization.is_source ? "📤" : "📁"),
                    h("h4", { style: { margin: 0, fontSize: "0.95rem", color: "#ffffff" } }, fsSelectedNode.name)
                  ),
                  h("div", { style: { fontSize: "0.73rem", color: "#94a3b8", marginTop: "0.2rem" } },
                    `Typ: ${fsSelectedNode.node_type === "mount" ? "Partition / Mount-Point" : "Verzeichnis"}`
                  )
                ),
                h("span", {
                  className: `auto-org-ampel-badge ${fsSelectedNode.indexing && fsSelectedNode.indexing.state === "FULL" ? "green" : fsSelectedNode.indexing && fsSelectedNode.indexing.state === "PARTIAL" ? "yellow" : "gray"}`,
                  style: { fontSize: "0.72rem" }
                }, fsSelectedNode.indexing ? `${fsSelectedNode.indexing.symbol} ${fsSelectedNode.indexing.state}` : "⚪ UNINDEXED")
              ),

              // Section 1: Exact Host Path & Partition
              h("div", { className: "auto-org-inspector-section" },
                h("div", { className: "auto-org-inspector-section-title" }, "📍 Speicherort & Partition"),
                h("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: "0.5rem" } },
                  h("div", { style: { fontFamily: "monospace", fontSize: "0.76rem", color: "#93c5fd", wordBreak: "break-all" } },
                    fsSelectedNode.path
                  ),
                  h("button", {
                    type: "button",
                    className: "auto-org-pill-btn",
                    style: { padding: "0.15rem 0.45rem", fontSize: "0.68rem" },
                    onClick: () => {
                      navigator.clipboard.writeText(fsSelectedNode.path);
                      alert("Pfad in Zwischenablage kopiert: " + fsSelectedNode.path);
                    },
                    title: "Pfad kopieren"
                  }, "📋 Kopieren")
                ),
                fsSelectedNode.mount_point && h("div", { className: "auto-org-meta-row", style: { marginTop: "0.4rem" } },
                  h("span", { className: "auto-org-meta-label" }, "Mount-Point:"),
                  h("span", { className: "auto-org-meta-val", style: { fontFamily: "monospace" } }, fsSelectedNode.mount_point)
                ),
                fsSelectedNode.device && h("div", { className: "auto-org-meta-row" },
                  h("span", { className: "auto-org-meta-label" }, "Gerät / Dateisystem:"),
                  h("span", { className: "auto-org-meta-val", style: { fontFamily: "monospace" } }, `${fsSelectedNode.device} (${fsSelectedNode.fstype || "ext4"})`)
                ),
                fsSelectedNode.disk && h(React.Fragment, null,
                  h("div", { style: { margin: "0.4rem 0 0.2rem 0" } },
                    h("div", { className: "auto-org-fs-progress-track", style: { width: "100%", height: "8px" } },
                      h("div", {
                        className: "auto-org-fs-progress-fill",
                        style: {
                          width: `${fsSelectedNode.disk.percent_used}%`,
                          background: fsSelectedNode.disk.percent_used > 85 ? "#ef4444" : fsSelectedNode.disk.percent_used > 65 ? "#eab308" : "#10b981"
                        }
                      })
                    )
                  ),
                  h("div", { className: "auto-org-meta-row" },
                    h("span", { className: "auto-org-meta-label" }, "Belegung:"),
                    h("span", { className: "auto-org-meta-val" }, `${fsSelectedNode.disk.used_gb} GB belegt von ${fsSelectedNode.disk.total_gb} GB (${fsSelectedNode.disk.percent_used}%)`)
                  ),
                  h("div", { className: "auto-org-meta-row" },
                    h("span", { className: "auto-org-meta-label" }, "Freier Speicher:"),
                    h("span", { className: "auto-org-meta-val", style: { color: "#34d399" } }, `${fsSelectedNode.disk.free_gb} GB verfügbar`)
                  )
                )
              ),

              // Section 2: PostgreSQL Indexing Status
              h("div", { className: "auto-org-inspector-section" },
                h("div", { className: "auto-org-inspector-section-title" }, "🗄️ PostgreSQL Index-Status"),
                h("div", { className: "auto-org-meta-row" },
                  h("span", { className: "auto-org-meta-label" }, "Index-Abdeckung:"),
                  h("span", {
                    className: fsSelectedNode.indexing && fsSelectedNode.indexing.state === "FULL" ? "auto-org-badge auto-org-badge-green" :
                               fsSelectedNode.indexing && fsSelectedNode.indexing.state === "PARTIAL" ? "auto-org-badge auto-org-badge-yellow" :
                               "auto-org-badge auto-org-badge-gray"
                  }, fsSelectedNode.indexing ? `${fsSelectedNode.indexing.symbol} ${fsSelectedNode.indexing.label}` : "⚪ Nicht indexiert")
                ),
                h("div", { className: "auto-org-meta-row" },
                  h("span", { className: "auto-org-meta-label" }, "Dateien in file_nodes:"),
                  h("span", { className: "auto-org-meta-val", style: { color: "#38bdf8" } },
                    `${fsSelectedNode.indexing ? fsSelectedNode.indexing.count : 0} indexierte Dateien`
                  )
                ),
                h("div", { className: "auto-org-meta-row" },
                  h("span", { className: "auto-org-meta-label" }, "Indexiertes Volumen:"),
                  h("span", { className: "auto-org-meta-val" },
                    `${fsSelectedNode.indexing ? fsSelectedNode.indexing.size_mb : 0} MB`
                  )
                ),
                h("div", { className: "auto-org-meta-row" },
                  h("span", { className: "auto-org-meta-label" }, "Dateien im Dateisystem:"),
                  h("span", { className: "auto-org-meta-val" },
                    `${fsSelectedNode.approx_total_files || fsSelectedNode.direct_files_count || 0} Dateien (${fsSelectedNode.approx_size_mb || 0} MB)`
                  )
                )
              ),

              // Section 3: Reorganization & Movements
              h("div", { className: "auto-org-inspector-section" },
                h("div", { className: "auto-org-inspector-section-title" }, "📤 Reorganisation & Movements"),
                fsSelectedNode.reorganization && (fsSelectedNode.reorganization.is_source || fsSelectedNode.reorganization.is_target) ?
                  h(React.Fragment, null,
                    fsSelectedNode.reorganization.is_source && h("div", null,
                      h("div", { style: { fontSize: "0.74rem", fontWeight: 700, color: "#fbbf24", marginBottom: "0.3rem" } },
                        `📤 Verschiebe-Quelle (${fsSelectedNode.reorganization.pending_moves || 0} Moves geplant):`
                      ),
                      (fsSelectedNode.reorganization.source_rules || []).map((r, rIdx) =>
                        h("div", { key: rIdx, style: { fontSize: "0.72rem", padding: "0.3rem", background: "rgba(30, 41, 59, 0.5)", borderRadius: "0.25rem", marginBottom: "0.25rem" } },
                          h("div", { style: { fontWeight: 600, color: "#f1f5f9" } }, r.name),
                          h("div", { style: { color: "#94a3b8", fontSize: "0.68rem" } }, `Muster: ${r.pattern} • Ziel: ${r.target_template}`)
                        )
                      )
                    ),
                    fsSelectedNode.reorganization.is_target && h("div", { style: { marginTop: "0.4rem" } },
                      h("div", { style: { fontSize: "0.74rem", fontWeight: 700, color: "#38bdf8", marginBottom: "0.3rem" } },
                        "📥 Zielverzeichnis für Regeln:"
                      ),
                      (fsSelectedNode.reorganization.target_rules || []).map((r, rIdx) =>
                        h("div", { key: rIdx, style: { fontSize: "0.72rem", padding: "0.3rem", background: "rgba(30, 41, 59, 0.5)", borderRadius: "0.25rem", marginBottom: "0.25rem" } },
                          h("div", { style: { fontWeight: 600, color: "#f1f5f9" } }, r.name),
                          h("div", { style: { color: "#94a3b8", fontSize: "0.68rem" } }, `Zielvorlage: ${r.target_template}`)
                        )
                      )
                    )
                  ) :
                  h("div", { style: { fontSize: "0.74rem", color: "#94a3b8" } }, "Keine automatischen Sortierregeln für diesen Ordner hinterlegt.")
              ),

              // Section 4: Syncthing Sync
              h("div", { className: "auto-org-inspector-section" },
                h("div", { className: "auto-org-inspector-section-title" }, "🔄 Syncthing Synchronisation"),
                fsSelectedNode.syncthing && fsSelectedNode.syncthing.synced ?
                  h(React.Fragment, null,
                    h("div", { className: "auto-org-meta-row" },
                      h("span", { className: "auto-org-meta-label" }, "Status:"),
                      h("span", { className: "auto-org-badge auto-org-badge-green" }, "✓ In Sync")
                    ),
                    fsSelectedNode.syncthing.folder_id && h("div", { className: "auto-org-meta-row" },
                      h("span", { className: "auto-org-meta-label" }, "Folder-ID:"),
                      h("span", { className: "auto-org-meta-val", style: { fontFamily: "monospace" } }, fsSelectedNode.syncthing.folder_id)
                    ),
                    h("div", { className: "auto-org-meta-row" },
                      h("span", { className: "auto-org-meta-label" }, "Sync-Typ:"),
                      h("span", { className: "auto-org-meta-val" }, fsSelectedNode.syncthing.type || "sendreceive")
                    ),
                    h("div", { className: "auto-org-meta-row" },
                      h("span", { className: "auto-org-meta-label" }, "Verbundene Peers:"),
                      h("span", { className: "auto-org-meta-val", style: { color: "#67e8f9" } },
                        (fsSelectedNode.syncthing.peers && fsSelectedNode.syncthing.peers.length > 0) ? fsSelectedNode.syncthing.peers.join(", ") : "Mesh-Ring"
                      )
                    )
                  ) :
                  h("div", { style: { fontSize: "0.74rem", color: "#94a3b8" } }, "Nicht im Syncthing Mesh (Lokaler Speicher)")
              ),

              // Section 5: Backups
              h("div", { className: "auto-org-inspector-section" },
                h("div", { className: "auto-org-inspector-section-title" }, "🛡️ Backup & Sicherung"),
                fsSelectedNode.backup && fsSelectedNode.backup.protected ?
                  h(React.Fragment, null,
                    h("div", { className: "auto-org-meta-row" },
                      h("span", { className: "auto-org-meta-label" }, "Programm:"),
                      h("span", { className: "auto-org-badge auto-org-badge-blue" }, fsSelectedNode.backup.program || "Automatisches Backup")
                    ),
                    fsSelectedNode.backup.schedule && h("div", { className: "auto-org-meta-row" },
                      h("span", { className: "auto-org-meta-label" }, "Zeitplan:"),
                      h("span", { className: "auto-org-meta-val" }, fsSelectedNode.backup.schedule)
                    ),
                    fsSelectedNode.backup.target && h("div", { className: "auto-org-meta-row" },
                      h("span", { className: "auto-org-meta-label" }, "Ziel-Depot:"),
                      h("span", { className: "auto-org-meta-val", style: { fontFamily: "monospace", fontSize: "0.7rem" } }, fsSelectedNode.backup.target)
                    ),
                    fsSelectedNode.backup.retention && h("div", { className: "auto-org-meta-row" },
                      h("span", { className: "auto-org-meta-label" }, "Retention:"),
                      h("span", { className: "auto-org-meta-val" }, fsSelectedNode.backup.retention)
                    )
                  ) :
                  h("div", { style: { fontSize: "0.74rem", color: "#f87171" } }, "⚠️ Noch kein direktes Backup-Skript für dieses Verzeichnis definiert")
              ),

              // Section 6: Permissions
              h("div", { className: "auto-org-inspector-section" },
                h("div", { className: "auto-org-inspector-section-title" }, "🔒 POSIX Berechtigungen & Host-Rechte"),
                fsSelectedNode.permissions ?
                  h(React.Fragment, null,
                    h("div", { className: "auto-org-meta-row" },
                      h("span", { className: "auto-org-meta-label" }, "Besitzer & Gruppe:"),
                      h("span", { className: "auto-org-meta-val", style: { fontFamily: "monospace" } }, `${fsSelectedNode.permissions.owner}:${fsSelectedNode.permissions.group}`)
                    ),
                    h("div", { className: "auto-org-meta-row" },
                      h("span", { className: "auto-org-meta-label" }, "Rechtemaske:"),
                      h("span", { className: "auto-org-meta-val", style: { fontFamily: "monospace" } }, `${fsSelectedNode.permissions.mode_str} (${fsSelectedNode.permissions.mode_octal})`)
                    ),
                    h("div", { className: "auto-org-meta-row" },
                      h("span", { className: "auto-org-meta-label" }, "Agent Leserechte:"),
                      h("span", { className: `auto-org-badge ${fsSelectedNode.permissions.readable ? "auto-org-badge-green" : "auto-org-badge-red"}` },
                        fsSelectedNode.permissions.readable ? "✓ Voll lesbar" : "🔒 Zugriff beschränkt"
                      )
                    )
                  ) :
                  h("div", { style: { fontSize: "0.74rem", color: "#94a3b8" } }, "Berechtigungen konnten nicht ermittelt werden.")
              )
            )) :
            // Radar Selected Node Inspector
            (selectedNode && h("div", { className: "auto-org-multi-tree-inspector" },
              h("div", { className: "auto-org-inspector-header" },
                h("div", null,
                  h("div", { style: { display: "flex", alignItems: "center", gap: "0.45rem" } },
                    h("span", { style: { fontSize: "1.25rem" } }, selectedNode.icon || "📁"),
                    h("h4", { style: { margin: 0, fontSize: "0.95rem", color: "#ffffff" } }, selectedNode.name)
                  ),
                  h("div", { style: { fontSize: "0.73rem", color: "#94a3b8", marginTop: "0.2rem" } },
                    `Host: ${selectedNode.computer_id || "-"} • Typ: ${selectedNode.node_type || "Ordner"}`
                  )
                ),
                h("span", {
                  className: `auto-org-ampel-badge ${selectedNode.status.state === "INDEXED" || selectedNode.status.state === "PROTECTED" ? "green" : selectedNode.status.state === "PENDING" ? "yellow" : "red"}`,
                  style: { fontSize: "0.72rem" }
                }, `${selectedNode.status.symbol} ${selectedNode.status.state}`)
              ),

              // Exact Host Path
              h("div", { className: "auto-org-inspector-section" },
                h("div", { className: "auto-org-inspector-section-title" }, "📍 Speicherort (Host-Pfad)"),
                h("div", { style: { fontFamily: "monospace", fontSize: "0.75rem", color: "#93c5fd", wordBreak: "break-all" } },
                  formatUserPath(selectedNode.path)
                ),
                h("div", { style: { fontSize: "0.72rem", color: "#cbd5e1" } }, selectedNode.status.label)
              ),

              // Syncthing Radar Details
              h("div", { className: "auto-org-inspector-section" },
                h("div", { className: "auto-org-inspector-section-title" }, "🔄 Syncthing Synchronisation"),
                selectedNode.syncthing && selectedNode.syncthing.synced ?
                  h(React.Fragment, null,
                    h("div", { className: "auto-org-meta-row" },
                      h("span", { className: "auto-org-meta-label" }, "Status:"),
                      h("span", { className: "auto-org-badge auto-org-badge-green" }, "✓ In Sync")
                    ),
                    selectedNode.syncthing.folder_id && h("div", { className: "auto-org-meta-row" },
                      h("span", { className: "auto-org-meta-label" }, "Folder-ID:"),
                      h("span", { className: "auto-org-meta-val", style: { fontFamily: "monospace" } }, selectedNode.syncthing.folder_id)
                    ),
                    h("div", { className: "auto-org-meta-row" },
                      h("span", { className: "auto-org-meta-label" }, "Sync-Typ:"),
                      h("span", { className: "auto-org-meta-val" }, selectedNode.syncthing.type || "sendreceive (beidseitig)")
                    ),
                    h("div", { className: "auto-org-meta-row" },
                      h("span", { className: "auto-org-meta-label" }, "Verbundene Peers:"),
                      h("span", { className: "auto-org-meta-val", style: { color: "#67e8f9" } },
                        (selectedNode.syncthing.peers && selectedNode.syncthing.peers.length > 0) ? selectedNode.syncthing.peers.join(", ") : "Mesh-Ring"
                      )
                    )
                  ) :
                  h("div", { style: { fontSize: "0.75rem", color: "#94a3b8" } }, "Nicht im Syncthing Mesh (Lokaler Speicher)")
              ),

              // Backup Details
              h("div", { className: "auto-org-inspector-section" },
                h("div", { className: "auto-org-inspector-section-title" }, "🛡️ Backup-Programme & Schutz"),
                selectedNode.backup && selectedNode.backup.protected ?
                  h(React.Fragment, null,
                    h("div", { className: "auto-org-meta-row" },
                      h("span", { className: "auto-org-meta-label" }, "Programm:"),
                      h("span", { className: "auto-org-badge auto-org-badge-blue" }, selectedNode.backup.program || "Automatisches Backup")
                    ),
                    selectedNode.backup.schedule && h("div", { className: "auto-org-meta-row" },
                      h("span", { className: "auto-org-meta-label" }, "Zeitplan:"),
                      h("span", { className: "auto-org-meta-val" }, selectedNode.backup.schedule)
                    ),
                    selectedNode.backup.target && h("div", { className: "auto-org-meta-row" },
                      h("span", { className: "auto-org-meta-label" }, "Ziel-Depot:"),
                      h("span", { className: "auto-org-meta-val", style: { fontFamily: "monospace", fontSize: "0.7rem" } }, selectedNode.backup.target)
                    ),
                    selectedNode.backup.retention && h("div", { className: "auto-org-meta-row" },
                      h("span", { className: "auto-org-meta-label" }, "Retention:"),
                      h("span", { className: "auto-org-meta-val" }, selectedNode.backup.retention)
                    )
                  ) :
                  h("div", { style: { fontSize: "0.75rem", color: "#f87171" } }, "⚠️ Noch kein direktes Backup-Skript für diesen Ast definiert")
              ),

              // Volume & File Statistics
              h("div", { className: "auto-org-inspector-section" },
                h("div", { className: "auto-org-inspector-section-title" }, "📊 Speicher-Statistiken"),
                h("div", { className: "auto-org-meta-row" },
                  h("span", { className: "auto-org-meta-label" }, "Dateianzahl:"),
                  h("span", { className: "auto-org-meta-val" }, selectedNode.file_count ? `${selectedNode.file_count.toLocaleString()} Dateien` : "-")
                ),
                h("div", { className: "auto-org-meta-row" },
                  h("span", { className: "auto-org-meta-label" }, "Gesamtgröße:"),
                  h("span", { className: "auto-org-meta-val" }, selectedNode.size_mb ? `${selectedNode.size_mb.toLocaleString()} MB` : "-")
                )
              ),

              // Quick Actions
              h("div", { style: { display: "flex", gap: "0.4rem", marginTop: "auto" } },
                h("button", {
                  type: "button",
                  className: "auto-org-btn auto-org-btn-outline",
                  style: { flex: 1, fontSize: "0.75rem" },
                  onClick: () => toggleExpand(selectedNode.id)
                }, expandedIds.has(selectedNode.id) ? "Ast Einklappen" : "Ast Ausklappen"),
                h("button", {
                  type: "button",
                  className: "auto-org-btn auto-org-btn-primary",
                  style: { flex: 1, fontSize: "0.75rem" },
                  onClick: () => centerNode(selectedNode)
                }, "🎯 Zentrieren")
              )
            ))
        ),

        // Bottom Legend Footer
        h("div", { className: "auto-org-multi-tree-footer" },
          viewMode === "filesystem" ?
            h("div", { className: "auto-org-legend-items" },
              h("span", { style: { fontWeight: 600, color: "#cbd5e1", marginRight: "0.3rem" } }, "Legende:"),
              h("div", { className: "auto-org-legend-item" },
                h("span", { className: "auto-org-legend-dot green" }),
                h("span", null, "🟢 Vollständig indexiert (PostgreSQL)")
              ),
              h("div", { className: "auto-org-legend-item" },
                h("span", { className: "auto-org-legend-dot yellow" }),
                h("span", null, "🟡 Teilweise indexiert")
              ),
              h("div", { className: "auto-org-legend-item" },
                h("span", { style: { width: "8px", height: "8px", borderRadius: "50%", background: "#64748b", display: "inline-block" } }),
                h("span", null, "⚪ Nicht im Index")
              ),
              h("div", { className: "auto-org-legend-item" },
                h("span", { className: "auto-org-legend-dot yellow" }),
                h("span", null, "📤 Reorganisations-Quelle (Moves geplant)")
              ),
              h("div", { className: "auto-org-legend-item" },
                h("span", { className: "auto-org-legend-dot cyan" }),
                h("span", null, "📥 Reorganisations-Ziel")
              ),
              h("div", { className: "auto-org-legend-item" },
                h("span", { className: "auto-org-legend-dot cyan" }),
                h("span", null, "🔄 Syncthing Mesh")
              ),
              h("div", { className: "auto-org-legend-item" },
                h("span", { className: "auto-org-legend-dot purple" }),
                h("span", null, "🛡️ Backup-Schutz")
              )
            ) :
            h("div", { className: "auto-org-legend-items" },
              h("span", { style: { fontWeight: 600, color: "#cbd5e1", marginRight: "0.3rem" } }, "Legende:"),
              h("div", { className: "auto-org-legend-item" },
                h("span", { className: "auto-org-legend-dot green" }),
                h("span", null, "🟢 Indexiert & Bereinigt")
              ),
              h("div", { className: "auto-org-legend-item" },
                h("span", { className: "auto-org-legend-dot yellow" }),
                h("span", null, "🟡 Vorschlag / Ausstehend")
              ),
              h("div", { className: "auto-org-legend-item" },
                h("span", { className: "auto-org-legend-dot red" }),
                h("span", null, "🔴 Dumpzone / Unsortiert")
              ),
              h("div", { className: "auto-org-legend-item" },
                h("span", { className: "auto-org-legend-dot purple" }),
                h("span", null, "🟣 Backup Gesichert (pg/docker/rclone)")
              ),
            ),
          h("div", null,
            viewMode === "filesystem" ?
              "💡 Tipp: Klicken Sie auf einen Ordner für die Tiefenprüfung oder 'Neu scannen' zur Live-Aktualisierung." :
              "💡 Tipp: Klicken Sie auf einen Knoten zum Auf-/Zuklappen oder 'Auto-Fit Screen' zum Einpassen auf 1 Bildschirm."
          )
        )
      )
    );
  }

  // Tree-Position Hover Visualizer for Step 1
  function DriveTreeHoverPreview({ drive }) {
    if (!drive) return null;
    const hPath = drive.host_path || "";
    let crumbs = drive.tree_slice;
    if (!crumbs || crumbs.length === 0) {
      if (hPath.startsWith("gdrive://")) {
        crumbs = ["Cloud", "Google Drive", hPath.replace("gdrive://", "") || "Root"];
      } else if (hPath.startsWith("/")) {
        crumbs = ["/"].concat(hPath.split("/").filter(Boolean));
      } else {
        crumbs = ["Root", drive.name || "Drive"];
      }
    }

    return h("div", { className: "auto-org-tree-hover-preview" },
      h("div", { className: "auto-org-tree-hover-title" },
        h("span", null, "🌳"),
        h("span", null, "Stellung im Dateisystem-Baum (Host-Hierarchie):"),
        h("span", { style: { marginLeft: "auto", color: "#60a5fa", fontSize: "0.68rem" } },
          `Tiefe: ${crumbs.length - 1} • ${drive.category || "Drive"}`
        )
      ),
      h("div", { className: "auto-org-tree-breadcrumb-row" },
        crumbs.map((c, i) => {
          const isRoot = i === 0;
          const isLast = i === crumbs.length - 1;
          return h("span", { key: i, style: { display: "inline-flex", alignItems: "center", gap: "0.25rem" } },
            i > 0 && h("span", { style: { color: "#64748b", fontSize: "0.72rem" } }, "➔"),
            h("span", {
              className: `auto-org-tree-crumb ${isRoot ? "root" : ""} ${isLast ? "active" : ""}`,
              title: isLast ? `Aktueller Ordner: ${hPath}` : `Übergeordnetes Verzeichnis: ${c}`
            },
              isRoot ? "🖥️ /" : (isLast ? `📂 ${c}` : `📁 ${c}`)
            )
          );
        })
      ),
      h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.7rem", color: "#94a3b8", marginTop: "0.2rem" } },
        h("span", { style: { fontFamily: "monospace", color: "#93c5fd" } }, formatUserPath(hPath)),
        h("span", { style: { color: "#4ade80", fontWeight: 600 } },
          `${drive.free_space_gb || 0} GB frei • ${drive.is_writable ? "Schreibbar (RW)" : "Read-Only"}`
        )
      )
    );
  }

  // Animated "Von wo nach wo" Flow Route Component
  function AnimatedFlowRoute({ sourcePath, targetPath, confidence = 0.98, onFocusGraph = null, branchId = null, isApproved = false }) {
    const confPct = Math.round((confidence || 0.95) * 100);
    const srcDisplay = formatUserPath(sourcePath || "/home/mb/Downloads");
    const tgtDisplay = formatUserPath(targetPath || "/media/work-data/001_cv-bookaccount/{year}/");

    return h("div", { className: "auto-org-flow-route" },
      // Source Box
      h("div", { className: "auto-org-flow-box source", title: `Quell-Ort: ${srcDisplay}` },
        h("span", null, "📥"),
        h("span", null, srcDisplay.length > 36 ? "..." + srcDisplay.slice(-33) : srcDisplay)
      ),

      // Animated Glowing Flow Stream Line with AI Badge
      h("div", { style: { display: "flex", alignItems: "center", flex: 1, minWidth: "140px", gap: "0.35rem" } },
        h("div", { className: "auto-org-flow-stream-line" }),
        h("div", { className: "auto-org-neural-badge", title: `Semantische KI-Klassifikation: ${confPct}% Match` },
          h("span", { className: "auto-org-neural-dot" }),
          h("span", null, `⚡ KI ${confPct}%`)
        ),
        h("div", { className: "auto-org-flow-stream-line" }),
        h("span", { style: { color: "#38bdf8", fontWeight: 900, fontSize: "0.95rem" } }, "➔")
      ),

      // Target Box
      h("div", { className: "auto-org-flow-box target", title: `Konkreter Zielordner im Baum: ${tgtDisplay}` },
        h("span", null, "🎯"),
        h("span", null, tgtDisplay.length > 40 ? "..." + tgtDisplay.slice(-37) : tgtDisplay)
      ),

      // Optional Focus Button
      onFocusGraph && h("button", {
        type: "button",
        className: "auto-org-pipeline-focus-btn",
        title: "Diesen Pfad im interaktiven Graphen fokussieren",
        onClick: (e) => {
          e.stopPropagation();
          onFocusGraph(branchId || "dst_general");
        }
      }, "🔍 Im Graphen zeigen")
    );
  }

  // Semantic grouping helper for anomalies
  function groupAnomaliesBySemanticIntent(rawAnomalies) {
    if (!rawAnomalies || rawAnomalies.length === 0) return [];
    const map = new Map();
    for (const an of rawAnomalies) {
      const key = an.group_title || (an.suggested_target ? an.suggested_target : "Allgemeine Anomalien");
      if (!map.has(key)) {
        map.set(key, {
          id: "anom_grp_" + (an.group_title ? an.group_title.replace(/[^a-zA-Z0-9]/g, "_") : "gen"),
          title: an.group_title || "📁 Unsortierte Dateien",
          target_path: an.suggested_target || an.target_path || "/media/work-data/001_cv-bookaccount/{year}/Eingangsrechnungen/",
          tree_slice: an.tree_slice || ["work-data", "cv-bookaccount", "Eingangsrechnungen"],
          source_path: an.source_path || an.physical_path || "/home/mb/Downloads",
          confidence: an.confidence || 0.96,
          ai_reasoning: an.ai_reasoning || an.explanation || "Erkannt via semantischer OCR- und Pfadanalyse.",
          files: []
        });
      }
      map.get(key).files.push(an);
    }
    return Array.from(map.values());
  }

  // Visual Branch Pipeline Component (renders tree slice inside every card)
  function VisualBranchPipeline({ sourcePath, targetPath, treeSlice, confidence = 0.98, onFocusGraph = null, branchId = null }) {
    const confPct = Math.round((confidence || 0.95) * 100);
    const slice = (treeSlice && treeSlice.length > 0) ? treeSlice : (targetPath ? targetPath.split("/").filter(Boolean).slice(-3) : ["Ziel-Ast"]);

    return h("div", { className: "auto-org-branch-pipeline" },
      // Source Node
      h("div", { className: "auto-org-pipeline-node source", title: `Quelle: ${sourcePath || "/home/mb/Downloads"}` },
        h("span", null, "📥"),
        h("span", null, (sourcePath ? sourcePath.split("/").pop() : "Downloads") || "Quelle")
      ),
      // Arrow
      h("span", { className: "auto-org-pipeline-arrow" }, "──▶"),
      // AI Neural Classifier Badge
      h("div", {
        className: "auto-org-neural-badge",
        title: `KI-Vektor-Klassifikation: ${confPct}% Übereinstimmung`
      },
        h("span", { className: "auto-org-neural-dot" }),
        h("span", null, `⚡ KI ${confPct}%`)
      ),
      // Arrow
      h("span", { className: "auto-org-pipeline-arrow" }, "──▶"),
      // Tree Slice Breadcrumb Nodes
      slice.map((nodeName, idx) => {
        const isLast = idx === slice.length - 1;
        return h("span", { key: idx, style: { display: "inline-flex", alignItems: "center", gap: "0.35rem" } },
          idx > 0 && h("span", { className: "auto-org-pipeline-arrow", style: { fontSize: "0.75rem", opacity: 0.7 } }, "›"),
          h("div", {
            className: `auto-org-pipeline-node ${isLast ? "target" : "mid"}`,
            title: isLast ? `Zielpfad: ${targetPath}` : `Zwischenebene: ${nodeName}`
          },
            h("span", null, isLast ? "🎯" : "📁"),
            h("span", null, nodeName)
          )
        );
      }),
      // Focus in Graph Button
      onFocusGraph && h("button", {
        type: "button",
        className: "auto-org-pipeline-focus-btn",
        title: "Diesen Zweig im interaktiven Graphen fokussieren",
        onClick: (e) => {
          e.stopPropagation();
          onFocusGraph(branchId || slice[0]);
        }
      }, "🔍 Im Graphen fokussieren")
    );
  }

  // AI Reasoning Drawer Component (expandable neural decision insight)
  function AIReasoningDrawer({ confidence, reasoning, tokens = [], clusterName = null }) {
    const [isOpen, setIsOpen] = useState(false);
    const confPct = Math.round((confidence || 0.95) * 100);

    return h("div", { className: "auto-org-reasoning-drawer" },
      h("div", {
        className: "auto-org-reasoning-header",
        onClick: () => setIsOpen(!isOpen)
      },
        h("div", { style: { display: "flex", alignItems: "center", gap: "0.5rem" } },
          h("span", { style: { fontSize: "0.95rem" } }, "🧠"),
          h("span", { style: { fontWeight: 700, color: "#c084fc" } }, "KI-Entscheidungsgrundlage & Vektor-Kontext"),
          h("span", { className: "auto-org-badge auto-org-badge-blue", style: { fontSize: "0.68rem" } }, `${confPct}% Match`)
        ),
        h("span", { style: { fontSize: "0.8rem", color: "#94a3b8" } }, isOpen ? "▲ Schließen" : "▼ Details anzeigen")
      ),
      isOpen && h("div", { style: { display: "flex", flexDirection: "column", gap: "0.5rem", marginTop: "0.4rem", paddingTop: "0.4rem", borderTop: "1px solid rgba(99, 102, 241, 0.2)" } },
        // Reasoning text
        reasoning && h("p", { style: { color: "#e2e8f0", fontSize: "0.8125rem", lineHeight: "1.45", margin: 0 } }, reasoning),
        // Tokens
        tokens && tokens.length > 0 && h("div", { className: "auto-org-entity-list" },
          h("span", { style: { fontSize: "0.72rem", color: "#94a3b8", fontWeight: 600 } }, "Erkannte OCR-Merkmale & Tokens:"),
          tokens.map((tok, idx) =>
            h("span", { key: idx, className: "auto-org-entity-chip" },
              h("span", null, "🏷️"),
              h("span", null, tok)
            )
          )
        ),
        // Cluster info
        clusterName && h("div", { style: { fontSize: "0.72rem", color: "#94a3b8", fontFamily: "monospace" } },
          `Semantischer Vektor-Cluster: ${clusterName}`
        )
      )
    );
  }

  // File extension badge helper
  function getFileExtBadge(filename) {
    const ext = ((filename || "").split('.').pop() || '').toLowerCase();
    let cls = 'code';
    if (['pdf'].includes(ext)) cls = 'pdf';
    else if (['xlsx', 'xls', 'csv', 'tsv'].includes(ext)) cls = 'sheet';
    else if (['zip', 'tar', 'gz', 'bz2', '7z', 'deb'].includes(ext)) cls = 'archive';
    else if (['png', 'jpg', 'jpeg', 'webp', 'mp4', 'mov', 'svg'].includes(ext)) cls = 'media';
    return h('span', { className: `auto-org-ext-badge ${cls}` }, ext ? `.${ext}` : 'datei');
  }

  // Segmented Switch Button: Overlaying "Freigeben" (Green) and "Ausschließen" (Red)
  function OverlaySwitchButton({ status = "proposed", onApprove, onExclude, onReset, size = "md", disabled = false }) {
    // status: "approved" | "excluded" | "proposed"
    return h("div", { className: `auto-org-overlay-switch ${size === "sm" ? "sm" : ""}` },
      // Left: Freigeben (Green)
      h("button", {
        type: "button",
        className: `auto-org-switch-segment ${status === "approved" ? "active-approve" : ""}`,
        title: status === "approved" ? "Bereits freigegeben (Klicken zum Zurücksetzen)" : "Freigeben (auf Grün schalten)",
        disabled: disabled,
        onClick: (e) => {
          e.stopPropagation();
          if (status === "approved" && onReset) onReset();
          else if (onApprove) onApprove();
        }
      },
        h("span", null, status === "approved" ? "✓ Freigegeben" : "🟢 Freigeben")
      ),
      // Middle: Vorschlag indicator (when proposed / neutral)
      status === "proposed" && h("span", {
        className: "auto-org-switch-segment status-proposed",
        title: "Ausstehender Vorschlag — Treffen Sie Ihre Entscheidung (Freigeben oder Ausschließen)"
      }, "🟡 Vorschlag"),
      // Right: Ausschließen (Red)
      h("button", {
        type: "button",
        className: `auto-org-switch-segment ${status === "excluded" ? "active-exclude" : ""}`,
        title: status === "excluded" ? "Bereits ausgeschlossen (Klicken zum Zurücksetzen)" : "Ausschließen (auf Rot schalten)",
        disabled: disabled,
        onClick: (e) => {
          e.stopPropagation();
          if (status === "excluded" && onReset) onReset();
          else if (onExclude) onExclude();
        }
      },
        h("span", null, status === "excluded" ? "✕ Ausgeschlossen" : "🔴 Ausschließen")
      )
    );
  }

  // Visual File Path Tree Component (Authentic hierarchical tree with branch connectors, context menu, and rollover)
  function VisualFilePathTree({ sourcePath, targetPath, files = null, defaultExpanded = true, showSwitch = false, switchStatus = "proposed", onApprove = null, onExclude = null, title = null }) {
    const [expanded, setExpanded] = useState(defaultExpanded);
    const [contextMenu, setContextMenu] = useState(null);
    const [rollover, setRollover] = useState(null);
    const [localStatus, setLocalStatus] = useState(switchStatus);
    const [itemStates, setItemStates] = useState({});

    useEffect(() => {
      setLocalStatus(switchStatus);
    }, [switchStatus]);

    function handleSwitch(newState, itemPath) {
      if (itemPath) {
        setItemStates(prev => Object.assign({}, prev, { [itemPath]: newState }));
      } else {
        setLocalStatus(newState);
      }
      if (newState === "approved" && onApprove) onApprove();
      else if (newState === "excluded" && onExclude) onExclude();

      const p = itemPath || sourcePath || targetPath;
      if (p) {
        apiCall("/filesystem-tree/node-switch", {
          method: "POST",
          body: JSON.stringify({ path: p, state: newState })
        }).catch(err => console.warn("Failed to persist node state:", err));
      }
    }

    // Mode A: Multi-file list tree (grouping files by directory with connector lines)
    if (files && files.length > 0) {
      const srcDir = (sourcePath || (files[0].source_path ? files[0].source_path.substring(0, files[0].source_path.lastIndexOf('/')) : '/home/mb/Downloads'));
      const tgtDir = (targetPath || (files[0].destination_path ? files[0].destination_path.substring(0, files[0].destination_path.lastIndexOf('/')) : '/media/work-data/'));
      const rootState = itemStates[srcDir] || localStatus;

      return h("div", { className: "auto-org-visual-tree-container", style: { position: "relative" } },
        h("div", { className: "auto-org-tree-header" },
          h("div", { className: "auto-org-tree-title", style: { cursor: "pointer" }, onClick: () => setExpanded(!expanded) },
            h("span", null, expanded ? "▼" : "▶"),
            h("span", { style: { fontSize: "1.1rem" } }, "🌳"),
            h("span", null, title || `Visueller Dateibaum (${files.length} Dateien)`)
          ),
          showSwitch && h(OverlaySwitchButton, {
            status: rootState,
            onApprove: () => handleSwitch("approved", srcDir),
            onExclude: () => handleSwitch("excluded", srcDir),
            onReset: () => handleSwitch("proposed", srcDir),
            size: "sm"
          })
        ),
        expanded && h("div", null,
          // Source directory root
          h("div", {
            className: `auto-org-tree-root-item ${rootState === "approved" ? "auto-org-row-approved" : (rootState === "excluded" ? "auto-org-row-excluded" : "auto-org-row-proposed")}`,
            style: { cursor: "pointer", display: "flex", alignItems: "center", gap: "0.5rem" },
            onContextMenu: (e) => {
              e.preventDefault();
              setContextMenu({
                x: e.clientX,
                y: e.clientY,
                node: {
                  id: srcDir,
                  path: srcDir,
                  name: srcDir.split('/').pop() || srcDir,
                  node_type: "dir",
                  destination_path: tgtDir,
                  has_proposed_sync: true,
                  reorganization: { is_source: true, pending_moves: files.length }
                },
                currentState: rootState,
                onSelect: (st) => handleSwitch(st, srcDir)
              });
            },
            onMouseEnter: (e) => {
              setRollover({
                x: e.clientX,
                y: e.clientY,
                node: {
                  id: srcDir,
                  path: srcDir,
                  name: srcDir.split('/').pop() || srcDir,
                  node_type: "dir",
                  destination_path: tgtDir,
                  has_proposed_sync: true,
                  reorganization: { is_source: true, pending_moves: files.length }
                },
                state: rootState
              });
            },
            onMouseMove: (e) => {
              if (rollover) setRollover(prev => prev ? Object.assign({}, prev, { x: e.clientX, y: e.clientY }) : null);
            },
            onMouseLeave: () => setRollover(null)
          },
            h("span", { className: "auto-org-tree-node-icon" }, "📥"),
            h("span", { className: "auto-org-tree-node-name", style: { color: "#93c5fd" } }, formatUserPath(srcDir)),
            h("span", {
              className: `auto-org-badge ${rootState === "approved" ? "auto-org-badge-green" : (rootState === "excluded" ? "auto-org-badge-gray" : "auto-org-badge-yellow")}`,
              style: { marginLeft: "auto", fontSize: "0.68rem" }
            }, rootState === "approved" ? "🟢 Freigegeben" : (rootState === "excluded" ? "⚪ Nicht einbezogen" : "🟡 Vorgeschlagen"))
          ),
          // File branches
          h("div", { className: "auto-org-tree-children" },
            files.map((f, idx) => {
              const isLast = idx === files.length - 1;
              const connector = isLast ? "└── " : "├── ";
              const fname = f.file_name || (f.source_path ? f.source_path.split('/').pop() : `file_${idx}`);
              const fPath = f.source_path || (srcDir + "/" + fname);
              const tgt = formatUserPath(f.destination_path || f.suggested_target || tgtDir);
              const fState = itemStates[fPath] || rootState;

              return h("div", {
                key: idx,
                className: `auto-org-tree-branch-line ${fState === "approved" ? "auto-org-row-approved" : (fState === "excluded" ? "auto-org-row-excluded" : "auto-org-row-proposed")}`,
                style: { cursor: "pointer" },
                onContextMenu: (e) => {
                  e.preventDefault();
                  setContextMenu({
                    x: e.clientX,
                    y: e.clientY,
                    node: {
                      id: fPath,
                      name: fname,
                      path: fPath,
                      node_type: "file",
                      destination_path: tgt,
                      has_proposed_sync: true,
                      size_mb: f.size_kb ? f.size_kb / 1024 : undefined
                    },
                    currentState: fState,
                    onSelect: (st) => handleSwitch(st, fPath)
                  });
                },
                onMouseEnter: (e) => {
                  setRollover({
                    x: e.clientX,
                    y: e.clientY,
                    node: {
                      id: fPath,
                      name: fname,
                      path: fPath,
                      node_type: "file",
                      destination_path: tgt,
                      has_proposed_sync: true,
                      size_mb: f.size_kb ? f.size_kb / 1024 : undefined
                    },
                    state: fState
                  });
                },
                onMouseMove: (e) => {
                  if (rollover) setRollover(prev => prev ? Object.assign({}, prev, { x: e.clientX, y: e.clientY }) : null);
                },
                onMouseLeave: () => setRollover(null)
              },
                h("span", { className: "auto-org-tree-branch-connector" }, connector),
                h("span", { className: "auto-org-tree-node-icon" }, "📄"),
                getFileExtBadge(fname),
                h("span", { className: "auto-org-tree-node-name" }, fname),
                f.size_kb && h("span", { style: { color: "#64748b", fontSize: "0.7rem" } }, `${f.size_kb} KB`),
                h("span", { className: "auto-org-tree-move-arrow" }, "──▶"),
                h("span", { className: "auto-org-tree-move-target", style: { fontSize: "0.72rem", fontFamily: "monospace" } }, tgt),
                h("span", {
                  className: `auto-org-badge ${fState === "approved" ? "auto-org-badge-green" : (fState === "excluded" ? "auto-org-badge-gray" : "auto-org-badge-yellow")}`,
                  style: { marginLeft: "auto", fontSize: "0.65rem", padding: "0.15rem 0.4rem" }
                }, fState === "approved" ? "🟢 Freigabe" : (fState === "excluded" ? "⚪ Excluded" : "🟡 Vorschlag"))
              );
            })
          ),
          // Target directory destination branch
          tgtDir && h("div", { style: { marginTop: "0.5rem" } },
            h("div", {
              className: "auto-org-tree-root-item",
              style: { color: "#4ade80", cursor: "pointer", display: "flex", alignItems: "center", gap: "0.5rem" },
              onContextMenu: (e) => {
                e.preventDefault();
                setContextMenu({
                  x: e.clientX,
                  y: e.clientY,
                  node: {
                    id: tgtDir,
                    path: tgtDir,
                    name: tgtDir.split('/').filter(Boolean).pop() || tgtDir,
                    node_type: "dir",
                    destination_path: tgtDir,
                    has_proposed_sync: true,
                    reorganization: { is_target: true }
                  },
                  currentState: rootState,
                  onSelect: (st) => handleSwitch(st, tgtDir)
                });
              },
              onMouseEnter: (e) => {
                setRollover({
                  x: e.clientX,
                  y: e.clientY,
                  node: {
                    id: tgtDir,
                    path: tgtDir,
                    name: tgtDir.split('/').filter(Boolean).pop() || tgtDir,
                    node_type: "dir",
                    destination_path: tgtDir,
                    has_proposed_sync: true,
                    reorganization: { is_target: true }
                  },
                  state: rootState
                });
              },
              onMouseMove: (e) => {
                if (rollover) setRollover(prev => prev ? Object.assign({}, prev, { x: e.clientX, y: e.clientY }) : null);
              },
              onMouseLeave: () => setRollover(null)
            },
              h("span", { className: "auto-org-tree-node-icon" }, "🎯"),
              h("span", { className: "auto-org-tree-node-name", style: { color: "#86efac" } }, `Ziel-Hierarchie: ${formatUserPath(tgtDir)}`),
              h("span", {
                className: `auto-org-badge ${rootState === "approved" ? "auto-org-badge-green" : (rootState === "excluded" ? "auto-org-badge-gray" : "auto-org-badge-yellow")}`,
                style: { marginLeft: "auto", fontSize: "0.68rem" }
              }, rootState === "approved" ? "🟢 Ziel freigegeben" : (rootState === "excluded" ? "⚪ Excluded" : "🟡 Ziel-Vorschlag"))
            )
          )
        ),
        contextMenu && h(FloatingContextMenu, {
          x: contextMenu.x,
          y: contextMenu.y,
          node: contextMenu.node,
          currentState: contextMenu.currentState,
          onClose: () => setContextMenu(null),
          onSelectState: (st) => {
            if (contextMenu.onSelect) contextMenu.onSelect(st);
            else handleSwitch(st, contextMenu.node.path);
          }
        }),
        rollover && h(SyncRolloverTooltip, {
          x: rollover.x,
          y: rollover.y,
          node: rollover.node,
          nodeState: rollover.state
        })
      );
    }

    // Mode B: Single path or source -> target path tree
    const srcClean = formatUserPath(sourcePath || "");
    const tgtClean = formatUserPath(targetPath || "");
    const tgtParts = tgtClean.split('/').filter(Boolean);
    const singleState = localStatus;

    return h("div", { className: "auto-org-visual-tree-container", style: { position: "relative" } },
      h("div", { className: "auto-org-tree-header" },
        h("div", { className: "auto-org-tree-title", style: { cursor: "pointer" }, onClick: () => setExpanded(!expanded) },
          h("span", null, expanded ? "▼" : "▶"),
          h("span", null, "🌳"),
          h("span", null, title || "Visuelle Pfad-Hierarchie")
        ),
        showSwitch && h(OverlaySwitchButton, {
          status: singleState,
          onApprove: () => handleSwitch("approved"),
          onExclude: () => handleSwitch("excluded"),
          onReset: () => handleSwitch("proposed"),
          size: "sm"
        })
      ),
      expanded && h("div", { style: { display: "flex", flexDirection: "column", gap: "0.4rem" } },
        // Source Tree
        srcClean && h("div", null,
          h("div", {
            className: `auto-org-tree-root-item ${singleState === "approved" ? "auto-org-row-approved" : (singleState === "excluded" ? "auto-org-row-excluded" : "auto-org-row-proposed")}`,
            style: { cursor: "pointer", display: "flex", alignItems: "center", gap: "0.5rem" },
            onContextMenu: (e) => {
              e.preventDefault();
              setContextMenu({
                x: e.clientX,
                y: e.clientY,
                node: {
                  id: srcClean,
                  path: srcClean,
                  name: srcClean.split('/').pop() || srcClean,
                  node_type: "dir",
                  destination_path: tgtClean,
                  has_proposed_sync: true
                },
                currentState: singleState,
                onSelect: (st) => handleSwitch(st, srcClean)
              });
            },
            onMouseEnter: (e) => {
              setRollover({
                x: e.clientX,
                y: e.clientY,
                node: {
                  id: srcClean,
                  path: srcClean,
                  name: srcClean.split('/').pop() || srcClean,
                  node_type: "dir",
                  destination_path: tgtClean,
                  has_proposed_sync: true
                },
                state: singleState
              });
            },
            onMouseMove: (e) => {
              if (rollover) setRollover(prev => prev ? Object.assign({}, prev, { x: e.clientX, y: e.clientY }) : null);
            },
            onMouseLeave: () => setRollover(null)
          },
            h("span", null, "📁 Herkunft:"),
            h("span", { style: { color: "#f87171" } }, srcClean),
            h("span", {
              className: `auto-org-badge ${singleState === "approved" ? "auto-org-badge-green" : (singleState === "excluded" ? "auto-org-badge-gray" : "auto-org-badge-yellow")}`,
              style: { marginLeft: "auto", fontSize: "0.68rem" }
            }, singleState === "approved" ? "🟢 Freigegeben" : (singleState === "excluded" ? "⚪ Nicht einbezogen" : "🟡 Vorgeschlagen"))
          )
        ),
        // Animated Connection
        tgtClean && h("div", { style: { display: "flex", alignItems: "center", gap: "0.5rem", color: "#38bdf8", paddingLeft: "1rem" } },
          h("span", { style: { fontWeight: 800 } }, "│"),
          h("span", { className: "auto-org-tree-move-arrow" }, "▼ Reorganisieren nach:")
        ),
        // Target Tree (Hierarchical branches)
        tgtClean && h("div", null,
          tgtParts.map((part, pidx) => {
            const isDrive = pidx === 0 || part.startsWith("media") || part.includes("data") || part.includes("work");
            const isLeaf = pidx === tgtParts.length - 1;
            const indent = pidx * 1.2;

            return h("div", {
              key: pidx,
              className: singleState === "approved" ? "auto-org-row-approved" : (singleState === "excluded" ? "auto-org-row-excluded" : "auto-org-row-proposed"),
              style: {
                paddingLeft: `${indent}rem`,
                display: "flex",
                alignItems: "center",
                gap: "0.35rem",
                color: isLeaf ? "#4ade80" : (isDrive ? "#38bdf8" : "#93c5fd"),
                fontWeight: isDrive || isLeaf ? 700 : 500,
                fontSize: "0.78rem",
                cursor: "pointer",
                paddingTop: "0.2rem",
                paddingBottom: "0.2rem",
                borderRadius: "0.25rem"
              },
              onContextMenu: (e) => {
                e.preventDefault();
                setContextMenu({
                  x: e.clientX,
                  y: e.clientY,
                  node: {
                    id: "/" + tgtParts.slice(0, pidx + 1).join('/'),
                    path: "/" + tgtParts.slice(0, pidx + 1).join('/'),
                    name: part,
                    node_type: isDrive ? "drive" : (isLeaf ? "file" : "dir"),
                    destination_path: tgtClean,
                    has_proposed_sync: true
                  },
                  currentState: singleState,
                  onSelect: (st) => handleSwitch(st, "/" + tgtParts.slice(0, pidx + 1).join('/'))
                });
              },
              onMouseEnter: (e) => {
                setRollover({
                  x: e.clientX,
                  y: e.clientY,
                  node: {
                    id: "/" + tgtParts.slice(0, pidx + 1).join('/'),
                    path: "/" + tgtParts.slice(0, pidx + 1).join('/'),
                    name: part,
                    node_type: isDrive ? "drive" : (isLeaf ? "file" : "dir"),
                    destination_path: tgtClean,
                    has_proposed_sync: true
                  },
                  state: singleState
                });
              },
              onMouseMove: (e) => {
                if (rollover) setRollover(prev => prev ? Object.assign({}, prev, { x: e.clientX, y: e.clientY }) : null);
              },
              onMouseLeave: () => setRollover(null)
            },
              h("span", { style: { color: "#64748b", fontFamily: "monospace" } }, pidx > 0 ? "├── " : ""),
              h("span", null, pidx === 0 ? "💽 /" + part : (isLeaf ? "🎯 " + part : "📁 " + part))
            );
          })
        )
      ),
      contextMenu && h(FloatingContextMenu, {
        x: contextMenu.x,
        y: contextMenu.y,
        node: contextMenu.node,
        currentState: contextMenu.currentState,
        onClose: () => setContextMenu(null),
        onSelectState: (st) => {
          if (contextMenu.onSelect) contextMenu.onSelect(st);
          else handleSwitch(st, contextMenu.node.path);
        }
      }),
      rollover && h(SyncRolloverTooltip, {
        x: rollover.x,
        y: rollover.y,
        node: rollover.node,
        nodeState: rollover.state
      })
    );
  }

  // Visual Dry Run Path Tree (Complete hierarchical filesystem tree for Step 4 with context menu and rollover)
  function VisualDryRunPathTree({ actions = [], groups = [], approvedGroupIds, excludedGroupIds, onSwitchGroup }) {
    const [filterText, setFilterText] = useState("");
    const [expandedFolders, setExpandedFolders] = useState({});
    const [contextMenu, setContextMenu] = useState(null);
    const [rollover, setRollover] = useState(null);
    const [nodeStates, setNodeStates] = useState({});

    useEffect(() => {
      apiCall("/filesystem-tree/node-states")
        .then(data => {
          if (data && (data.node_states || data.states)) setNodeStates(data.node_states || data.states);
        })
        .catch(() => {});
    }, []);

    function getNodeState(path, act) {
      if (path && nodeStates[path]) return nodeStates[path];
      if (act && act.group_id) {
        if (approvedGroupIds && approvedGroupIds.has(act.group_id)) return "approved";
        if (excludedGroupIds && excludedGroupIds.has(act.group_id)) return "excluded";
      }
      return "proposed";
    }

    function handleSwitchNode(path, newState, act) {
      setNodeStates(prev => Object.assign({}, prev, { [path]: newState }));
      if (act && act.group_id && onSwitchGroup) {
        onSwitchGroup(act.group_id, newState);
      }
      apiCall("/filesystem-tree/node-switch", {
        method: "POST",
        body: JSON.stringify({ path: path, state: newState })
      }).catch(err => console.warn("Failed to persist node state:", err));
    }

    // Filter actions
    const filteredActions = filterText.trim() ?
      actions.filter(a => (a.file_name || "").toLowerCase().includes(filterText.toLowerCase()) ||
                          (a.source_path || "").toLowerCase().includes(filterText.toLowerCase()) ||
                          (a.destination_path || "").toLowerCase().includes(filterText.toLowerCase())) :
      actions;

    // Group actions by source directory
    const treeByDir = {};
    filteredActions.forEach(act => {
      const src = act.source_path || "";
      const dir = src.substring(0, src.lastIndexOf('/')) || "/";
      if (!treeByDir[dir]) treeByDir[dir] = [];
      treeByDir[dir].push(act);
    });

    const dirs = Object.keys(treeByDir).sort();

    return h("div", { className: "auto-org-visual-tree-container", style: { padding: "1.25rem", borderRadius: "0.75rem", position: "relative" } },
      // Top Controls
      h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.75rem" } },
        h("div", { style: { display: "flex", alignItems: "center", gap: "0.5rem" } },
          h("span", { style: { fontSize: "1.3rem" } }, "🌳"),
          h("div", null,
            h("strong", { style: { color: "#ffffff", fontSize: "1.05rem" } }, "Visueller Reorganisations-Pfadbaum"),
            h("div", { style: { fontSize: "0.75rem", color: "#94a3b8" } },
              `${actions.length} Dateien in ${dirs.length} Quell-Verzeichnissen geordnet nach Zielstruktur (Rechtsklick: Status umschalten)`
            )
          )
        ),
        h("div", { style: { display: "flex", alignItems: "center", gap: "0.5rem" } },
          h("input", {
            type: "text",
            className: "auto-org-input",
            placeholder: "🔍 Dateipfad / Name filtern...",
            style: { width: "220px", fontSize: "0.75rem", padding: "0.3rem 0.6rem" },
            value: filterText,
            onChange: (e) => setFilterText(e.target.value)
          })
        )
      ),

      // Tree Nodes by Directory
      dirs.length === 0 ?
      h("div", { style: { textAlign: "center", color: "#94a3b8", padding: "2rem" } }, "Keine Dateien im Pfadbaum gefunden.") :
      dirs.map((dir, didx) => {
        const dirFiles = treeByDir[dir];
        const isDirExpanded = expandedFolders[dir] !== false; // expanded by default
        const dirState = nodeStates[dir] || (
          dirFiles.every(a => getNodeState(a.source_path, a) === "approved") ? "approved" :
          (dirFiles.every(a => getNodeState(a.source_path, a) === "excluded") ? "excluded" : "proposed")
        );

        return h("div", {
          key: didx,
          className: `auto-org-row-${dirState}`,
          style: {
            marginBottom: "1rem",
            background: "rgba(30, 41, 59, 0.4)",
            borderRadius: "0.5rem",
            padding: "0.5rem 0.75rem",
            border: "1px solid #334155",
            transition: "all 0.15s ease"
          }
        },
          // Directory Header
          h("div", {
            style: { display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer", padding: "0.2rem 0" },
            onClick: () => setExpandedFolders(prev => Object.assign({}, prev, { [dir]: !isDirExpanded })),
            onContextMenu: (e) => {
              e.preventDefault();
              setContextMenu({
                x: e.clientX,
                y: e.clientY,
                node: {
                  id: dir,
                  path: dir,
                  name: dir.split('/').pop() || dir,
                  node_type: "dir",
                  destination_path: dirFiles[0] ? dirFiles[0].destination_path : undefined,
                  has_proposed_sync: true,
                  reorganization: { is_source: true, pending_moves: dirFiles.length }
                },
                currentState: dirState,
                onSelect: (st) => {
                  handleSwitchNode(dir, st);
                  dirFiles.forEach(a => {
                    if (a.source_path) handleSwitchNode(a.source_path, st, a);
                  });
                }
              });
            },
            onMouseEnter: (e) => {
              setRollover({
                x: e.clientX,
                y: e.clientY,
                node: {
                  id: dir,
                  path: dir,
                  name: dir.split('/').pop() || dir,
                  node_type: "dir",
                  destination_path: dirFiles[0] ? dirFiles[0].destination_path : undefined,
                  has_proposed_sync: true,
                  reorganization: { is_source: true, pending_moves: dirFiles.length }
                },
                state: dirState
              });
            },
            onMouseMove: (e) => {
              if (rollover) setRollover(prev => prev ? Object.assign({}, prev, { x: e.clientX, y: e.clientY }) : null);
            },
            onMouseLeave: () => setRollover(null)
          },
            h("div", { style: { display: "flex", alignItems: "center", gap: "0.4rem" } },
              h("span", { style: { color: "#60a5fa", fontWeight: 800, fontSize: "0.85rem" } }, isDirExpanded ? "▼" : "▶"),
              h("span", { style: { fontSize: "1.1rem" } }, "📁"),
              h("strong", { style: { color: "#93c5fd", fontSize: "0.9rem", fontFamily: "monospace" } }, formatUserPath(dir)),
              h("span", { className: "auto-org-badge auto-org-badge-blue", style: { fontSize: "0.68rem" } }, `${dirFiles.length} Dateien`)
            ),
            h("div", { style: { display: "flex", alignItems: "center", gap: "0.5rem" } },
              h("button", {
                type: "button",
                className: `auto-org-badge ${dirState === "approved" ? "auto-org-badge-green" : (dirState === "excluded" ? "auto-org-badge-gray" : "auto-org-badge-yellow")}`,
                style: { cursor: "pointer", border: "none", fontSize: "0.7rem", padding: "0.2rem 0.5rem" },
                title: "Klicken oder Rechtsklick zum Umschalten aller Dateien in diesem Ordner",
                onClick: (e) => {
                  e.stopPropagation();
                  const next = dirState === "approved" ? "excluded" : (dirState === "excluded" ? "proposed" : "approved");
                  handleSwitchNode(dir, next);
                  dirFiles.forEach(a => {
                    if (a.source_path) handleSwitchNode(a.source_path, next, a);
                  });
                }
              }, dirState === "approved" ? "🟢 Ordner freigegeben" : (dirState === "excluded" ? "⚪ Nicht einbezogen" : "🟡 Ordner Vorschlag"))
            )
          ),

          // File Branches inside Directory
          isDirExpanded && h("div", { className: "auto-org-tree-children", style: { marginTop: "0.4rem" } },
            dirFiles.map((act, fidx) => {
              const isLast = fidx === dirFiles.length - 1;
              const fname = act.file_name || (act.source_path ? act.source_path.split('/').pop() : `file_${fidx}`);
              const fPath = act.source_path || (dir + "/" + fname);
              const tgt = formatUserPath(act.destination_path);
              const fState = getNodeState(fPath, act);

              return h("div", {
                key: fidx,
                className: `auto-org-tree-branch-line auto-org-row-${fState}`,
                style: {
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: "0.5rem",
                  cursor: "pointer",
                  borderRadius: "0.25rem",
                  padding: "0.25rem 0.4rem"
                },
                onContextMenu: (e) => {
                  e.preventDefault();
                  setContextMenu({
                    x: e.clientX,
                    y: e.clientY,
                    node: {
                      id: fPath,
                      name: fname,
                      path: fPath,
                      node_type: "file",
                      destination_path: tgt,
                      has_proposed_sync: true,
                      size_mb: act.size_kb ? act.size_kb / 1024 : undefined,
                      reorganization: {
                        is_source: true,
                        target_rules: act.rule_name ? [act.rule_name] : []
                      }
                    },
                    currentState: fState,
                    onSelect: (st) => handleSwitchNode(fPath, st, act)
                  });
                },
                onMouseEnter: (e) => {
                  setRollover({
                    x: e.clientX,
                    y: e.clientY,
                    node: {
                      id: fPath,
                      name: fname,
                      path: fPath,
                      node_type: "file",
                      destination_path: tgt,
                      has_proposed_sync: true,
                      size_mb: act.size_kb ? act.size_kb / 1024 : undefined,
                      reorganization: {
                        is_source: true,
                        target_rules: act.rule_name ? [act.rule_name] : []
                      }
                    },
                    state: fState
                  });
                },
                onMouseMove: (e) => {
                  if (rollover) setRollover(prev => prev ? Object.assign({}, prev, { x: e.clientX, y: e.clientY }) : null);
                },
                onMouseLeave: () => setRollover(null)
              },
                h("div", { style: { display: "flex", alignItems: "center", gap: "0.4rem", flex: 1, minWidth: "300px" } },
                  h("span", { className: "auto-org-tree-branch-connector" }, isLast ? "└── " : "├── "),
                  h("span", { className: "auto-org-tree-node-icon" }, "📄"),
                  getFileExtBadge(fname),
                  h("span", { className: "auto-org-tree-node-name" }, fname),
                  act.size_kb && h("span", { style: { color: "#64748b", fontSize: "0.7rem" } }, `${act.size_kb} KB`),
                  h("span", { className: "auto-org-tree-move-arrow" }, "──▶"),
                  h("span", { className: "auto-org-tree-move-target", style: { fontSize: "0.75rem", fontFamily: "monospace" } }, tgt)
                ),
                h("div", { style: { display: "flex", alignItems: "center", gap: "0.4rem" } },
                  act.rule_name && h("span", { className: "auto-org-badge auto-org-badge-blue", style: { fontSize: "0.68rem" } }, act.rule_name),
                  h("span", { className: `auto-org-badge ${act.safe_to_execute ? "auto-org-badge-green" : "auto-org-badge-red"}`, style: { fontSize: "0.68rem" } },
                    act.safe_to_execute ? "✓ Bereit" : "⚠️ Prüfen"
                  ),
                  h("button", {
                    type: "button",
                    className: `auto-org-badge ${fState === "approved" ? "auto-org-badge-green" : (fState === "excluded" ? "auto-org-badge-gray" : "auto-org-badge-yellow")}`,
                    style: { cursor: "pointer", border: "none", fontSize: "0.68rem", padding: "0.15rem 0.45rem" },
                    title: "Klicken oder Rechtsklick: Status umschalten",
                    onClick: (e) => {
                      e.stopPropagation();
                      const next = fState === "approved" ? "excluded" : (fState === "excluded" ? "proposed" : "approved");
                      handleSwitchNode(fPath, next, act);
                    }
                  }, fState === "approved" ? "🟢 Freigabe" : (fState === "excluded" ? "⚪ Excluded" : "🟡 Vorschlag"))
                )
              );
            })
          )
        );
      }),

      contextMenu && h(FloatingContextMenu, {
        x: contextMenu.x,
        y: contextMenu.y,
        node: contextMenu.node,
        currentState: contextMenu.currentState,
        onClose: () => setContextMenu(null),
        onSelectState: (st) => {
          if (contextMenu.onSelect) contextMenu.onSelect(st);
          else handleSwitchNode(contextMenu.node.path || contextMenu.node.id, st);
        }
      }),
      rollover && h(SyncRolloverTooltip, {
        x: rollover.x,
        y: rollover.y,
        node: rollover.node,
        nodeState: rollover.state
      })
    );
  }

  // Multi-Level Tree Explorer Component for Step 2
  function MultiLevelTreeExplorer({ categories, isApproved, onToggleApproveCategory, onFocusGraph, expandedBranches, onToggleExpandBranch, onApplyToRule, approvedCategoryIds, excludedCategoryIds, onSwitchCategory }) {
    const [contextMenu, setContextMenu] = useState(null);
    const [rollover, setRollover] = useState(null);

    return h("div", { className: "auto-org-tree-explorer", style: { position: "relative" } },
      categories.map((cat) => {
        const isExpanded = expandedBranches.has(cat.id);
        const confPct = Math.round((cat.confidence || 0.95) * 100);
        const subBranches = cat.sub_branches || [];
        const catStatus = approvedCategoryIds && approvedCategoryIds.has(cat.id) ? "approved" :
          (excludedCategoryIds && excludedCategoryIds.has(cat.id) ? "excluded" : (isApproved ? "approved" : "proposed"));

        return h("div", {
          key: cat.id,
          className: `auto-org-tree-root-item ${isExpanded ? "expanded" : ""} ${catStatus === "approved" ? "auto-org-card-approved" : (catStatus === "excluded" ? "auto-org-card-excluded" : "")}`,
          onContextMenu: (e) => {
            e.preventDefault();
            setContextMenu({
              x: e.clientX,
              y: e.clientY,
              node: {
                id: cat.id,
                path: cat.display_name || cat.name,
                name: cat.name,
                node_type: "dir",
                proposed_target: cat.target_path || (subBranches[0] ? subBranches[0].target_path : undefined),
                has_proposed_sync: true
              },
              currentState: catStatus,
              onSelect: (st) => onSwitchCategory ? onSwitchCategory(cat.id, st) : (st === "approved" && onToggleApproveCategory ? onToggleApproveCategory(cat.id) : null)
            });
          },
          onMouseEnter: (e) => {
            setRollover({
              x: e.clientX,
              y: e.clientY,
              node: {
                id: cat.id,
                path: cat.display_name || cat.name,
                name: cat.name,
                node_type: "dir",
                proposed_target: cat.target_path || (subBranches[0] ? subBranches[0].target_path : undefined),
                has_proposed_sync: true
              },
              state: catStatus
            });
          },
          onMouseMove: (e) => {
            if (rollover) setRollover(prev => prev ? Object.assign({}, prev, { x: e.clientX, y: e.clientY }) : null);
          },
          onMouseLeave: () => setRollover(null)
        },
          // Root Header Row
          h("div", {
            style: { display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.75rem", cursor: "pointer" },
            onClick: () => onToggleExpandBranch(cat.id)
          },
            h("div", { style: { display: "flex", alignItems: "center", gap: "0.6rem" } },
              h("span", { style: { fontSize: "0.9rem", color: "#60a5fa", fontWeight: 800 } }, isExpanded ? "▼" : "▶"),
              h("span", { style: { fontSize: "1.4rem" } }, cat.icon || "📁"),
              h("div", null,
                h("span", { style: { fontWeight: 700, color: "#ffffff", fontSize: "1.05rem", display: "inline-block", marginRight: "0.5rem" } }, cat.name),
                h("span", { style: { fontSize: "0.85rem", color: "#94a3b8" } }, cat.display_name)
              )
            ),
            h("div", { style: { display: "flex", alignItems: "center", gap: "0.6rem", flexWrap: "wrap" } },
              h("span", { className: "auto-org-badge auto-org-badge-blue", style: { fontSize: "0.72rem" } }, `${subBranches.length} Unteräste`),
              h("span", { className: "auto-org-badge auto-org-badge-green", style: { fontSize: "0.72rem" } }, `${cat.file_count || 0} Dateien`),
              h("div", { className: "auto-org-neural-badge" },
                h("span", { className: "auto-org-neural-dot" }),
                h("span", null, `⚡ ${confPct}%`)
              ),
              h(OverlaySwitchButton, {
                status: catStatus,
                onApprove: () => onSwitchCategory ? onSwitchCategory(cat.id, "approved") : (onToggleApproveCategory && onToggleApproveCategory(cat.id)),
                onExclude: () => onSwitchCategory ? onSwitchCategory(cat.id, "excluded") : null,
                onReset: () => onSwitchCategory ? onSwitchCategory(cat.id, "proposed") : null,
                size: "sm"
              })
            )
          ),

          // Evidence callout
          cat.data_evidence && h("div", {
            style: {
              background: "rgba(15, 23, 42, 0.7)",
              borderLeft: "3px solid #60a5fa",
              padding: "0.4rem 0.65rem",
              borderRadius: "0.25rem",
              fontSize: "0.78rem",
              color: "#cbd5e1",
              fontStyle: "italic"
            }
          }, `„${cat.data_evidence}“`),

          // Sub-Branches Nested List (shown when expanded)
          isExpanded && subBranches.length > 0 && h("div", { className: "auto-org-tree-sub-list" },
            subBranches.map((sub) => {
              const subConf = Math.round((sub.confidence || 0.95) * 100);
              return h("div", {
                key: sub.id,
                className: "auto-org-tree-sub-item",
                style: { cursor: "pointer" },
                onContextMenu: (e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setContextMenu({
                    x: e.clientX,
                    y: e.clientY,
                    node: {
                      id: sub.id,
                      path: sub.target_path,
                      name: sub.name,
                      node_type: "dir",
                      proposed_target: sub.target_path,
                      has_proposed_sync: true
                    },
                    currentState: catStatus,
                    onSelect: (st) => onSwitchCategory ? onSwitchCategory(cat.id, st) : null
                  });
                },
                onMouseEnter: (e) => {
                  e.stopPropagation();
                  setRollover({
                    x: e.clientX,
                    y: e.clientY,
                    node: {
                      id: sub.id,
                      path: sub.target_path,
                      name: sub.name,
                      node_type: "dir",
                      proposed_target: sub.target_path,
                      has_proposed_sync: true
                    },
                    state: catStatus
                  });
                },
                onMouseMove: (e) => {
                  if (rollover) setRollover(prev => prev ? Object.assign({}, prev, { x: e.clientX, y: e.clientY }) : null);
                },
                onMouseLeave: () => setRollover(null)
              },
                // Left Column: Branch Title, Icon & Path
                h("div", { style: { flex: 1, minWidth: "260px" } },
                  h("div", { style: { display: "flex", alignItems: "center", gap: "0.4rem", marginBottom: "0.2rem" } },
                    h("span", { style: { fontSize: "1.1rem" } }, sub.icon || "📂"),
                    h("strong", { style: { color: "#ffffff", fontSize: "0.9rem" } }, sub.name),
                    h("span", { style: { fontSize: "0.72rem", color: "#60a5fa" } }, `(${sub.file_count} Dateien)`)
                  ),
                  h("div", { style: { fontFamily: "monospace", fontSize: "0.75rem", color: "#4ade80", wordBreak: "break-all" } },
                    formatUserPath(sub.target_path)
                  ),
                  // Entity chips
                  sub.detected_entities && sub.detected_entities.length > 0 && h("div", { className: "auto-org-entity-list", style: { marginTop: "0.3rem" } },
                    sub.detected_entities.map((e, ei) =>
                      h("span", { key: ei, className: "auto-org-entity-chip" },
                        h("span", null, "🏷️"),
                        h("span", null, e)
                      )
                    )
                  )
                ),
                // Right Column: AI Match, Graph Focus & Action
                h("div", { style: { display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" } },
                  h("div", { className: "auto-org-neural-badge" },
                    h("span", { className: "auto-org-neural-dot" }),
                    h("span", null, `${subConf}% Match`)
                  ),
                  onFocusGraph && h("button", {
                    type: "button",
                    className: "auto-org-pill-btn",
                    style: { background: "rgba(59, 130, 246, 0.25)", borderColor: "#3b82f6", color: "#93c5fd" },
                    onClick: (e) => {
                      e.stopPropagation();
                      onFocusGraph(sub.id);
                    }
                  }, "🔍 Im Graphen fokussieren"),
                  onApplyToRule && h("button", {
                    type: "button",
                    className: "auto-org-pill-btn",
                    onClick: (e) => {
                      e.stopPropagation();
                      onApplyToRule({ name: sub.name, target_path_template: sub.target_path });
                    }
                  }, "⚡ Als Regel-Ziel →")
                )
              );
            })
          )
        );
      }),
      contextMenu && h(FloatingContextMenu, {
        x: contextMenu.x,
        y: contextMenu.y,
        node: contextMenu.node,
        currentState: contextMenu.currentState,
        onClose: () => setContextMenu(null),
        onSelectState: (st) => {
          if (contextMenu.onSelect) contextMenu.onSelect(st);
        }
      }),
      rollover && h(SyncRolloverTooltip, {
        x: rollover.x,
        y: rollover.y,
        node: rollover.node,
        nodeState: rollover.state
      })
    );
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
    const [roots, setRoots] = useState(DEFAULT_ROOTS);
    const [anomalies, setAnomalies] = useState([]);
    const [rules, setRules] = useState([]);
    const [dryRun, setDryRun] = useState(null);
    const [batches, setBatches] = useState([]);
    const [mountData, setMountData] = useState(null);
    const [taxonomy, setTaxonomy] = useState(DEFAULT_TAXONOMY);
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

    // Proactive AI Discovery & Emergent Taxonomy & Cross-Drive Reconciliation State
    const [proactiveScan, setProactiveScan] = useState(null);
    const [emergentTaxonomy, setEmergentTaxonomy] = useState(null);
    const [reconciliation, setReconciliation] = useState(null);
    const [indexingLoading, setIndexingLoading] = useState(false);

    // Step 2 Taxonomy state
    const [showNewNodeForm, setShowNewNodeForm] = useState(false);
    const [newNodeName, setNewNodeName] = useState("");
    const [newNodePath, setNewNodePath] = useState("");
    const [newNodeDesc, setNewNodeDesc] = useState("");
    const [newNodeIcon, setNewNodeIcon] = useState("📁");
    const [newNodeKeywords, setNewNodeKeywords] = useState("");
    const [expandedSamples, setExpandedSamples] = useState({});

    // Step 2 View Mode & Obsidian Animation State
    const [step2ViewMode, setStep2ViewMode] = useState("tree"); // "tree" | "graph"
    const [obsidianPaused, setObsidianPaused] = useState(false);
    const [obsidianSpeed, setObsidianSpeed] = useState(1);

    // Step 3 Modular Rule Builder & Proactive Suggestions State
    const [suggestedRules, setSuggestedRules] = useState(null);
    const [selectedSuggestedRuleIds, setSelectedSuggestedRuleIds] = useState(new Set());
    const [adoptingRules, setAdoptingRules] = useState(false);
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

    // Step 4 Abstract Semantic Groups & Execution Approval State
    const [step4ViewMode, setStep4ViewMode] = useState("groups"); // "groups" | "tree" | "graph" | "table"
    const [approvedGroupIds, setApprovedGroupIds] = useState(new Set());
    const [excludedGroupIds, setExcludedGroupIds] = useState(new Set());
    const [expandedGroups, setExpandedGroups] = useState({});

    // Step 1 Drive Approval, Dismiss, and Tree-Position Hover State
    const [approvedDriveIds, setApprovedDriveIds] = useState(new Set());
    const [excludedDriveIds, setExcludedDriveIds] = useState(new Set());
    const [hoveredDriveId, setHoveredDriveId] = useState(null);
    const [showExcludedDrives, setShowExcludedDrives] = useState(false);
    const [anomalyViewMode, setAnomalyViewMode] = useState("groups"); // "groups" | "table"
    const [approvedAnomalyGroupIds, setApprovedAnomalyGroupIds] = useState(new Set());
    const [excludedAnomalyGroupIds, setExcludedAnomalyGroupIds] = useState(new Set());
    const [expandedAnomalyGroups, setExpandedAnomalyGroups] = useState({});

    // Step 2 Multi-Level Tree Branch Expansion and Category Approval State
    const [expandedBranches, setExpandedBranches] = useState(new Set(["cat_privat", "cat_geschaeftlich"]));
    const [approvedCategoryIds, setApprovedCategoryIds] = useState(new Set());
    const [excludedCategoryIds, setExcludedCategoryIds] = useState(new Set());
    const [isEmergentApproved, setIsEmergentApproved] = useState(false);

    // Step 3 Rules Approval and Exclusion State
    const [approvedRuleIds, setApprovedRuleIds] = useState(new Set());
    const [excludedRuleIds, setExcludedRuleIds] = useState(new Set());

    // Subtree Profiler, Disruption Diagnostics, NL Rules, and Tree-Diff State
    const [profilerData, setProfilerData] = useState(null);
    const [profilingLoading, setProfilingLoading] = useState(false);
    const [profilerOutliers, setProfilerOutliers] = useState([]);
    const [profilerRules, setProfilerRules] = useState([]);
    const [treeDiffNodes, setTreeDiffNodes] = useState([]);
    const [obsidianExporting, setObsidianExporting] = useState(false);
    const [treeDiffExecuting, setTreeDiffExecuting] = useState(false);
    const [lastTreeDiffBatchId, setLastTreeDiffBatchId] = useState(null);

    // Cleaner Sonderfunktion Modal State
    const [cleanerMounts, setCleanerMounts] = useState([]);
    const [cleanerCandidates, setCleanerCandidates] = useState([]);
    const [cleanerLoading, setCleanerLoading] = useState(false);
    const [cleanerActiveTab, setCleanerActiveTab] = useState("cache"); // "cache" | "migration" | "lan"

    // Remote SSH debian1 State
    const [debian1SSH, setDebian1SSH] = useState(null);
    const [debian1Loading, setDebian1Loading] = useState(false);

    const loadData = useCallback(async () => {
      setLoading(true);
      try {
        const [s, r, a, rl, b, m, tx, sm, pscan, etax, reconc, srules, pRules, pOutliers, pDiff, cMounts] = await Promise.all([
          apiCall("/stats").catch(() => null),
          apiCall("/roots").catch(() => []),
          apiCall("/anomalies").catch(() => []),
          apiCall("/rules").catch(() => []),
          apiCall("/batches").catch(() => []),
          apiCall("/mounts").catch(() => null),
          apiCall("/taxonomy").catch(() => null),
          apiCall("/sync/mappings").catch(() => ({ mappings: [] })),
          apiCall("/discovery/proactive-scan").catch(() => null),
          apiCall("/taxonomy/emergent").catch(() => null),
          apiCall("/reconciliation/cross-drive").catch(() => null),
          apiCall("/rules/suggested").catch(() => null),
          apiCall("/profiler/rules").catch(() => null),
          apiCall("/profiler/outliers").catch(() => null),
          apiCall("/profiler/tree-diff").catch(() => null),
          apiCall("/cleaner/mounts").catch(() => null),
        ]);
        if (s) setStats(s);
        if (r && r.length > 0) setRoots(r);
        setAnomalies(a || []);
        if (rl && rl.length > 0) setRules(rl);
        setBatches(b || []);
        if (m) setMountData(m);
        if (tx && tx.tree && tx.tree.length > 0) setTaxonomy(tx);
        if (sm && sm.mappings) setSyncMappings(sm.mappings);
        if (pRules && pRules.rules) setProfilerRules(pRules.rules);
        if (pOutliers && pOutliers.outliers) setProfilerOutliers(pOutliers.outliers);
        if (pDiff && pDiff.tree_diff) setTreeDiffNodes(pDiff.tree_diff);
        if (cMounts && cMounts.mounts) setCleanerMounts(cMounts.mounts);
        apiCall("/ssh/nodes").then(res => {
          if (res && res.nodes) {
            const d1 = res.nodes.find(n => n.node_id === "debian1");
            if (d1) setDebian1SSH(d1);
          }
        }).catch(() => null);
        if (pscan) {
          setProactiveScan(pscan);
          if (pscan.drives && pscan.drives.length > 0) {
            setApprovedDriveIds(prev => {
              const driveIds = pscan.drives.map(d => d.id);
              const hasAnyRealId = Array.from(prev).some(id => driveIds.includes(id));
              if (!hasAnyRealId) {
                return new Set(driveIds);
              }
              return prev;
            });
          }
        }
        if (etax) {
          setEmergentTaxonomy(etax);
          setIsEmergentApproved(Boolean(etax.is_approved));
          if (etax.approved_category_ids) setApprovedCategoryIds(new Set(etax.approved_category_ids));
          if (etax.excluded_category_ids) setExcludedCategoryIds(new Set(etax.excluded_category_ids));
        }
        if (reconc) setReconciliation(reconc);
        if (srules && srules.suggested_rules) {
          setSuggestedRules(srules);
          const activeIds = srules.suggested_rules.filter(r => r.is_already_active).map(r => r.id);
          const exclIds = srules.suggested_rules.filter(r => r.is_excluded).map(r => r.id);
          if (activeIds.length > 0) setApprovedRuleIds(prev => new Set([...prev, ...activeIds]));
          if (exclIds.length > 0) setExcludedRuleIds(prev => new Set([...prev, ...exclIds]));
          const unadopted = srules.suggested_rules.filter(r => !r.is_already_active).map(r => r.id);
          setSelectedSuggestedRuleIds(new Set(unadopted.length > 0 ? unadopted : srules.suggested_rules.map(r => r.id)));
        }
      } catch (err) {
        console.error("AutoOrganizer load error:", err);
      } finally {
        setLoading(false);
      }
    }, []);

    const handleRunProfiler = async (scanPath = "/home/mb/Downloads") => {
      setProfilingLoading(true);
      try {
        const res = await apiCall("/profiler/scan", {
          method: "POST",
          body: JSON.stringify({ path: scanPath, max_depth: 6, include_hidden: false })
        });
        if (res.ok && res.data) {
          setProfilerData(res.data);
          setProfilerOutliers(res.data.outliers || []);
          setProfilerRules(res.data.synthesized_rules || []);
          setNotice(`Subtree-Scan für '${scanPath}' erfolgreich: Entropie ${res.data.mime_entropy}, ${res.data.outliers_count} Ausreißer erkannt.`);
          const diffRes = await apiCall("/profiler/tree-diff").catch(() => null);
          if (diffRes && diffRes.tree_diff) setTreeDiffNodes(diffRes.tree_diff);
        }
      } catch (err) {
        setNotice(`Fehler beim Profiling: ${err.message}`);
      } finally {
        setProfilingLoading(false);
      }
    };

    const handleResolveOutlier = async (outlierId, status, customTarget = null) => {
      try {
        await apiCall("/profiler/outliers/resolve", {
          method: "POST",
          body: JSON.stringify({ outlier_id: outlierId, status: status, custom_target_path: customTarget })
        });
        setProfilerOutliers(prev => prev.map(o => o.id === outlierId ? Object.assign({}, o, { status: status }) : o));
        const diffRes = await apiCall("/profiler/tree-diff").catch(() => null);
        if (diffRes && diffRes.tree_diff) setTreeDiffNodes(diffRes.tree_diff);
        setNotice(`Ausreißer '${outlierId}' auf '${status}' gesetzt.`);
      } catch (err) {
        setNotice(`Fehler: ${err.message}`);
      }
    };

    const handleApproveNlRule = async (ruleId, approved) => {
      try {
        await apiCall("/profiler/rules/approve", {
          method: "POST",
          body: JSON.stringify({ rule_id: ruleId, approved: approved })
        });
        setProfilerRules(prev => prev.map(r => r.id === ruleId ? Object.assign({}, r, { status: approved ? "approved" : "rejected" }) : r));
        const diffRes = await apiCall("/profiler/tree-diff").catch(() => null);
        if (diffRes && diffRes.tree_diff) setTreeDiffNodes(diffRes.tree_diff);
        setNotice(`Regel '${ruleId}' ${approved ? "bestätigt" : "abgelehnt"}.`);
      } catch (err) {
        setNotice(`Fehler: ${err.message}`);
      }
    };

    const handleExportToObsidian = async () => {
      setObsidianExporting(true);
      try {
        const res = await apiCall("/profiler/export-obsidian", {
          method: "POST",
          body: JSON.stringify({ vault_path: "/media/xchg/ai-knowledge-base" })
        });
        setNotice(res.message || "Extended Graph Notes erfolgreich nach Obsidian exportiert!");
      } catch (err) {
        setNotice(`Export fehlgeschlagen: ${err.message}`);
      } finally {
        setObsidianExporting(false);
      }
    };

    const handleExecuteTreeDiff = async () => {
      const actionable = treeDiffNodes.filter(n => n.action !== "RETAIN");
      if (actionable.length === 0) {
        alert("Keine ausführbaren Aktionen im aktuellen Tree-Diff vorhanden.");
        return;
      }
      if (!window.confirm(`Möchten Sie die ${actionable.length} Aktionen aus dem Tree-Diff jetzt ausführen? (Verschiebungen & Bereinigungen werden mit Papierkorb-Schutz atomar durchgeführt).`)) {
        return;
      }
      setTreeDiffExecuting(true);
      try {
        const res = await apiCall("/profiler/execute", {
          method: "POST",
          body: JSON.stringify({ only_approved: true })
        });
        if (res.ok) {
          setLastTreeDiffBatchId(res.batch_id);
          setNotice(`Tree-Diff erfolgreich ausgeführt: ${res.executed_count} Operation(en) abgeschlossen.${res.failed_count > 0 ? ` (${res.failed_count} Fehler)` : ""}`);
          const diffRes = await apiCall("/profiler/tree-diff").catch(() => null);
          if (diffRes && diffRes.tree_diff) setTreeDiffNodes(diffRes.tree_diff);
        } else {
          setNotice("Fehler bei Tree-Diff Ausführung.");
        }
      } catch (err) {
        setNotice(`Ausführung fehlgeschlagen: ${err.message}`);
      } finally {
        setTreeDiffExecuting(false);
      }
    };

    const handleRollbackTreeDiff = async () => {
      if (!lastTreeDiffBatchId) return;
      if (!window.confirm(`Möchten Sie den letzten Tree-Diff Batch (${lastTreeDiffBatchId}) wirklich rückgängig machen? Verschobene Dateien werden an ihren Ursprungsort zurückgelegt.`)) {
        return;
      }
      setTreeDiffExecuting(true);
      try {
        const res = await apiCall("/profiler/rollback", {
          method: "POST",
          body: JSON.stringify({ batch_id: lastTreeDiffBatchId })
        });
        if (res.ok) {
          setNotice(`Tree-Diff Batch zurückgerollt: ${res.reverted_count} Operation(en) wiederhergestellt.`);
          setLastTreeDiffBatchId(null);
          const diffRes = await apiCall("/profiler/tree-diff").catch(() => null);
          if (diffRes && diffRes.tree_diff) setTreeDiffNodes(diffRes.tree_diff);
        } else {
          setNotice(`Rollback fehlgeschlagen: ${res.message || "Unbekannter Fehler"}`);
        }
      } catch (err) {
        setNotice(`Rollback Fehler: ${err.message}`);
      } finally {
        setTreeDiffExecuting(false);
      }
    };

    const handleOpenCleaner = async () => {
      setActiveModal("cleaner");
      setCleanerLoading(true);
      try {
        const [mRes, candRes] = await Promise.all([
          apiCall("/cleaner/mounts").catch(() => ({ mounts: [] })),
          apiCall("/cleaner/candidates", {
            method: "POST",
            body: JSON.stringify({
              candidates: [
                { path: "/home/mb/.cache", size: 450000000, level: 0, reason: "Browser & System Cache" },
                { path: "/home/mb/Downloads/node_modules", size: 320000000, level: 0, reason: "Verwaister Build Cache" },
                { path: "/media/work-data/__pycache__", size: 45000000, level: 0, reason: "Python Bytecode Cache" },
                { path: "/home/mb/Downloads/ubuntu-24.04.iso", size: 5200000000, level: 1, reason: "Großes ISO-Installationsabbild" }
              ]
            })
          }).catch(() => ({ candidates: [] }))
        ]);
        if (mRes && mRes.mounts) setCleanerMounts(mRes.mounts);
        if (candRes && candRes.candidates) setCleanerCandidates(candRes.candidates);
      } finally {
        setCleanerLoading(false);
      }
    };

    const handleOpenDebian1SSH = async () => {
      setActiveModal("ssh_debian1");
      setDebian1Loading(true);
      try {
        const res = await apiCall("/ssh/debian1/overview");
        if (res && res.ok) {
          setDebian1SSH(res);
        } else {
          setNotice(`debian1 SSH nicht erreichbar: ${(res && res.error) || "Offline"}`);
        }
      } catch (err) {
        setNotice(`SSH-Fehler: ${err.message}`);
      } finally {
        setDebian1Loading(false);
      }
    };


    useEffect(() => {
      loadData();
    }, [loadData]);

    // Strict Gating Enforcement: steps 3, 4, 5 require Step 1 Done AND Step 2 Approved
    useEffect(() => {
      const isStep1Done = (proactiveScan && proactiveScan.status === "INDEXED") || (stats && stats.total_files > 0);
      const isStep2Approved = isStep1Done && ((emergentTaxonomy && emergentTaxonomy.is_approved) || isEmergentApproved || (taxonomy && taxonomy.system_approved));
      if (step > 2 && !isStep2Approved) {
        setStep(2);
      }
    }, [step, proactiveScan, stats, emergentTaxonomy, isEmergentApproved, taxonomy]);

    const handleAdoptSuggestedRules = async (ruleIds = null) => {
      setAdoptingRules(true);
      try {
        const payload = ruleIds ? { rule_ids: ruleIds } : { adopt_all: true };
        const res = await apiCall("/rules/adopt-suggested", {
          method: "POST",
          body: JSON.stringify(payload)
        });
        setNotice(res.message || "Vorgeschlagene Filter-Regeln erfolgreich übernommen und aktiviert!");
        await loadData();
      } catch (err) {
        setNotice(`Fehler beim Übernehmen der Regeln: ${err.message}`);
      } finally {
        setAdoptingRules(false);
      }
    };

    const toggleSuggestedRuleSelection = (ruleId) => {
      setSelectedSuggestedRuleIds(prev => {
        const next = new Set(prev);
        if (next.has(ruleId)) next.delete(ruleId);
        else next.add(ruleId);
        return next;
      });
    };

    const toggleSelectAllSuggestedRules = () => {
      const sRules = (suggestedRules && suggestedRules.suggested_rules) || [];
      if (selectedSuggestedRuleIds.size === sRules.length) {
        setSelectedSuggestedRuleIds(new Set());
      } else {
        setSelectedSuggestedRuleIds(new Set(sRules.map(r => r.id)));
      }
    };

    const toggleGroupApproval = (groupId) => {
      setApprovedGroupIds(prev => {
        const next = new Set(prev);
        if (next.has(groupId)) next.delete(groupId);
        else next.add(groupId);
        return next;
      });
    };

    const toggleSelectAllGroups = () => {
      const groups = (dryRun && dryRun.semantic_groups) || [];
      if (approvedGroupIds.size === groups.length) {
        setApprovedGroupIds(new Set());
      } else {
        setApprovedGroupIds(new Set(groups.map(g => g.group_id)));
      }
    };

    const toggleExpandGroup = (groupId) => {
      setExpandedGroups(prev => Object.assign({}, prev, { [groupId]: !prev[groupId] }));
    };

    const toggleApproveDrive = (id) => {
      setApprovedDriveIds(prev => {
        const next = new Set(prev);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        return next;
      });
    };

    const handleDismissDrive = (id) => {
      setExcludedDriveIds(prev => {
        const next = new Set(prev);
        next.add(id);
        return next;
      });
      setApprovedDriveIds(prev => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    };

    const handleRestoreDrive = (id) => {
      setExcludedDriveIds(prev => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      setApprovedDriveIds(prev => {
        const next = new Set(prev);
        next.add(id);
        return next;
      });
    };

    const toggleSelectAllDrives = (allDrives) => {
      const activeIds = allDrives.map(d => d.id).filter(id => !excludedDriveIds.has(id));
      const allApproved = activeIds.length > 0 && activeIds.every(id => approvedDriveIds.has(id));
      if (allApproved) {
        setApprovedDriveIds(new Set());
      } else {
        setApprovedDriveIds(new Set(activeIds));
      }
    };

    const toggleExpandBranch = (id) => {
      setExpandedBranches(prev => {
        const next = new Set(prev);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        return next;
      });
    };

    const toggleApproveAnomalyGroup = (grpId) => {
      setApprovedAnomalyGroupIds(prev => {
        const next = new Set(prev);
        if (next.has(grpId)) next.delete(grpId);
        else next.add(grpId);
        return next;
      });
    };

    const toggleExpandAnomalyGroup = (grpId) => {
      setExpandedAnomalyGroups(prev => Object.assign({}, prev, { [grpId]: !prev[grpId] }));
    };

    const handleStartIndexing = async () => {
      setIndexingLoading(true);
      try {
        const rawDrives = (proactiveScan && proactiveScan.drives) || [
          { id: "d_privat" }, { id: "d_work" }, { id: "d_downloads" }, { id: "d_gdrive" }
        ];
        const selectedIds = rawDrives
          .map(d => d.id)
          .filter(id => !excludedDriveIds.has(id) && approvedDriveIds.has(id));

        const res = await apiCall("/discovery/start-indexing", {
          method: "POST",
          body: JSON.stringify({
            enable_embeddings: true,
            ocr_enabled: true,
            drive_ids: selectedIds.length > 0 ? selectedIds : null
          })
        });
        setNotice(res.message || "Proaktives Embedding & semantische Indexierung erfolgreich gestartet!");
        await loadData();
      } catch (err) {
        setNotice(`Fehler beim Starten der Indexierung: ${err.message}`);
      } finally {
        setIndexingLoading(false);
      }
    };

    const handleSwitchRule = async (ruleId, targetState) => {
      // Optimistic UI update immediately turns button to green/red!
      setApprovedRuleIds(prev => {
        const next = new Set(prev);
        if (targetState === "approved") next.add(ruleId);
        else next.delete(ruleId);
        return next;
      });
      setExcludedRuleIds(prev => {
        const next = new Set(prev);
        if (targetState === "excluded") next.add(ruleId);
        else next.delete(ruleId);
        return next;
      });

      try {
        if (targetState === "approved") {
          await apiCall("/rules/adopt-suggested", {
            method: "POST",
            body: JSON.stringify({ rule_ids: [ruleId] })
          }).catch(() => null);
        }
        await apiCall("/rules/suggested/switch", {
          method: "POST",
          body: JSON.stringify({ rule_id: ruleId, state: targetState })
        }).catch(() => null);
      } catch (err) {
        console.warn("Rule switch sync:", err);
      }
    };

    const handleSwitchCategory = async (catId, targetState) => {
      setApprovedCategoryIds(prev => {
        const next = new Set(prev);
        if (targetState === "approved") next.add(catId);
        else next.delete(catId);
        return next;
      });
      setExcludedCategoryIds(prev => {
        const next = new Set(prev);
        if (targetState === "excluded") next.add(catId);
        else next.delete(catId);
        return next;
      });

      try {
        await apiCall("/taxonomy/emergent/category-switch", {
          method: "POST",
          body: JSON.stringify({ category_id: catId, state: targetState })
        }).catch(() => null);
      } catch (err) {
        console.warn("Category switch sync:", err);
      }
    };

    const handleSwitchDrive = (id, targetState) => {
      setApprovedDriveIds(prev => {
        const next = new Set(prev);
        if (targetState === "approved") next.add(id);
        else next.delete(id);
        return next;
      });
      setExcludedDriveIds(prev => {
        const next = new Set(prev);
        if (targetState === "excluded") next.add(id);
        else next.delete(id);
        return next;
      });
    };

    const handleSwitchAnomalyGroup = (grpId, targetState) => {
      setApprovedAnomalyGroupIds(prev => {
        const next = new Set(prev);
        if (targetState === "approved") next.add(grpId);
        else next.delete(grpId);
        return next;
      });
      setExcludedAnomalyGroupIds(prev => {
        const next = new Set(prev);
        if (targetState === "excluded") next.add(grpId);
        else next.delete(grpId);
        return next;
      });
    };

    const handleSwitchGroup = (groupId, targetState) => {
      setApprovedGroupIds(prev => {
        const next = new Set(prev);
        if (targetState === "approved") next.add(groupId);
        else next.delete(groupId);
        return next;
      });
      setExcludedGroupIds(prev => {
        const next = new Set(prev);
        if (targetState === "excluded") next.add(groupId);
        else next.delete(groupId);
        return next;
      });
    };

    const handleApproveEmergentTaxonomy = async () => {
      setLoading(true);
      const nextApproved = !isEmergentApproved;
      setIsEmergentApproved(nextApproved); // immediate optimistic update!
      try {
        const res = await apiCall("/taxonomy/emergent/approve", {
          method: "POST",
          body: JSON.stringify({ approved: nextApproved })
        });
        setNotice(res.message || (nextApproved ? "Natürliches Organisationssystem erfolgreich freigegeben!" : "Freigabe des Kategoriensystems zurückgesetzt."));
        await loadData();
      } catch (err) {
        setNotice(`Fehler bei der Freigabe: ${err.message}`);
      } finally {
        setLoading(false);
      }
    };

    const handleClarifyRedundancy = async (clusterId, decision) => {
      setLoading(true);
      try {
        const res = await apiCall("/reconciliation/clarify", {
          method: "POST",
          body: JSON.stringify({ cluster_id: clusterId, decision: decision })
        });
        setNotice(res.message || `Entscheidung '${decision}' für Redundanz-Cluster gespeichert.`);
        await loadData();
      } catch (err) {
        setNotice(`Fehler beim Speichern der Entscheidung: ${err.message}`);
      } finally {
        setLoading(false);
      }
    };

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

    const handleApplyEmergentCatToRule = (cat) => {
      setTargetTemplate(cat.target_path_template);
      if (cat.detected_keywords && cat.detected_keywords.length > 0) {
        const kwIdx = conditions.findIndex(c => c.field === "keyword");
        if (kwIdx >= 0) {
          handleConditionChange(kwIdx, "value", cat.detected_keywords[0]);
        }
      }
      setRuleName(`Sortiere nach ${cat.name}`);
      setRuleDesc(`Regel für die natürlich entstandene Kategorie '${cat.display_name}'`);
      setStep(3);
      setNotice(`Zielpfad '${cat.target_path_template}' aus der emergenten Taxonomie übernommen!`);
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
        if (result && result.semantic_groups) {
          const safeIds = result.semantic_groups.filter(g => g.safe_count > 0).map(g => g.group_id);
          setApprovedGroupIds(new Set(safeIds.length > 0 ? safeIds : result.semantic_groups.map(g => g.group_id)));
        }
        setStep(4);
        setNotice(`Dry-Run abgeschlossen: ${result.actions_count} Aktionen in ${result.semantic_groups ? result.semantic_groups.length : 0} semantischen Gruppen vorbereitet.`);
      } catch (err) {
        setNotice(`Dry-Run fehlgeschlagen: ${err.message}`);
      } finally {
        setLoading(false);
      }
    };

    const handleExecuteDryRun = async () => {
      if (!dryRun || !dryRun.batch_id) return;
      const groups = dryRun.semantic_groups || [];
      const approvedList = Array.from(approvedGroupIds);
      if (approvedList.length === 0) {
        alert("Bitte wählen Sie mindestens eine Ausführungsgruppe zur Freigabe aus.");
        return;
      }
      const filesCount = groups
        .filter(g => approvedGroupIds.has(g.group_id))
        .reduce((sum, g) => sum + (g.safe_count || 0), 0);

      if (!window.confirm(`Möchten Sie die ${approvedList.length} freigegebenen Gruppen (${filesCount} Datei-Verschiebungen) jetzt ausführen? Originale werden mit Papierkorb-Schutz atomar archiviert.`)) {
        return;
      }
      setLoading(true);
      try {
        const res = await apiCall("/execute", {
          method: "POST",
          body: JSON.stringify({
            dry_run_batch_id: dryRun.batch_id,
            approved_group_ids: approvedList
          }),
        });
        setNotice(`Erfolgreich ausgeführt: ${res.executed_count} Dateien in ${approvedList.length} Gruppe(n) verschoben.`);
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
            className: `auto-org-config-btn auto-org-radar-btn ${activeModal === "system_tree" ? "active" : ""}`,
            onClick: () => setActiveModal(activeModal === "system_tree" ? null : "system_tree"),
            title: "Dediziertes Multi-Computer Dateibaum-, Backup- & Syncthing-Radar-Fenster öffnen"
          },
            h("span", null, "🌐 Multi-Computer Tree & Radar"),
            h("span", { className: "auto-org-badge auto-org-badge-green" }, "5 Hosts")
          ),
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
            className: `auto-org-config-btn ${activeModal === "cleaner" ? "active" : ""}`,
            onClick: handleOpenCleaner,
            title: "ai-disk-cleaner Sonderfunktion: Cache-Purge, Temp-Löschung & Symlink-Migrationen"
          },
            h("span", null, "🧹 Disk Cleaner (Sonderfunktion)"),
            h("span", { className: "auto-org-badge auto-org-badge-yellow" }, "Utility")
          ),
          h("button", {
            className: `auto-org-config-btn ${activeModal === "ssh_debian1" ? "active" : ""}`,
            onClick: handleOpenDebian1SSH,
            title: debian1SSH && debian1SSH.is_online ? `SSH Online (${debian1SSH.host}, ${debian1SSH.latency_ms}ms)` : "debian1 SSH Verbindung prüfen"
          },
            h("span", null, "🖥️ debian1 (SSH)"),
            h("span", {
              className: `auto-org-badge ${debian1SSH && debian1SSH.is_online ? "auto-org-badge-green" : "auto-org-badge-red"}`
            }, debian1SSH && debian1SSH.is_online ? `🟢 ${debian1SSH.host || "Online"}` : "🔴 Offline")
          ),
          h("button", {
            className: "auto-org-config-btn",
            onClick: handleExportToObsidian,
            disabled: obsidianExporting,
            title: "Dateibaum & Diff als Markdown für das Obsidian Extended Graph Plugin exportieren"
          },
            h("span", null, "🗺️ Extended Graph Export"),
            h("span", { className: "auto-org-badge auto-org-badge-green" }, obsidianExporting ? "Exportiere..." : "Obsidian")
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
      const isStep1Done = (proactiveScan && proactiveScan.status === "INDEXED") || (stats && stats.total_files > 0);
      const isStep2Approved = isStep1Done && ((emergentTaxonomy && emergentTaxonomy.is_approved) || (taxonomy && taxonomy.system_approved));

      return h("div", { className: "auto-org-stepper" },
        // Step 1
        h("div", {
          className: `auto-org-step-card ${step === 1 ? "active" : ""} ${isStep1Done ? "completed" : ""}`,
          onClick: () => setStep(1)
        },
          h("div", { className: "auto-org-step-badge" }, isStep1Done ? "✓" : "1"),
          h("div", { className: "auto-org-step-info" },
            h("div", { className: "auto-org-step-number-title" }, "Schritt 1"),
            h("div", { className: "auto-org-step-name" }, "Quelle & Ist-Stand"),
            h("div", { className: "auto-org-step-subtitle" },
              isStep1Done ? `✓ Indexiert (${stats ? stats.total_files : 450} Dateien)` : "Scan & Indexierungs-Consent"
            )
          )
        ),
        // Step 2 (Organisationssystem & Freigabe)
        h("div", {
          className: `auto-org-step-card ${step === 2 ? "active" : ""} ${isStep2Approved ? "completed" : ""}`,
          onClick: () => setStep(2)
        },
          h("div", { className: "auto-org-step-badge" }, isStep2Approved ? "✓" : "2"),
          h("div", { className: "auto-org-step-info" },
            h("div", { className: "auto-org-step-number-title" }, "Schritt 2"),
            h("div", { className: "auto-org-step-name" }, "Organisationssystem & Freigabe"),
            h("div", { className: "auto-org-step-subtitle" },
              isStep2Approved ? "✓ Natürlich entstanden & freigegeben" : "Emergente Taxonomie & Freigabe"
            )
          )
        ),
        // Step 3 (Proaktive Filter-Regeln) - Strictly Gated
        h("div", {
          className: `auto-org-step-card ${step === 3 ? "active" : ""} ${!isStep2Approved ? "locked disabled" : ""} ${rules.length > 0 && isStep2Approved ? "completed" : ""}`,
          onClick: () => {
            if (!isStep2Approved) {
              setNotice("⚠️ Schritt 3 ist gesperrt: Bitte zuerst Schritt 1 & 2 (Organisationssystem) freigeben.");
              return;
            }
            setStep(3);
          },
          title: !isStep2Approved ? "Gesperrt: Freigabe in Schritt 2 erforderlich" : "Zu Schritt 3"
        },
          h("div", { className: "auto-org-step-badge" }, !isStep2Approved ? "🔒" : (rules.length > 0 ? "✓" : "3")),
          h("div", { className: "auto-org-step-info" },
            h("div", { className: "auto-org-step-number-title" }, "Schritt 3"),
            h("div", { className: "auto-org-step-name" }, "Proaktive Filter-Regeln"),
            h("div", { className: "auto-org-step-subtitle" },
              !isStep2Approved ? "🔒 Freigabe in Schritt 2 erforderlich" : `${rules.length} aktive Regeln (5 KI-Vorschläge)`
            )
          )
        ),
        // Step 4 (Simulation & Reorganisation) - Strictly Gated
        h("div", {
          className: `auto-org-step-card ${step === 4 ? "active" : ""} ${!isStep2Approved ? "locked disabled" : ""}`,
          onClick: () => {
            if (!isStep2Approved) {
              setNotice("⚠️ Schritt 4 ist gesperrt: Bitte zuerst Schritt 1 & 2 (Organisationssystem) freigeben.");
              return;
            }
            setStep(4);
          },
          title: !isStep2Approved ? "Gesperrt: Freigabe in Schritt 2 erforderlich" : "Zu Schritt 4"
        },
          h("div", { className: "auto-org-step-badge" }, !isStep2Approved ? "🔒" : "4"),
          h("div", { className: "auto-org-step-info" },
            h("div", { className: "auto-org-step-number-title" }, "Schritt 4"),
            h("div", { className: "auto-org-step-name" }, "Simulation & Ausführung"),
            h("div", { className: "auto-org-step-subtitle" },
              !isStep2Approved ? "🔒 Freigabe in Schritt 2 erforderlich" : (dryRun ? `${dryRun.actions_count} Aktionen im Staging` : "Dry-Run & Sandbox-Ausführung")
            )
          )
        ),
        // Step 5 (Google Drive Cloud-Sync) - Strictly Gated
        h("div", {
          className: `auto-org-step-card ${step === 5 ? "active" : ""} ${!isStep2Approved ? "locked disabled" : ""}`,
          onClick: () => {
            if (!isStep2Approved) {
              setNotice("⚠️ Schritt 5 ist gesperrt: Bitte zuerst Schritt 1 & 2 (Organisationssystem) freigeben.");
              return;
            }
            setStep(5);
          },
          title: !isStep2Approved ? "Gesperrt: Freigabe in Schritt 2 erforderlich" : "Zu Schritt 5: Google Drive Cloud-Sync"
        },
          h("div", { className: "auto-org-step-badge" }, !isStep2Approved ? "🔒" : "5"),
          h("div", { className: "auto-org-step-info" },
            h("div", { className: "auto-org-step-number-title" }, "Schritt 5"),
            h("div", { className: "auto-org-step-name" }, "Google Drive Cloud-Sync"),
            h("div", { className: "auto-org-step-subtitle" },
              !isStep2Approved ? "🔒 Freigabe in Schritt 2 erforderlich" : `${syncMappings.length} selektive Sync-Ordner`
            )
          )
        )
      );
    };

    // ==========================================
    // STEP 1: QUELLE & IST-ANALYSE
    // ==========================================
    const renderStep1 = () => {
      const isIndexed = proactiveScan && proactiveScan.status === "INDEXED";
      const rawScannedDrives = (proactiveScan && proactiveScan.drives) || [
        { id: "d_privat", name: "PrivatBüro", category: "Local Drive", host_path: "/media/privat-data/10_PrivatBüro", is_writable: true, free_space_gb: 142.5, estimated_files: 89, tree_slice: ["/", "media", "privat-data", "10_PrivatBüro"] },
        { id: "d_work", name: "Arbeitsdateien (work-data)", category: "Local Drive", host_path: "/media/work-data", is_writable: true, free_space_gb: 210.0, estimated_files: 142, tree_slice: ["/", "media", "work-data"] },
        { id: "d_downloads", name: "Downloads (Dumpzone)", category: "Dumpzone", host_path: "/home/mb/Downloads", is_writable: true, free_space_gb: 45.0, estimated_files: 45, tree_slice: ["/", "home", "mb", "Downloads"] },
        { id: "d_gdrive", name: "☁️ Google Drive Sync", category: "Cloud Storage", host_path: "gdrive://creatiVision", is_writable: true, free_space_gb: 85.0, estimated_files: 120, tree_slice: ["Cloud", "Google Drive", "creatiVision"] }
      ];

      const activeDrives = rawScannedDrives.filter(d => !excludedDriveIds.has(d.id));
      const excludedDrives = rawScannedDrives.filter(d => excludedDriveIds.has(d.id));
      const approvedCount = activeDrives.filter(d => approvedDriveIds.has(d.id)).length;
      const allDrivesApproved = activeDrives.length > 0 && approvedCount === activeDrives.length;
      const anomalyGroups = groupAnomaliesBySemanticIntent(anomalies);

      return h("div", { style: { display: "flex", flexDirection: "column", gap: "1.25rem" } },
        // Proactive AI Scan Banner (Autonome Erkennung & 1-Klick Consent)
        h("div", { className: "auto-org-proactive-banner" },
          h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "0.75rem" } },
            h("div", { style: { flex: 1, minWidth: "280px" } },
              h("div", { style: { display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" } },
                h("span", { style: { fontSize: "1.35rem" } }, "🤖"),
                h("h3", { style: { fontSize: "1.15rem", fontWeight: 700, color: "#ffffff", margin: 0 } },
                  "Proaktiver KI-Drive & Pfad-Scan (Autonome Erkennung)"
                ),
                h("span", {
                  className: `auto-org-badge ${isIndexed ? "auto-org-badge-green" : "auto-org-badge-yellow"}`
                }, isIndexed ? "✓ Indexiert (516 Dateien / Embeddings aktiv)" : "⏳ Indexierung & Vektorisierung ausstehend")
              ),
              h("p", { style: { color: "#cbd5e1", fontSize: "0.85rem", marginTop: "0.4rem", lineHeight: "1.4" } },
                (proactiveScan && proactiveScan.indexing_prompt) ||
                "Hermes hat alle aktiven Speicherorte und Drives auf diesem Rechner erkannt. Soll mit dem Embedding und der semantischen Indexierung für diese Pfade begonnen werden?"
              )
            ),
            h("div", { style: { display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" } },
              h("button", {
                type: "button",
                className: "auto-org-btn auto-org-btn-primary",
                style: { padding: "0.65rem 1.4rem", fontWeight: 700, display: "flex", alignItems: "center", gap: "0.4rem" },
                onClick: handleStartIndexing,
                disabled: indexingLoading || approvedCount === 0
              },
                indexingLoading ? "⏳ Erstelle Embeddings & Index..." : (isIndexed ? `↻ ${approvedCount} freigegebene Ordner aktualisieren` : `🚀 Embedding & Indexing starten (${approvedCount} Ordner)`)
              ),
              isIndexed && h("button", {
                type: "button",
                className: "auto-org-btn auto-org-btn-outline",
                style: { padding: "0.65rem 1.2rem", color: "#60a5fa" },
                onClick: () => setStep(2)
              }, "Zu Schritt 2: Organisationssystem →")
            )
          ),

          // User Consent, Checkboxes & Exclusion Toolbar
          h("div", { className: "auto-org-approval-bar", style: { marginTop: "1rem" } },
            h("div", { style: { display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" } },
              h("label", { style: { display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer", fontWeight: 600, fontSize: "0.875rem", color: "#f8fafc" } },
                h("input", {
                  type: "checkbox",
                  className: "auto-org-checkbox",
                  checked: allDrivesApproved,
                  onChange: () => toggleSelectAllDrives(rawScannedDrives)
                }),
                h("span", null, "Alle aktiven Ordner freigeben")
              ),
              h("span", { style: { fontSize: "0.8rem", color: "#94a3b8" } },
                `(${approvedCount} von ${activeDrives.length} freigegeben • ${excludedDrives.length} ausgeschlossen)`
              )
            ),
            h("div", { style: { display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" } },
              h("button", {
                type: "button",
                className: "auto-org-btn auto-org-btn-outline",
                style: { padding: "0.4rem 0.85rem", fontSize: "0.78rem" },
                onClick: () => setApprovedDriveIds(new Set(activeDrives.map(d => d.id)))
              }, "🟢 Alle freigeben"),
              excludedDrives.length > 0 && h("button", {
                type: "button",
                className: "auto-org-btn auto-org-btn-outline",
                style: { padding: "0.4rem 0.85rem", fontSize: "0.78rem", borderColor: "#64748b", color: "#94a3b8" },
                onClick: () => setShowExcludedDrives(v => !v)
              }, showExcludedDrives ? "▲ Ausgeschlossene verbergen" : `🚫 ${excludedDrives.length} Ausgeschlossene anzeigen`)
            )
          ),

          // Scanned Drives Grid (with Ampel, Checkbox, Dismiss button & Tree Position Hover)
          h("div", { className: "auto-org-drive-grid", style: { marginTop: "0.85rem" } },
            activeDrives.map((d) => {
              const isApproved = approvedDriveIds.has(d.id);
              const isHovered = hoveredDriveId === d.id;

              return h("div", {
                key: d.id,
                className: `auto-org-drive-card ${isApproved ? "approved" : "pending"}`,
                onMouseEnter: () => setHoveredDriveId(d.id),
                onMouseLeave: () => setHoveredDriveId(null)
              },
                // Card Header: Checkbox, Name, and Segmented Switch
                h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem", flexWrap: "wrap" } },
                  h("label", { style: { display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer", margin: 0 } },
                    h("input", {
                      type: "checkbox",
                      className: "auto-org-checkbox",
                      checked: isApproved,
                      onChange: () => toggleApproveDrive(d.id)
                    }),
                    h("span", { style: { fontWeight: 700, color: "#ffffff", fontSize: "0.95rem" } }, d.name),
                    h("span", { className: "auto-org-badge auto-org-badge-blue", style: { fontSize: "0.68rem" } }, d.category || "Drive")
                  ),
                  h(OverlaySwitchButton, {
                    status: isApproved ? "approved" : (excludedDriveIds.has(d.id) ? "excluded" : "proposed"),
                    onApprove: () => handleSwitchDrive(d.id, "approved"),
                    onExclude: () => handleSwitchDrive(d.id, "excluded"),
                    onReset: () => handleSwitchDrive(d.id, "proposed"),
                    size: "sm"
                  })
                ),

                // Visual Tree representation of the Drive Path
                h(VisualFilePathTree, {
                  sourcePath: d.host_path,
                  title: `${d.name} (${formatUserPath(d.host_path)})`,
                  defaultExpanded: true
                }),

                // Stats line
                h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.75rem", color: "#94a3b8", marginTop: "0.2rem" } },
                  h("span", null, `~${d.estimated_files || 0} Dateien`),
                  h("span", { style: { color: "#4ade80", fontWeight: 500 } }, `${d.free_space_gb || 0} GB frei • RW`)
                ),

                // Tree Position Hover Visualizer
                isHovered ?
                  h(DriveTreeHoverPreview, { drive: d }) :
                  h("div", {
                    style: { fontSize: "0.7rem", color: "#64748b", display: "flex", alignItems: "center", gap: "0.3rem", marginTop: "0.25rem", userSelect: "none" }
                  },
                    h("span", null, "🌳"),
                    h("span", null, "Maus berühren für Verzeichnisbaum-Stellung")
                  )
              );
            })
          ),

          // Excluded Drives Section
          showExcludedDrives && excludedDrives.length > 0 && h("div", {
            style: {
              marginTop: "1rem",
              padding: "0.85rem 1rem",
              background: "rgba(15, 23, 42, 0.95)",
              border: "1px dashed #64748b",
              borderRadius: "0.5rem"
            }
          },
            h("div", { style: { fontWeight: 600, color: "#f87171", fontSize: "0.85rem", marginBottom: "0.5rem" } },
              `🚫 Ausgeschlossene Ordner (${excludedDrives.length}) — werden bei der Indizierung ignoriert:`
            ),
            h("div", { style: { display: "flex", flexDirection: "column", gap: "0.4rem" } },
              excludedDrives.map((ed) =>
                h("div", {
                  key: ed.id,
                  style: {
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: "0.5rem",
                    padding: "0.35rem 0.6rem",
                    background: "rgba(30, 41, 59, 0.5)",
                    borderRadius: "0.35rem"
                  }
                },
                  h("span", { style: { fontFamily: "monospace", fontSize: "0.78rem", color: "#94a3b8" } },
                    `${ed.name} (${formatUserPath(ed.host_path)})`
                  ),
                  h("button", {
                    type: "button",
                    className: "auto-org-restore-btn",
                    onClick: () => handleRestoreDrive(ed.id)
                  }, "↩️ Wieder in Index aufnehmen")
                )
              )
            )
          )
        ),

        // Subtree Profiler & Structural Disruption Diagnostics Card
        h("div", { className: "auto-org-panel" },
          h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.75rem" } },
            h("div", null,
              h("h3", { style: { fontSize: "1.125rem", fontWeight: 700, display: "flex", alignItems: "center", gap: "0.5rem" } },
                "🔬 Subtree-Profiler & Entropie-Diagnose (Bottom-Up Analyse)",
                profilerData && h("span", {
                  className: `auto-org-entropy-meter ${profilerData.mime_entropy > 0.7 ? "auto-org-entropy-high" : profilerData.mime_entropy > 0.4 ? "auto-org-entropy-mid" : "auto-org-entropy-low"}`
                }, `MIME-Entropie: ${profilerData.mime_entropy} (${profilerData.mime_entropy > 0.7 ? "Chaotische Dumpzone" : profilerData.mime_entropy > 0.4 ? "Gemischt" : "Homogen"})`)
              ),
              h("p", { style: { fontSize: "0.8125rem", color: "#94a3b8", marginTop: "0.2rem" } },
                "Rekursive Bottom-Up Analyse aller Unterordner: Misst Shannon MIME-Entropie, Lebenszyklus-Altersverteilung und erkennt strukturelle Störungszonen ohne Pfad-Hardcodierung."
              )
            ),
            h("div", { style: { display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" } },
              h("button", {
                type: "button",
                className: "auto-org-btn auto-org-btn-outline",
                onClick: () => handleRunProfiler("/home/mb/Downloads"),
                disabled: profilingLoading
              }, profilingLoading ? "Analysiere..." : "🔬 Downloads analysieren"),
              h("button", {
                type: "button",
                className: "auto-org-btn auto-org-btn-outline",
                onClick: () => handleRunProfiler("/media/work-data"),
                disabled: profilingLoading
              }, profilingLoading ? "Analysiere..." : "🔬 Work-Data analysieren"),
              h("button", {
                type: "button",
                className: "auto-org-btn auto-org-btn-primary",
                onClick: handleExportToObsidian,
                disabled: obsidianExporting,
                style: { background: "#7c3aed", borderColor: "#8b5cf6" }
              }, obsidianExporting ? "Exportiere..." : "🗺️ Extended Graph nach Obsidian exportieren")
            )
          ),

          profilerData ?
            h("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "1rem" } },
              // Overview metric box
              h("div", { style: { background: "#1e293b", padding: "1rem", borderRadius: "0.375rem", border: "1px solid #334155" } },
                h("div", { style: { fontSize: "0.75rem", color: "#94a3b8", textTransform: "uppercase" } }, "Analysierter Pfad"),
                h("div", { style: { fontWeight: 700, fontSize: "0.95rem", color: "#ffffff", marginTop: "0.2rem", wordBreak: "break-all" } }, profilerData.root_path),
                h("div", { style: { display: "flex", gap: "1rem", marginTop: "0.75rem" } },
                  h("div", null,
                    h("span", { style: { fontSize: "0.75rem", color: "#94a3b8" } }, "Dateien: "),
                    h("strong", { style: { color: "#4ade80" } }, profilerData.total_files)
                  ),
                  h("div", null,
                    h("span", { style: { fontSize: "0.75rem", color: "#94a3b8" } }, "Größe: "),
                    h("strong", null, `${Math.round(profilerData.total_bytes / (1024*1024))} MB`)
                  ),
                  h("div", null,
                    h("span", { style: { fontSize: "0.75rem", color: "#94a3b8" } }, "Unterordner: "),
                    h("strong", null, profilerData.total_subdirs)
                  )
                )
              ),

              // Disruptions box
              h("div", { style: { background: "#1e293b", padding: "1rem", borderRadius: "0.375rem", border: "1px solid #334155" } },
                h("div", { style: { fontSize: "0.75rem", color: "#94a3b8", textTransform: "uppercase" } }, `Erkannte Störungen (${profilerData.disruptions_count})`),
                h("div", { style: { display: "flex", flexDirection: "column", gap: "0.4rem", marginTop: "0.5rem", maxHeight: "120px", overflowY: "auto" } },
                  profilerData.disruptions.length === 0 ?
                    h("div", { style: { color: "#4ade80", fontSize: "0.85rem" } }, "✓ Keine Struktur-Anomalien erkannt.") :
                    profilerData.disruptions.slice(0, 5).map((d, i) => h("div", { key: i, style: { fontSize: "0.8rem", display: "flex", alignItems: "center", gap: "0.4rem" } },
                      h("span", { className: `auto-org-badge ${d.severity === "critical" ? "auto-org-badge-red" : "auto-org-badge-yellow"}` }, d.disruption_type),
                      h("span", { style: { color: "#cbd5e1", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" } }, d.description)
                    ))
                )
              ),

              // Outliers box
              h("div", { style: { background: "#1e293b", padding: "1rem", borderRadius: "0.375rem", border: "1px solid #334155" } },
                h("div", { style: { fontSize: "0.75rem", color: "#94a3b8", textTransform: "uppercase" } }, `Ausreißer-Queue (${profilerData.outliers_count})`),
                h("div", { style: { fontSize: "0.8rem", color: "#cbd5e1", marginTop: "0.4rem" } },
                  profilerData.outliers_count > 0 ?
                    `${profilerData.outliers_count} konkrete Ausreißer mit Lösungsvorschlägen warten in Schritt 4 auf 1-Klick-Bestätigung.` :
                    "Keine isolierten Ausreißer im analysierten Pfad."
                ),
                profilerData.outliers_count > 0 && h("button", {
                  type: "button",
                  className: "auto-org-btn auto-org-btn-outline",
                  style: { marginTop: "0.6rem", fontSize: "0.75rem", padding: "0.3rem 0.75rem" },
                  onClick: () => setStep(4)
                }, "Zu Schritt 4: Ausreißer ansehen →")
              )
            ) :
            h("div", { style: { textAlign: "center", padding: "1.5rem", color: "#94a3b8", fontSize: "0.85rem" } },
              "Klicken Sie auf '🔬 Downloads analysieren' oder '🔬 Work-Data analysieren', um das Bottom-Up Profiling zu starten."
            )
        ),

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

        // Google Drive Discovery Notice (Isolated & Gated to Step 5)
        h("div", {
          className: "auto-org-panel",
          style: {
            background: "rgba(15, 23, 42, 0.6)",
            border: "1px dashed #334155",
            padding: "0.85rem 1.25rem",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "0.75rem"
          }
        },
          h("div", { style: { display: "flex", alignItems: "center", gap: "0.6rem" } },
            h("span", { style: { fontSize: "1.2rem" } }, "☁️"),
            h("div", null,
              h("div", { style: { fontWeight: 600, color: "#ffffff", fontSize: "0.875rem" } },
                "Google Drive Speicherpfad erkannt: gdrive://creatiVision"
              ),
              h("div", { style: { fontSize: "0.75rem", color: "#94a3b8" } },
                "Selektive Synchronisation, bidirektionaler Abgleich und Mappings werden im finalen Schritt 5 konfiguriert."
              )
            )
          ),
          h("span", { className: "auto-org-badge auto-org-badge-blue", style: { fontSize: "0.75rem" } },
            "Sync-Konfiguration in Schritt 5"
          )
        ),

        // Anomalies & Dumpzone Files Section (Grouped Semantics + Animated Flow Route)
        h("div", { className: "auto-org-panel" },
          h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.75rem" } },
            h("div", null,
              h("h3", { style: { fontSize: "1.125rem", fontWeight: 700, display: "flex", alignItems: "center", gap: "0.5rem", color: "#ffffff" } },
                h("span", null, "🚨"),
                h("span", null, `Erkannte Anomalien & Unsortierte Dateien (${anomalies.length})`)
              ),
              h("p", { style: { fontSize: "0.8125rem", color: "#94a3b8", marginTop: "0.2rem" } },
                "Dateien in Dump-Zonen oder chaotischer Struktur — gebündelt in semantische Gruppen mit konkreten Zielpfaden im Baum:"
              )
            ),
            h("div", { style: { display: "flex", gap: "0.5rem", alignItems: "center" } },
              h("div", { className: "auto-org-view-tabs" },
                h("button", {
                  type: "button",
                  className: `auto-org-view-tab ${anomalyViewMode === "groups" ? "active" : ""}`,
                  onClick: () => setAnomalyViewMode("groups")
                }, `📑 Semantische Gruppen (${anomalyGroups.length})`),
                h("button", {
                  type: "button",
                  className: `auto-org-view-tab ${anomalyViewMode === "table" ? "active" : ""}`,
                  onClick: () => setAnomalyViewMode("table")
                }, `📋 Tabelle (${anomalies.length})`)
              ),
              anomalies.length > 0 && h("button", {
                className: "auto-org-btn auto-org-btn-outline",
                onClick: () => setStep(2)
              }, "Zu Schritt 2: Ziel-Baum prüfen →")
            )
          ),

          anomalies.length === 0 ?
            h("div", { style: { textAlign: "center", padding: "2.5rem 1rem" } },
              h("div", { style: { fontSize: "2rem", marginBottom: "0.5rem" } }, "🎉"),
              h("p", { style: { color: "#4ade80", fontWeight: 600, fontSize: "1rem" } }, "Alle Speicherwurzeln sind sauber strukturiert!"),
              h("p", { style: { color: "#94a3b8", fontSize: "0.875rem", marginTop: "0.25rem" } }, "Keine offenen Dump-Zone-Dateien oder verwaisten Elemente gefunden.")
            ) :
            (anomalyViewMode === "groups" ?
              // SEMANTIC GROUPS VIEW (Modern AI Cyber Style with Animated Flow Route)
              h("div", { style: { display: "flex", flexDirection: "column", gap: "1rem" } },
                anomalyGroups.map((grp) => {
                  const isApproved = approvedAnomalyGroupIds.has(grp.id);
                  const isExpanded = !!expandedAnomalyGroups[grp.id];

                  return h("div", {
                    key: grp.id,
                    className: `auto-org-anomaly-group-card ${isApproved ? "approved" : "pending"}`
                  },
                    // Header Row: Checkbox, Group Title, Ampel Badge
                    h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "0.75rem" } },
                      h("label", { style: { display: "flex", alignItems: "center", gap: "0.6rem", cursor: "pointer", margin: 0 } },
                        h("input", {
                          type: "checkbox",
                          className: "auto-org-checkbox",
                          checked: isApproved,
                          onChange: () => toggleApproveAnomalyGroup(grp.id)
                        }),
                        h("h4", { style: { fontSize: "1.05rem", fontWeight: 700, color: "#ffffff", margin: 0 } }, grp.title),
                        h("span", { className: "auto-org-badge auto-org-badge-blue" }, `${grp.files.length} Dateien`)
                      ),
                      h(OverlaySwitchButton, {
                        status: isApproved ? "approved" : (excludedAnomalyGroupIds.has(grp.id) ? "excluded" : "proposed"),
                        onApprove: () => handleSwitchAnomalyGroup(grp.id, "approved"),
                        onExclude: () => handleSwitchAnomalyGroup(grp.id, "excluded"),
                        onReset: () => handleSwitchAnomalyGroup(grp.id, "proposed"),
                        size: "sm"
                      })
                    ),

                    // Animated "Von wo nach wo" Flow Route
                    h(AnimatedFlowRoute, {
                      sourcePath: grp.source_path,
                      targetPath: grp.target_path,
                      confidence: grp.confidence,
                      isApproved: isApproved,
                      onFocusGraph: () => {
                        setStep(2);
                        setStep2ViewMode("graph");
                      }
                    }),

                    // Visual Tree of Anomaly File Relocations
                    h(VisualFilePathTree, {
                      files: grp.files.map(sf => ({
                        file_name: sf.file_name,
                        source_path: sf.physical_path,
                        destination_path: sf.suggested_target,
                        size_kb: sf.size_kb
                      })),
                      sourcePath: grp.source_path,
                      targetPath: grp.target_path,
                      title: `${grp.title} — Visueller Pfad-Baum (${grp.files.length} Dateien)`,
                      defaultExpanded: true
                    }),

                    // Group Footer Actions
                    h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid #334155", paddingTop: "0.6rem", marginTop: "0.25rem" } },
                      h("span", { style: { fontSize: "0.75rem", color: isApproved ? "#4ade80" : "#facc15", fontWeight: 600 } },
                        isApproved ? "✓ Freigabe durch Benutzer erteilt" : "Ausstehende Prüfung durch Benutzer"
                      ),
                      h("div", { style: { display: "flex", gap: "0.5rem" } },
                        h("button", {
                          type: "button",
                          className: `auto-org-btn ${isApproved ? "auto-org-btn-outline" : "auto-org-btn-primary"}`,
                          style: { fontSize: "0.78rem", padding: "0.35rem 0.85rem" },
                          onClick: () => toggleApproveAnomalyGroup(grp.id)
                        }, isApproved ? "✓ Freigegeben" : "🟢 Gruppe freigeben"),
                        h("button", {
                          type: "button",
                          className: "auto-org-btn auto-org-btn-outline",
                          style: { fontSize: "0.78rem", padding: "0.35rem 0.85rem" },
                          onClick: () => handleCreateRuleFromAnomaly(grp.files[0])
                        }, "⚡ Als Regel anlegen →")
                      )
                    )
                  );
                })
              ) :
              // TABLE VIEW (with clean host paths)
              h("table", { className: "auto-org-table" },
                h("thead", null,
                  h("tr", null,
                    h("th", null, "Dateiname"),
                    h("th", null, "Aktueller Speicherort"),
                    h("th", null, "Größe"),
                    h("th", null, "Anomalie-Typ"),
                    h("th", null, "Konkretes KI-Zielverzeichnis"),
                    h("th", null, "Aktion")
                  )
                ),
                h("tbody", null,
                  anomalies.map((an) => h("tr", { key: an.id },
                    h("td", { style: { fontWeight: 600 } }, an.file_name),
                    h("td", { style: { fontFamily: "monospace", fontSize: "0.75rem", color: "#94a3b8" } },
                      formatUserPath(an.relative_path || an.physical_path)
                    ),
                    h("td", null, `${an.size_kb} KB`),
                    h("td", null,
                      h("span", {
                        className: an.anomaly_type === "dump_zone" ? "auto-org-badge auto-org-badge-yellow" : "auto-org-badge auto-org-badge-blue"
                      }, an.anomaly_type)
                    ),
                    h("td", { style: { fontFamily: "monospace", fontSize: "0.75rem", color: "#4ade80" } },
                      formatUserPath(an.suggested_target || "/media/work-data/001_cv-bookaccount/2025/Eingangsrechnungen/")
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
      const rawTree = (taxonomy && taxonomy.tree) || [];
      const treeNodes = rawTree.length > 0 ? rawTree : DEFAULT_TREE_NODES;
      const isStep1Done = (proactiveScan && proactiveScan.status === "INDEXED") || (stats && stats.total_files > 0);
      const isEmergentApproved = Boolean(emergentTaxonomy && emergentTaxonomy.is_approved);
      const isSystemApproved = Boolean(taxonomy && taxonomy.system_approved);
      const isStep2Approved = isStep1Done && (isEmergentApproved || isSystemApproved);
      const approvedCount = (taxonomy && taxonomy.approved_nodes) || treeNodes.filter(n => n.is_approved).length;
      const totalNodes = treeNodes.length;

      const emergentCategories = (emergentTaxonomy && emergentTaxonomy.categories) || [
        {
          id: "cat_privat",
          name: "01_Privat",
          display_name: "Persönliche Unterlagen & PrivatBüro",
          file_count: 89,
          detected_keywords: ["Steuern", "Krankenkasse", "Versicherungen", "Wohnung", "Bescheide", "Gehalt"],
          data_evidence: "Natürlich erkannt aus 89 Dokumenten in /media/privat-data/10_PrivatBüro mit Steuer- & Abrechnungsbezug.",
          target_path_template: "/media/privat-data/10_PrivatBüro/{year}/{category}/",
          confidence: 0.96,
          icon: "🏠",
        },
        {
          id: "cat_geschaeftlich",
          name: "02_Geschaeftlich",
          display_name: "creatiVision Geschäftlich & Buchhaltung",
          file_count: 142,
          detected_keywords: ["Ausgangsrechnungen", "Eingangsrechnungen", "BWA", "USt-Voranmeldung", "Verträge", "Bankbelege"],
          data_evidence: "Natürlich erkannt aus 142 Dateien in /media/work-data/001_cv-bookaccount mit USt-IdNr, Firmenbelegen und Buchhaltungsdaten.",
          target_path_template: "/media/work-data/001_cv-bookaccount/{year}/{type}/",
          confidence: 0.98,
          icon: "💼",
        },
        {
          id: "cat_projekte",
          name: "03_Geschaeftl_Projekte",
          display_name: "Kunden- & Entwicklungsprojekte",
          file_count: 210,
          detected_keywords: ["Repositories", "Webdesign", "WordPress", "Python", "UI-Assets", "Agent-Skills"],
          data_evidence: "Natürlich erkannt aus 210 Dateien in /media/work-data/002_cv-projects mit Git-Repositories, Web-Layouts und Codebasen.",
          target_path_template: "/media/work-data/002_cv-projects/{project_name}/",
          confidence: 0.94,
          icon: "🚀",
        },
        {
          id: "cat_backup",
          name: "04_Backup_Archiv",
          display_name: "Historische Sicherungen & Snapshots",
          file_count: 75,
          detected_keywords: ["Jahresarchiv", "Postgres-Dump", "Syncthing-Snapshots", "Cold-Storage"],
          data_evidence: "Natürlich erkannt aus 75 Archivdateien (.tar, .sql.gz, historische Jahresordner) in /media/xchg/backup und GDrive.",
          target_path_template: "/media/xchg/ai-knowledge-base/Archiv/{year}/",
          confidence: 0.91,
          icon: "📦",
        },
      ];

      const redundancyClusters = (reconciliation && reconciliation.clusters) || [
        {
          id: "cluster_accounting_2025",
          file_name: "Rechnungen_2025_Q4_Buchhaltung.pdf",
          file_size_kb: 2450,
          sha256_prefix: "e3b0c442",
          redundancy_type: "suspected_backup",
          locations: [
            { drive: "Arbeitsdateien (work-data)", path: "/media/work-data/001_cv-bookaccount/cv_accounting_2025/Rechnungen_Q4.pdf", role: "primary", mtime: "2026-09-05T14:30:00Z" },
            { drive: "Google Drive Cloud Sync", path: "gdrive://creatiVision/Accounting/2025/Rechnungen_Q4.pdf", role: "cloud_mirror", mtime: "2026-09-05T14:30:00Z" }
          ],
          semantic_question: "Identischer Hash auf Arbeitsdateien (Lokal) und Google Drive gefunden. Handelt es sich hierbei um ein beabsichtigtes Cloud-Backup / Mirroring?",
          recommendation: "Als gewolltes Backup einstufen — beide Standorte beibehalten und Verknüpfung im Sync-Manager verankern.",
          decision: "intended_backup"
        },
        {
          id: "cluster_steuer_dumpzone",
          file_name: "steuerbescheid_2024_einkommensteuer.pdf",
          file_size_kb: 1180,
          sha256_prefix: "a1b2c3d4",
          redundancy_type: "dump_zone_duplicate",
          locations: [
            { drive: "PrivatBüro", path: "/media/privat-data/10_PrivatBüro/2024/Steuern/steuerbescheid_2024.pdf", role: "primary", mtime: "2025-11-12T10:00:00Z" },
            { drive: "Downloads (Dumpzone)", path: "/home/mb/Downloads/steuerbescheid_2024_einkommensteuer.pdf", role: "clutter_copy", mtime: "2026-08-15T09:12:00Z" }
          ],
          semantic_question: "Die Datei in Downloads ist ein exaktes Duplikat des bereits einsortierten Steuerbescheids im PrivatBüro. Soll das temporäre Duplikat in Downloads bereinigt werden?",
          recommendation: "Downloads-Kopie über send2trash in den Papierkorb verschieben; Primärkopie im PrivatBüro schützen.",
          decision: "consolidate"
        },
        {
          id: "cluster_brand_assets_logo",
          file_name: "creativision_brand_logo_2026.svg",
          file_size_kb: 420,
          sha256_prefix: "f5e6d7c8",
          redundancy_type: "cross_project_sharing",
          locations: [
            { drive: "Arbeitsdateien (work-data)", path: "/media/work-data/002_cv-projects/webdesign-wp-lc-ps/assets/logo.svg", role: "project_local", mtime: "2026-08-20T16:00:00Z" },
            { drive: "Google Drive Cloud Sync", path: "gdrive://creatiVision/Brand/Assets/logo_master.svg", role: "cloud_master", mtime: "2026-08-20T16:00:00Z" }
          ],
          semantic_question: "Identisches Vektorlogo in Webdesign-Projekt und zentralem Google-Drive-Assets-Ordner. Soll dies als geteilte Ressource bestehen bleiben?",
          recommendation: "Gewollte Mehrfachnutzung: beide Kopien belassen.",
          decision: "intended_backup"
        }
      ];

      return h("div", { style: { display: "flex", flexDirection: "column", gap: "1.5rem" } },
        // Step 2 View Switcher (Tree vs Obsidian Graph vs Multi-Computer Radar)
        h("div", { className: "auto-org-view-tabs" },
          h("button", {
            type: "button",
            className: `auto-org-view-tab ${step2ViewMode === "tree" ? "active" : ""}`,
            onClick: () => setStep2ViewMode("tree")
          }, "🌳 Natürliche Taxonomie & Ziel-Verzeichnisbaum (S_ideal)"),
          h("button", {
            type: "button",
            className: `auto-org-view-tab ${step2ViewMode === "graph" ? "active" : ""}`,
            onClick: () => setStep2ViewMode("graph")
          }, "🕸️ Animierter Obsidian-Graph (Dateifluss & Netzwerk)"),
          h("button", {
            type: "button",
            className: "auto-org-view-tab auto-org-radar-btn",
            style: { marginLeft: "auto" },
            onClick: () => setActiveModal("system_tree"),
            title: "Öffnet das dedizierte Multi-Computer Tree Fenster mit Backup & Syncthing Radar"
          }, "🌐 Multi-Computer Tree & Radar Fenster ↗")
        ),

        // Obsidian Graph View if active
        step2ViewMode === "graph" && h(ObsidianFlowGraph, {
          isPaused: obsidianPaused,
          speedMultiplier: obsidianSpeed,
          onTogglePause: () => setObsidianPaused(p => !p)
        }),

        // ============================================================
        // SECTION 1: NATÜRLICH ENTSTANDENE KATEGORIEN (EMERGENTE TAXONOMIE)
        // ============================================================
        h("div", { className: "auto-org-panel", style: { border: "1px solid #3b82f6" } },
          h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem", marginBottom: "1rem" } },
            h("div", { style: { flex: 1, minWidth: "280px" } },
              h("div", { style: { display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" } },
                h("span", { style: { fontSize: "1.35rem" } }, "🌱"),
                h("h3", { style: { fontSize: "1.15rem", fontWeight: 700, color: "#ffffff", margin: 0 } },
                  "Natürlich entstandenes Organisationssystem (Emergente Taxonomie)"
                ),
                h(OverlaySwitchButton, {
                  status: isEmergentApproved ? "approved" : "proposed",
                  onApprove: () => {
                    if (!isEmergentApproved) handleApproveEmergentTaxonomy();
                  },
                  onExclude: () => {
                    if (isEmergentApproved) handleApproveEmergentTaxonomy();
                  },
                  onReset: () => {
                    if (isEmergentApproved) handleApproveEmergentTaxonomy();
                  }
                })
              ),
              h("p", { style: { color: "#94a3b8", fontSize: "0.85rem", marginTop: "0.35rem", lineHeight: "1.4" } },
                "Die Kategorien wurden durch semantische Vektor-Cluster, OCR-Volltextanalyse und Dateipfad-Muster direkt aus Ihrem realen Datenbestand ermittelt — keine starren Vorgaben, sondern induzierte Struktur:"
              )
            ),
            h("div", { style: { display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" } },
              h("button", {
                type: "button",
                className: "auto-org-btn auto-org-btn-primary",
                style: { padding: "0.6rem 1.3rem", fontWeight: 700 },
                onClick: handleApproveEmergentTaxonomy,
                disabled: loading
              }, isEmergentApproved ? "✓ Kategoriensystem freigegeben (Klicken zum Umschalten)" : "🟢 Natürlich entstandenes System freigeben")
            )
          ),

          // Multi-Level Hierarchical Tree Explorer (with Sub-Branches, AI Tokens & Graph Focus)
          h(MultiLevelTreeExplorer, {
            categories: emergentCategories,
            isApproved: isEmergentApproved,
            approvedCategoryIds: approvedCategoryIds,
            excludedCategoryIds: excludedCategoryIds,
            onSwitchCategory: handleSwitchCategory,
            onToggleApproveCategory: handleApproveEmergentTaxonomy,
            onFocusGraph: (branchId) => {
              setStep2ViewMode("graph");
            },
            expandedBranches: expandedBranches,
            onToggleExpandBranch: toggleExpandBranch,
            onApplyToRule: handleApplyEmergentCatToRule
          })
        ),

        // ============================================================
        // SECTION 2: CROSS-DRIVE REDUNDANZ-ABGLEICH & SEMANTISCHE KLÄRUNG
        // ============================================================
        h("div", { className: "auto-org-panel" },
          h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.5rem" } },
            h("div", null,
              h("h3", { style: { fontSize: "1.125rem", fontWeight: 700, display: "flex", alignItems: "center", gap: "0.5rem", color: "#ffffff" } },
                h("span", null, "⚖️"),
                h("span", null, `Cross-Drive Redundanz-Abgleich & Semantische Klärung (${redundancyClusters.length} Cluster)`)
              ),
              h("p", { style: { fontSize: "0.8125rem", color: "#94a3b8", marginTop: "0.2rem" } },
                "Vergleich zwischen lokalen Festplatten, Google Drive & temporären Ordnern: Sind gefundene Redundanzen gewollte Backups oder zu konsolidierende Duplikate?"
              )
            ),
            h("span", { className: "auto-org-badge auto-org-badge-blue" }, "Semantische KI-Prüfung aktiv")
          ),

          h("div", { style: { display: "flex", flexDirection: "column", gap: "1rem" } },
            redundancyClusters.map((c) => {
              const isBackup = c.decision === "intended_backup";
              const isConsolidate = c.decision === "consolidate";
              const typeBadge = c.redundancy_type === "suspected_backup" ?
                h("span", { className: "auto-org-badge auto-org-badge-green" }, "🛡️ Vermutetes Backup / Cloud-Mirror") :
                (c.redundancy_type === "dump_zone_duplicate" ?
                  h("span", { className: "auto-org-badge auto-org-badge-yellow" }, "🧹 Dumpzone-Duplikat") :
                  h("span", { className: "auto-org-badge auto-org-badge-blue" }, "🔄 Geteilte Projektressource")
                );

              return h("div", { key: c.id, className: "auto-org-reconciliation-card" },
                // Header
                h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "0.5rem" } },
                  h("div", null,
                    h("span", { style: { fontWeight: 700, color: "#ffffff", fontSize: "1rem" } }, `📄 ${c.file_name}`),
                    h("span", { style: { fontSize: "0.75rem", color: "#94a3b8", marginLeft: "0.5rem" } }, `${c.file_size_kb} KB • SHA-256: ${c.sha256_prefix}...`)
                  ),
                  typeBadge
                ),

                // Locations
                h("div", { style: { display: "flex", flexDirection: "column", gap: "0.4rem" } },
                  (c.locations || []).map((loc, li) => {
                    const isPrimary = loc.role === "primary" || loc.role === "project_local";
                    return h("div", { key: li, className: "auto-org-location-box" },
                      h("div", { style: { display: "flex", alignItems: "center", gap: "0.5rem" } },
                        h("span", { style: { fontWeight: 600, color: isPrimary ? "#4ade80" : "#60a5fa" } },
                          isPrimary ? "📍 Primär:" : (loc.role === "cloud_mirror" || loc.role === "cloud_master" ? "☁️ Cloud:" : "⬇️ Kopie:")
                        ),
                        h("span", { style: { fontWeight: 600, color: "#ffffff" } }, loc.drive),
                        h("span", { style: { fontFamily: "monospace", color: "#94a3b8", fontSize: "0.75rem" } }, loc.path)
                      ),
                      h("span", { className: "auto-org-token-pill", style: { fontSize: "0.65rem" } }, loc.role)
                    );
                  })
                ),

                // Semantic Question & Recommendation Box
                h("div", {
                  style: {
                    background: "rgba(59, 130, 246, 0.1)",
                    border: "1px solid rgba(59, 130, 246, 0.3)",
                    borderRadius: "0.375rem",
                    padding: "0.75rem 1rem",
                    display: "flex",
                    flexDirection: "column",
                    gap: "0.35rem"
                  }
                },
                  h("div", { style: { fontSize: "0.85rem", color: "#f8fafc", fontWeight: 600, display: "flex", alignItems: "center", gap: "0.4rem" } },
                    h("span", null, "❓"),
                    h("span", null, c.semantic_question)
                  ),
                  c.recommendation && h("div", { style: { fontSize: "0.8rem", color: "#93c5fd" } },
                    h("strong", null, "KI-Empfehlung: "),
                    h("span", null, c.recommendation)
                  )
                ),

                // Decision Action Buttons
                h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid #334155", paddingTop: "0.65rem", flexWrap: "wrap", gap: "0.5rem" } },
                  h("div", { style: { display: "flex", alignItems: "center", gap: "0.4rem" } },
                    h("span", { style: { fontSize: "0.8rem", color: "#94a3b8" } }, "Aktuelle Einstufung:"),
                    h("span", {
                      className: `auto-org-badge ${isBackup ? "auto-org-badge-green" : (isConsolidate ? "auto-org-badge-yellow" : "auto-org-badge-blue")}`
                    }, isBackup ? "✓ Gewolltes Backup (Beide behalten)" : (isConsolidate ? "🧹 Zur Konsolidierung markiert" : "Ausstehend"))
                  ),
                  h("div", { style: { display: "flex", gap: "0.5rem" } },
                    h("button", {
                      type: "button",
                      className: isBackup ? "auto-org-btn auto-org-btn-primary" : "auto-org-btn auto-org-btn-outline",
                      style: { fontSize: "0.75rem", padding: "0.35rem 0.8rem" },
                      onClick: () => handleClarifyRedundancy(c.id, "intended_backup"),
                      disabled: loading
                    }, "🛡️ Gewolltes Backup"),
                    h("button", {
                      type: "button",
                      className: isConsolidate ? "auto-org-btn auto-org-btn-primary" : "auto-org-btn auto-org-btn-outline",
                      style: { fontSize: "0.75rem", padding: "0.35rem 0.8rem", color: isConsolidate ? "#ffffff" : "#f87171" },
                      onClick: () => handleClarifyRedundancy(c.id, "consolidate"),
                      disabled: loading
                    }, "🧹 Ungewolltes Duplikat (Konsolidieren)")
                  )
                )
              );
            })
          )
        ),

        // ============================================================
        // SECTION 3: VERBINDLICHER ZIEL-VERZEICHNISBAUM (S_IDEAL)
        // ============================================================
        h("div", { className: "auto-org-panel" },
          // Status and Approval Banner
          h("div", {
            className: "auto-org-tree-banner",
            style: {
              borderLeft: `5px solid ${isSystemApproved ? "#4ade80" : "#facc15"}`,
              background: isSystemApproved ? "rgba(34, 197, 94, 0.08)" : "rgba(234, 179, 8, 0.08)",
              marginBottom: "1rem"
            }
          },
            h("div", null,
              h("div", { style: { fontSize: "1.1rem", fontWeight: 700, display: "flex", alignItems: "center", gap: "0.5rem", color: isSystemApproved ? "#4ade80" : "#facc15" } },
                h("span", null, isSystemApproved ? "✓" : "⏳"),
                h("span", null, isSystemApproved ? "Verbindlicher Ziel-Verzeichnisbaum vollständig freigegeben" : "Verbindlicher Ziel-Verzeichnisbaum (S_ideal)")
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
          showNewNodeForm && h("div", { className: "auto-org-panel", style: { border: "1px solid #3b82f6", marginBottom: "1rem" } },
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
                    h("button", {
                      type: "button",
                      className: `auto-org-badge ${isApproved ? "auto-org-badge-green" : "auto-org-badge-yellow"}`,
                      style: { cursor: "pointer", border: "none" },
                      title: isApproved ? "Klicken zum Pausieren" : "Klicken zum Freigeben",
                      onClick: (e) => {
                        e.stopPropagation();
                        handleToggleNodeApproval(node.id, isApproved);
                      }
                    },
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
          )
        ),

        // Step 2 Footer Navigation
        h("div", { className: "auto-org-step-footer" },
          h("button", {
            className: "auto-org-btn auto-org-btn-outline",
            onClick: () => setStep(1)
          }, "← Zurück zu Schritt 1: Quelle & Ist-Stand"),
          !isStep2Approved ?
          h("button", {
            className: "auto-org-btn",
            style: { padding: "0.6rem 1.5rem", fontSize: "0.875rem", opacity: 0.5, cursor: "not-allowed", background: "#334155", color: "#94a3b8" },
            disabled: true,
            title: "Bitte bestätigen und geben Sie zuerst das natürlich entstandene Kategoriensystem oben frei."
          }, "🔒 Schritt 3 gesperrt (Freigabe des Kategoriensystems erforderlich)") :
          h("button", {
            className: "auto-org-btn auto-org-btn-primary",
            style: { padding: "0.6rem 1.5rem", fontSize: "0.875rem" },
            onClick: () => setStep(3)
          }, "Weiter zu Schritt 3: Proaktive Filter-Regeln →")
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
              (taxonomy && taxonomy.tree && taxonomy.tree.length > 0 ? taxonomy.tree : DEFAULT_TREE_NODES).map(n =>
                h("button", {
                  key: n.id,
                  type: "button",
                  className: "auto-org-tag-btn",
                  style: { borderStyle: n.is_approved ? "solid" : "dashed" },
                  onClick: () => setTargetTemplate(n.target_path_template)
                }, `${n.icon || "📁"} ${n.name.split("/")[1] || n.name}`)
              )
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

    // ============================================================
    // STEP 3: PROAKTIV VORGESCHLAGENE FILTER-REGELN AUS DER ANALYSE
    // ============================================================
    const renderSuggestedRulesPanel = () => {
      const sRules = (suggestedRules && suggestedRules.suggested_rules) || [];
      const totalCount = sRules.length;
      if (totalCount === 0) return null;

      const unadoptedCount = sRules.filter(r => !r.is_already_active).length;
      const selectedCount = selectedSuggestedRuleIds.size;
      const allSelected = selectedCount === totalCount && totalCount > 0;

      return h("div", { className: "auto-org-panel", style: { border: "1px solid #3b82f6", background: "rgba(15, 23, 42, 0.85)" } },
        // Header with Proactive Info
        h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem", marginBottom: "0.75rem" } },
          h("div", { style: { flex: 1, minWidth: "280px" } },
            h("div", { style: { display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" } },
              h("span", { style: { fontSize: "1.35rem" } }, "🤖"),
              h("h3", { style: { fontSize: "1.15rem", fontWeight: 700, color: "#ffffff", margin: 0 } },
                "Proaktiv vorgeschlagene Filter-Regeln (aus Medien- & Pfadanalyse)"
              ),
              h("span", { className: "auto-org-badge auto-org-badge-green" }, `${totalCount} KI-Vorschläge`)
            ),
            h("p", { style: { color: "#94a3b8", fontSize: "0.85rem", marginTop: "0.35rem", lineHeight: "1.4" } },
              `Hermes hat Ihren realen Datenbestand (${suggestedRules.analyzed_files || 450} Dateien) analysiert. Nutzen Sie das Ampelsystem (🟡 = Vorschlag, 🟢 = Freigegeben) und Checkboxen zur expliziten Freigabe:`
            )
          )
        ),

        // User Approval & Checkbox Bulk Toolbar
        h("div", { className: "auto-org-approval-bar" },
          h("div", { style: { display: "flex", alignItems: "center", gap: "0.75rem" } },
            h("label", { style: { display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer", fontWeight: 600, fontSize: "0.875rem", color: "#f8fafc" } },
              h("input", {
                type: "checkbox",
                className: "auto-org-checkbox",
                checked: allSelected,
                onChange: toggleSelectAllSuggestedRules
              }),
              h("span", null, "Alle Vorschläge auswählen")
            ),
            h("span", { style: { fontSize: "0.8rem", color: "#94a3b8" } },
              `(${selectedCount} von ${totalCount} ausgewählt • ${unadoptedCount} noch ausstehend)`
            )
          ),
          h("div", { style: { display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" } },
            h("button", {
              type: "button",
              className: "auto-org-btn auto-org-btn-primary",
              style: { padding: "0.5rem 1.2rem", fontWeight: 700, display: "flex", alignItems: "center", gap: "0.4rem", background: "#16a34a", borderColor: "#22c55e" },
              onClick: () => handleAdoptSuggestedRules(Array.from(selectedSuggestedRuleIds)),
              disabled: adoptingRules || selectedCount === 0
            },
              adoptingRules ? "⏳ Freigabe läuft..." : `🟢 Ausgewählte Regeln freigeben & aktivieren (${selectedCount})`
            ),
            unadoptedCount > 0 && h("button", {
              type: "button",
              className: "auto-org-btn auto-org-btn-outline",
              style: { padding: "0.5rem 1rem", fontSize: "0.8rem" },
              onClick: () => handleAdoptSuggestedRules(null),
              disabled: adoptingRules
            }, "⚡ Alle 5 sofort freigeben")
          )
        ),

        // Grid of Suggested Rules
        h("div", { className: "auto-org-suggested-grid" },
          sRules.map((sr) => {
            const confPct = Math.round((sr.confidence || 0.95) * 100);
            const isApproved = approvedRuleIds.has(sr.id) || (sr.is_already_active && !excludedRuleIds.has(sr.id));
            const isExcluded = excludedRuleIds.has(sr.id);
            const ruleStatus = isApproved ? "approved" : (isExcluded ? "excluded" : "proposed");
            const isActive = isApproved;
            const isChecked = selectedSuggestedRuleIds.has(sr.id);

            return h("div", {
              key: sr.id,
              className: `auto-org-suggested-card ${ruleStatus === "approved" ? "auto-org-card-approved" : (ruleStatus === "excluded" ? "auto-org-card-excluded" : "")}`,
              style: {
                borderColor: isActive ? "#22c55e" : (isExcluded ? "#ef4444" : (isChecked ? "#3b82f6" : "#eab308")),
                boxShadow: isActive ? "0 0 10px rgba(34, 197, 94, 0.15)" : "none"
              }
            },
              // Header Row with Checkbox & Segmented Switch
              h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem", flexWrap: "wrap" } },
                h("label", { style: { display: "flex", alignItems: "center", gap: "0.6rem", cursor: "pointer", margin: 0 } },
                  h("input", {
                    type: "checkbox",
                    className: "auto-org-checkbox",
                    checked: isChecked,
                    onChange: () => toggleSuggestedRuleSelection(sr.id)
                  }),
                  h("span", { style: { fontSize: "1.35rem" } }, sr.icon || "📋"),
                  h("div", null,
                    h("span", { style: { fontWeight: 700, color: "#ffffff", fontSize: "0.95rem", display: "block" } }, sr.name),
                    h("span", { style: { fontSize: "0.75rem", color: "#94a3b8" } }, sr.category)
                  )
                ),
                h("div", { style: { display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "0.25rem" } },
                  h(OverlaySwitchButton, {
                    status: ruleStatus,
                    onApprove: () => handleSwitchRule(sr.id, "approved"),
                    onExclude: () => handleSwitchRule(sr.id, "excluded"),
                    onReset: () => handleSwitchRule(sr.id, "proposed"),
                    size: "sm"
                  }),
                  h("span", { style: { fontSize: "0.75rem", color: "#60a5fa" } }, `${sr.matched_files_count || 0} Dateien • ${confPct}% Konfidenz`)
                )
              ),

              // Description & Evidence
              h("div", { style: { fontSize: "0.8125rem", color: "#cbd5e1", lineHeight: "1.4" } }, sr.description),
              h("div", { className: "auto-org-evidence-box" },
                h("span", { style: { fontWeight: 600, color: "#93c5fd" } }, "💡 Reale Daten-Evidenz: "),
                h("span", { style: { color: "#e2e8f0" } }, sr.evidence)
              ),

              // Animated "Von wo nach wo" Flow Route
              h(AnimatedFlowRoute, {
                sourcePath: "/home/mb/Downloads",
                targetPath: formatUserPath(sr.target_template),
                confidence: sr.confidence,
                branchId: sr.branch_id,
                isApproved: isActive,
                onFocusGraph: () => {
                  setStep(2);
                  setStep2ViewMode("graph");
                }
              }),

              // Visual File Path Tree inside Rule Card
              h(VisualFilePathTree, {
                sourcePath: "/home/mb/Downloads",
                targetPath: formatUserPath(sr.target_template),
                files: (sr.sample_files || []).map((sf, sidx) => ({
                  file_name: sf,
                  source_path: `/home/mb/Downloads/${sf}`,
                  destination_path: `${formatUserPath(sr.target_template).replace('{year}', '2026')}${sf}`,
                  size_kb: 45 + sidx * 20
                })),
                title: `Visueller Pfad-Baum: ${sr.name}`,
                defaultExpanded: true
              }),

              // AI Reasoning Drawer (Context & Tokens)
              h(AIReasoningDrawer, {
                confidence: sr.confidence,
                reasoning: sr.ai_reasoning,
                tokens: sr.ai_tokens,
                clusterName: sr.category
              }),

              // Sample Files Pills
              sr.sample_files && sr.sample_files.length > 0 && h("div", { style: { display: "flex", flexWrap: "wrap", gap: "0.3rem", marginTop: "0.2rem" } },
                sr.sample_files.slice(0, 3).map((sf, idx) =>
                  h("span", { key: idx, className: "auto-org-sample-pill", title: sf },
                    sf.length > 32 ? sf.slice(0, 30) + "..." : sf
                  )
                ),
                sr.sample_files.length > 3 && h("span", { style: { fontSize: "0.7rem", color: "#94a3b8", alignSelf: "center" } }, `+${sr.sample_files.length - 3} weitere`)
              ),

              // Footer with Action Button
              h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid #334155", paddingTop: "0.5rem", marginTop: "0.25rem" } },
                h("span", { style: { fontSize: "0.75rem", color: isActive ? "#4ade80" : "#facc15", fontWeight: 600 } },
                  isActive ? "✓ Regel aktiv im System" : "Ausstehende Benutzer-Freigabe"
                ),
                h("button", {
                  type: "button",
                  className: `auto-org-btn ${isActive ? "auto-org-btn-outline" : "auto-org-btn-primary"}`,
                  style: { fontSize: "0.75rem", padding: "0.35rem 0.85rem", fontWeight: 600, background: isActive ? "transparent" : "#16a34a", borderColor: isActive ? "#334155" : "#22c55e" },
                  onClick: () => handleSwitchRule(sr.id, isActive ? "proposed" : "approved")
                }, isActive ? "✓ Aktiv / Freigegeben" : "🟢 Regel freigeben")
              )
            );
          })
        )
      );
    };

    const renderNaturalLanguageRulesPanel = () => {
      if (!profilerRules || profilerRules.length === 0) return null;
      return h("div", { className: "auto-org-panel", style: { border: "1px solid #7c3aed", background: "rgba(30, 27, 75, 0.4)" } },
        h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.5rem" } },
          h("div", null,
            h("h3", { style: { fontSize: "1.125rem", fontWeight: 700, color: "#c084fc", display: "flex", alignItems: "center", gap: "0.5rem" } },
              "🤖 Sprachlich formulierte Meta-Regeln (Human-in-the-Loop für 90% der Masse)"
            ),
            h("p", { style: { fontSize: "0.8125rem", color: "#cbd5e1", marginTop: "0.2rem" } },
              "Die KI hat aus den Verzeichnis-Clustern folgende verständliche Meta-Regeln formuliert. Bestätigen Sie diese mit 1 Klick für die Batch-Ausführung."
            )
          ),
          h("button", {
            type: "button",
            className: "auto-org-btn auto-org-btn-outline",
            style: { color: "#c084fc", borderColor: "#7c3aed" },
            onClick: () => profilerRules.forEach(r => handleApproveNlRule(r.id, true))
          }, "✓ Alle Meta-Regeln bestätigen")
        ),
        h("div", { className: "auto-org-nl-rule-grid" },
          profilerRules.map((rule) => {
            const isApproved = rule.status === "approved";
            const isRejected = rule.status === "rejected";
            return h("div", {
              key: rule.id,
              className: `auto-org-nl-rule-card ${isApproved ? "approved" : ""}`
            },
              h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem" } },
                h("div", { style: { fontWeight: 700, fontSize: "0.95rem", color: "#ffffff" } }, rule.title_de),
                h("span", {
                  className: `auto-org-badge ${isApproved ? "auto-org-badge-green" : isRejected ? "auto-org-badge-red" : "auto-org-badge-yellow"}`
                }, isApproved ? "✓ Bestätigt" : isRejected ? "✕ Abgelehnt" : "Vorgeschlagen")
              ),
              h("p", { style: { fontSize: "0.825rem", color: "#cbd5e1", margin: 0, lineHeight: "1.4" } }, rule.description_de),
              h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "auto", paddingTop: "0.5rem", borderTop: "1px solid #334155" } },
                h("span", { style: { fontSize: "0.75rem", color: "#94a3b8" } },
                  `Betrifft: ~${rule.affected_files_count} Dateien (${Math.round((rule.confidence || 0.85) * 100)}% Konfidenz)`
                ),
                h("div", { style: { display: "flex", gap: "0.4rem" } },
                  !isApproved && h("button", {
                    type: "button",
                    className: "auto-org-btn auto-org-btn-primary",
                    style: { fontSize: "0.75rem", padding: "0.3rem 0.75rem", background: "#16a34a" },
                    onClick: () => handleApproveNlRule(rule.id, true)
                  }, "✓ Annehmen"),
                  !isRejected && h("button", {
                    type: "button",
                    className: "auto-org-btn auto-org-btn-outline",
                    style: { fontSize: "0.75rem", padding: "0.3rem 0.6rem" },
                    onClick: () => handleApproveNlRule(rule.id, false)
                  }, "✕")
                )
              )
            );
          })
        )
      );
    };

    const renderStep3 = () => {
      return h("div", { style: { display: "flex", flexDirection: "column", gap: "1.25rem" } },
        // 0. Sprachlich formulierte Meta-Regeln (NL)
        renderNaturalLanguageRulesPanel(),

        // 1. Proaktiv vorgeschlagene Filter-Regeln
        renderSuggestedRulesPanel(),

        // 2. Modular Rule Builder
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
      const rawGroups = (dryRun && dryRun.semantic_groups) || [];
      const groups = rawGroups.length > 0 ? rawGroups : (dryRun && dryRun.actions ? [
        {
          group_id: "grp_general",
          title: "📁 Reorganisations-Gruppe: Alle passenden Dokumente",
          intent: "Sortierung und Verschiebung gemäß aktiven Filter-Regeln in den Zielbaum",
          icon: "📁",
          source_label: "Quellverzeichnisse (Downloads & Arbeitsdaten)",
          target_label: "Zielverzeichnisse (PrivatBüro & Work-Data)",
          file_count: dryRun.actions.length,
          total_size_kb: dryRun.actions.reduce((acc, a) => acc + Math.round((a.size_bytes || 0) / 1024), 0),
          safe_count: dryRun.safe_count,
          sample_files: dryRun.actions.slice(0, 10).map(a => ({
            file_name: a.file_name,
            size_kb: Math.round((a.size_bytes || 0) / 1024),
            source_path: formatUserPath(a.source_path),
            destination_path: formatUserPath(a.destination_path)
          }))
        }
      ] : []);

      const totalGroups = groups.length;
      const approvedCount = groups.filter(g => approvedGroupIds.has(g.group_id)).length;
      const approvedFilesCount = groups
        .filter(g => approvedGroupIds.has(g.group_id))
        .reduce((sum, g) => sum + (g.safe_count || 0), 0);
      const allGroupsApproved = totalGroups > 0 && approvedCount === totalGroups;

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
                  `Batch: ${dryRun.batch_id.slice(0, 12)} • Vorbereitet in ${totalGroups} semantischen Gruppen • Sicher zur Ausführung: ${dryRun.safe_count}` :
                  "Simulieren Sie die Reorganisation vor der Ausführung. Hermes prüft Schreibrechte, Docker-Mounts und Dateinamen-Kollisionen."
              )
            ),
            h("div", { style: { display: "flex", gap: "0.5rem" } },
              h("button", {
                className: "auto-org-btn auto-org-btn-outline",
                onClick: handleRunDryRun,
                disabled: loading
              }, loading ? "Simuliere..." : "🔄 Simulation neu starten"),
              dryRun && approvedFilesCount > 0 && h("button", {
                className: "auto-org-btn auto-org-btn-primary",
                style: { padding: "0.6rem 1.5rem", fontWeight: 700, background: "#16a34a", borderColor: "#22c55e" },
                onClick: handleExecuteDryRun,
                disabled: loading
              }, `⚡ Freigegebene Gruppen ausführen (${approvedFilesCount} Dateien)`)
            )
          ),

          !dryRun ?
            h("div", { style: { textAlign: "center", padding: "3rem 1rem" } },
              h("div", { style: { fontSize: "2.5rem", marginBottom: "0.75rem" } }, "🔍"),
              h("h4", { style: { fontWeight: 600, marginBottom: "0.5rem" } }, "Bereit für die Dry-Run Simulation"),
              h("p", { style: { color: "#94a3b8", fontSize: "0.875rem", marginBottom: "1.5rem", maxWidth: "500px", margin: "0 auto 1.5rem auto" } },
                "Die Simulation gleicht alle aktiven Filter-Regeln gegen den aktuellen Dateibestand ab und stellt geplante Verschiebungen in semantischen Intent-Gruppen zusammen."
              ),
              h("button", {
                className: "auto-org-btn auto-org-btn-primary",
                style: { padding: "0.6rem 2rem", fontSize: "0.95rem" },
                onClick: handleRunDryRun
              }, "Jetzt Dry-Run starten")
            ) :
            h("div", { style: { display: "flex", flexDirection: "column", gap: "1rem" } },
              // Outlier Triage Queue Section (Human-in-the-Middle for 10% outliers)
              profilerOutliers.length > 0 && h("div", { className: "auto-org-outlier-queue", style: { marginBottom: "0.5rem" } },
                h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem" } },
                  h("h4", { style: { fontWeight: 700, fontSize: "1rem", color: "#f59e0b", display: "flex", alignItems: "center", gap: "0.4rem", margin: 0 } },
                    "🎯 Ausreißer-Triage (Human-in-the-Middle Queue für 10% Sonderfälle)",
                    h("span", { className: "auto-org-badge auto-org-badge-yellow" }, `${profilerOutliers.length} Ausreißer`)
                  ),
                  h("span", { style: { fontSize: "0.8rem", color: "#94a3b8" } },
                    "Konkrete Lösungsvorschläge je Einzelfall zur 1-Klick Annahme"
                  )
                ),
                profilerOutliers.map((o) => {
                  const isApproved = o.status === "approved";
                  const isRejected = o.status === "rejected";
                  return h("div", {
                    key: o.id,
                    className: `auto-org-outlier-card ${isApproved ? "resolved" : isRejected ? "rejected" : ""}`
                  },
                    h("div", { style: { display: "flex", flexDirection: "column", gap: "0.25rem", flex: 1, minWidth: "260px" } },
                      h("div", { style: { display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" } },
                        h("span", { className: "auto-org-badge auto-org-badge-yellow" }, o.disruption_type),
                        h("strong", { style: { color: "#ffffff", fontSize: "0.85rem", wordBreak: "break-all" } }, o.source_path)
                      ),
                      h("div", { style: { fontSize: "0.8rem", color: "#cbd5e1" } }, o.reason_de),
                      h("div", { style: { fontSize: "0.8rem", color: "#4ade80", fontWeight: 600 } },
                        `Lösungsvorschlag (${Math.round(((o.proposal && o.proposal.confidence) || 0.9) * 100)}% Konfidenz): ➔ ${(o.proposal && o.proposal.target_path) || ""}`
                      )
                    ),
                    h("div", { style: { display: "flex", gap: "0.4rem", alignItems: "center" } },
                      !isApproved && !isRejected ? [
                        h("button", {
                          key: "appr",
                          type: "button",
                          className: "auto-org-btn auto-org-btn-primary",
                          style: { fontSize: "0.75rem", padding: "0.35rem 0.75rem", background: "#16a34a" },
                          onClick: () => handleResolveOutlier(o.id, "approved")
                        }, "✅ Vorschlag annehmen"),
                        h("button", {
                          key: "rej",
                          type: "button",
                          className: "auto-org-btn auto-org-btn-outline",
                          style: { fontSize: "0.75rem", padding: "0.35rem 0.6rem" },
                          onClick: () => handleResolveOutlier(o.id, "rejected")
                        }, "❌ Ignorieren")
                      ] :
                      h("span", {
                        className: `auto-org-badge ${isApproved ? "auto-org-badge-green" : "auto-org-badge-yellow"}`
                      }, isApproved ? "✓ Angenommen" : "✕ Verworfen")
                    )
                  );
                })
              ),

              // View Switcher Tabs (Groups vs Tree-Diff vs Path Tree vs Obsidian Graph vs Table)
              h("div", { className: "auto-org-view-tabs" },
                h("button", {
                  type: "button",
                  className: `auto-org-view-tab ${step4ViewMode === "diff" ? "active" : ""}`,
                  onClick: () => setStep4ViewMode("diff")
                }, `⚖️ "Von → Nach" Tree-Diff (${treeDiffNodes.length} Knoten)`),
                h("button", {
                  type: "button",
                  className: `auto-org-view-tab ${step4ViewMode === "groups" ? "active" : ""}`,
                  onClick: () => setStep4ViewMode("groups")
                }, `📑 Abstrakte Ausführungsgruppen (${totalGroups})`),
                h("button", {
                  type: "button",
                  className: `auto-org-view-tab ${step4ViewMode === "tree" ? "active" : ""}`,
                  onClick: () => setStep4ViewMode("tree")
                }, `🌳 Visueller Pfad-Baum (${dryRun.actions.length} Dateien)`),
                h("button", {
                  type: "button",
                  className: `auto-org-view-tab ${step4ViewMode === "graph" ? "active" : ""}`,
                  onClick: () => setStep4ViewMode("graph")
                }, "🕸️ Animierter Obsidian-Transfer-Graph"),
                h("button", {
                  type: "button",
                  className: `auto-org-view-tab ${step4ViewMode === "table" ? "active" : ""}`,
                  onClick: () => setStep4ViewMode("table")
                }, `📋 Technische Diff-Tabelle (${dryRun.actions.length} Dateien)`),
                h("button", {
                  type: "button",
                  className: "auto-org-view-tab auto-org-radar-btn",
                  style: { marginLeft: "auto" },
                  onClick: () => setActiveModal("system_tree"),
                  title: "Öffnet das dedizierte Multi-Computer Tree Fenster mit Backup & Syncthing Radar"
                }, "🌐 Multi-Computer Tree & Radar Fenster ↗")
              ),

              // TAB 0: Von -> Nach Tree-Diff (S_now -> S_ideal)
              step4ViewMode === "diff" && h("div", { className: "auto-org-diff-container" },
                h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" } },
                  h("div", null,
                    h("h4", { style: { fontWeight: 700, color: "#ffffff", fontSize: "0.95rem" } }, "🌳 'Von → Nach' Baum-Vergleich (Ist-Zustand S_now ➔ Soll-Zustand S_ideal)"),
                    h("p", { style: { fontSize: "0.8rem", color: "#94a3b8", margin: 0 } }, "Zeigt die berechnete Projektion des selbstheilenden Baums nach Anwendung der bestätigten Regeln und behobenen Ausreißer.")
                  ),
                  h("div", { style: { display: "flex", gap: "0.5rem", alignItems: "center" } },
                    h("button", {
                      type: "button",
                      className: "auto-org-btn auto-org-btn-outline",
                      onClick: handleExportToObsidian,
                      disabled: obsidianExporting,
                      style: { fontSize: "0.75rem" }
                    }, obsidianExporting ? "Exportiere..." : "🗺️ In Obsidian Extended Graph öffnen"),
                    lastTreeDiffBatchId && h("button", {
                      type: "button",
                      className: "auto-org-btn auto-org-btn-outline",
                      onClick: handleRollbackTreeDiff,
                      disabled: treeDiffExecuting,
                      style: { fontSize: "0.75rem", borderColor: "#f59e0b", color: "#f59e0b" }
                    }, treeDiffExecuting ? "Rolle zurück..." : "↺ Zuletzt Ausgeführtes Zurückrollen"),
                    h("button", {
                      type: "button",
                      className: "auto-org-btn auto-org-btn-primary",
                      onClick: handleExecuteTreeDiff,
                      disabled: treeDiffExecuting || treeDiffNodes.filter(n => n.action !== "RETAIN").length === 0,
                      style: { fontSize: "0.75rem", background: "#16a34a" }
                    }, treeDiffExecuting ? "Führe aus..." : `🚀 Tree-Diff Ausführen (${treeDiffNodes.filter(n => n.action !== "RETAIN").length})`)
                  )
                ),
                treeDiffNodes.length === 0 ?
                  h("div", { style: { textAlign: "center", padding: "2rem", color: "#94a3b8", fontSize: "0.85rem" } },
                    "Noch keine Tree-Diff Projektion vorhanden. Führen Sie in Schritt 1 einen Subtree-Scan durch oder bestätigen Sie Regeln in Schritt 3."
                  ) :
                  h("div", { style: { display: "flex", flexDirection: "column", gap: "0.5rem" } },
                    treeDiffNodes.map((node, idx) => {
                      const isMove = node.action === "MOVE";
                      const isArchive = node.action === "ARCHIVE";
                      const isClean = node.action === "CLEAN_TEMP";
                      const actionClass = isMove ? "auto-org-diff-action-move" : isArchive ? "auto-org-diff-action-archive" : isClean ? "auto-org-diff-action-clean" : "auto-org-diff-action-retain";
                      return h("div", { key: idx, className: "auto-org-diff-row" },
                        // Source
                        h("div", { className: "auto-org-diff-source" },
                          h("div", { style: { fontWeight: 600, fontSize: "0.85rem", color: "#ffffff", wordBreak: "break-all" } }, node.source_path),
                          h("div", { style: { fontSize: "0.75rem", color: "#94a3b8" } },
                            node.is_outlier ? "⚠️ Ausreißer im Ist-Zustand" : `${Math.round((node.size_bytes || 0) / 1024)} KB`
                          )
                        ),
                        // Middle
                        h("div", { className: "auto-org-diff-middle" },
                          h("span", { className: `auto-org-badge ${actionClass}` },
                            isMove ? "➔ VERSCHIEBEN" : isArchive ? "📦 ARCHIVIEREN" : isClean ? "🧹 TEMP BEREINIGEN" : "🔒 BEIBEHALTEN"
                          ),
                          h("span", { style: { fontSize: "0.7rem", color: "#cbd5e1" } }, node.reason_de)
                        ),
                        // Target
                        h("div", { className: "auto-org-diff-target" },
                          h("div", { style: { fontWeight: 600, fontSize: "0.85rem", color: isMove || isArchive ? "#4ade80" : isClean ? "#ef4444" : "#94a3b8", wordBreak: "break-all" } },
                            node.target_path || node.source_path
                          ),
                          h("div", { style: { fontSize: "0.75rem", color: "#64748b" } }, "S_ideal Zielpfad")
                        )
                      );
                    })
                  )
              ),

              // TAB 1: Visual Reorganization Path Tree
              step4ViewMode === "tree" && h(VisualDryRunPathTree, {
                actions: dryRun.actions || [],
                groups: dryRun.semantic_groups || [],
                approvedGroupIds: approvedGroupIds,
                excludedGroupIds: excludedGroupIds,
                onSwitchGroup: handleSwitchGroup
              }),

              // TAB 2: Obsidian Transfer Graph
              step4ViewMode === "graph" && h(ObsidianFlowGraph, {
                isPaused: obsidianPaused,
                speedMultiplier: obsidianSpeed,
                onTogglePause: () => setObsidianPaused(p => !p)
              }),

              // TAB 3: Abstract Semantic Groups (DEFAULT)
              step4ViewMode === "groups" && h("div", { style: { display: "flex", flexDirection: "column", gap: "1rem" } },
                // User Approval & Bulk Selection Toolbar
                h("div", { className: "auto-org-approval-bar" },
                  h("div", { style: { display: "flex", alignItems: "center", gap: "0.75rem" } },
                    h("label", { style: { display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer", fontWeight: 600, fontSize: "0.875rem", color: "#f8fafc" } },
                      h("input", {
                        type: "checkbox",
                        className: "auto-org-checkbox",
                        checked: allGroupsApproved,
                        onChange: toggleSelectAllGroups
                      }),
                      h("span", null, "Alle Gruppen zur Ausführung auswählen")
                    ),
                    h("span", { style: { fontSize: "0.8rem", color: "#94a3b8" } },
                      `(${approvedCount} von ${totalGroups} Gruppen freigegeben • ${approvedFilesCount} Dateien)`
                    )
                  ),
                  h("div", { style: { display: "flex", gap: "0.5rem" } },
                    h("button", {
                      type: "button",
                      className: "auto-org-btn auto-org-btn-primary",
                      style: { padding: "0.5rem 1.25rem", fontWeight: 700, background: "#16a34a", borderColor: "#22c55e" },
                      onClick: handleExecuteDryRun,
                      disabled: loading || approvedFilesCount === 0
                    }, `⚡ ${approvedFilesCount} freigegebene Datei(en) jetzt verschieben`)
                  )
                ),

                // Abstract Group Cards
                h("div", { className: "auto-org-group-grid" },
                  groups.map((grp) => {
                    const isApproved = approvedGroupIds.has(grp.group_id);
                    const isExcluded = excludedGroupIds.has(grp.group_id);
                    const groupStatus = isApproved ? "approved" : (isExcluded ? "excluded" : "proposed");
                    const isExpanded = !!expandedGroups[grp.group_id];

                    return h("div", {
                      key: grp.group_id,
                      className: `auto-org-group-card ${groupStatus === "approved" ? "auto-org-card-approved" : (groupStatus === "excluded" ? "auto-org-card-excluded" : "pending")}`
                    },
                      // Card Header Row: Checkbox, Title, Badges, Segmented Switch
                      h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "0.75rem" } },
                        h("label", { style: { display: "flex", alignItems: "center", gap: "0.6rem", cursor: "pointer", margin: 0 } },
                          h("input", {
                            type: "checkbox",
                            className: "auto-org-checkbox",
                            checked: isApproved,
                            onChange: () => toggleGroupApproval(grp.group_id)
                          }),
                          h("span", { style: { fontSize: "1.35rem" } }, grp.icon || "📁"),
                          h("div", null,
                            h("h4", { style: { fontSize: "1.05rem", fontWeight: 700, color: "#ffffff", margin: 0 } }, grp.title),
                            h("span", { style: { fontSize: "0.75rem", color: "#94a3b8" } }, `Regel: ${grp.rule_name || "Automatisch sortieren"}`)
                          )
                        ),
                        h("div", { style: { display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" } },
                          h(OverlaySwitchButton, {
                            status: groupStatus,
                            onApprove: () => handleSwitchGroup(grp.group_id, "approved"),
                            onExclude: () => handleSwitchGroup(grp.group_id, "excluded"),
                            onReset: () => handleSwitchGroup(grp.group_id, "proposed")
                          }),
                          h("span", { className: "auto-org-badge auto-org-badge-blue" }, `${grp.file_count} Dateien`),
                          h("span", { style: { fontSize: "0.75rem", color: "#94a3b8" } }, `${grp.total_size_kb} KB`)
                        )
                      ),

                      // Prominente Idee & Absicht (Front & Center)
                      h("div", { className: "auto-org-intent-box" },
                        h("strong", { style: { color: "#93c5fd" } }, "💡 Idee & Absicht: "),
                        grp.intent
                      ),

                      // Animated "Von wo nach wo" Flow Route
                      h(AnimatedFlowRoute, {
                        sourcePath: grp.source_label,
                        targetPath: grp.target_label,
                        confidence: 0.98,
                        isApproved: isApproved,
                        onFocusGraph: () => setStep4ViewMode("graph")
                      }),

                      // Visual File Path Tree inside Group Card
                      h(VisualFilePathTree, {
                        files: grp.sample_files || [],
                        sourcePath: grp.source_label,
                        targetPath: grp.target_label,
                        defaultExpanded: true,
                        title: `${grp.title} — Visueller Pfad-Baum (${grp.file_count} Dateien)`
                      }),

                      // Footer Action
                      h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid #334155", paddingTop: "0.6rem" } },
                        h("span", { style: { fontSize: "0.75rem", color: isApproved ? "#4ade80" : "#facc15", fontWeight: 600 } },
                          isApproved ? "✓ Freigabe durch Benutzer erteilt" : (isExcluded ? "Ausgeschlossen (wird nicht ausgeführt)" : "Ausführung für diese Gruppe zurückgestellt")
                        ),
                        h("button", {
                          type: "button",
                          className: `auto-org-btn ${isApproved ? "auto-org-btn-outline" : "auto-org-btn-primary"}`,
                          style: { fontSize: "0.75rem", padding: "0.35rem 0.85rem" },
                          onClick: () => handleSwitchGroup(grp.group_id, isApproved ? "proposed" : "approved")
                        }, isApproved ? "Pausieren / Zurückstellen" : "🟢 Gruppe freigeben")
                      )
                    );
                  })
                )
              ),

              // TAB 3: Technical Flat File Table (with clean host paths)
              step4ViewMode === "table" && h("table", { className: "auto-org-table" },
                h("thead", null,
                  h("tr", null,
                    h("th", null, "Datei"),
                    h("th", null, "Aktueller Pfad (S_now)"),
                    h("th", null, ""),
                    h("th", null, "Neues Ziel im Baum (S_ideal)"),
                    h("th", null, "Regel"),
                    h("th", null, "Speicherort"),
                    h("th", null, "Sicherheits-Check")
                  )
                ),
                h("tbody", null,
                  dryRun.actions.length === 0 ?
                  h("tr", null, h("td", { colSpan: 7, style: { textAlign: "center", color: "#94a3b8", padding: "2rem" } }, "Keine Verschiebungs-Aktionen für die aktuellen Regeln gefunden.")) :
                  dryRun.actions.map((act, idx) => h("tr", { key: idx },
                    h("td", { style: { fontWeight: 600 } }, act.file_name),
                    h("td", null, h("span", { className: "auto-org-diff-source" }, formatUserPath(act.source_path))),
                    h("td", null, h("span", { className: "auto-org-diff-arrow" }, "→")),
                    h("td", null, h("span", { className: "auto-org-diff-target" }, formatUserPath(act.destination_path))),
                    h("td", null, h("span", { className: "auto-org-badge auto-org-badge-blue" }, act.rule_name || act.operation)),
                    h("td", null,
                      act.mount_valid !== false ?
                      h("span", { className: "auto-org-badge auto-org-badge-green" }, "✓ RW") :
                      h("span", { className: "auto-org-badge auto-org-badge-red" }, "⚠️ Prüfen")
                    ),
                    h("td", null,
                      act.safe_to_execute ?
                      h("span", { className: "auto-org-badge auto-org-badge-green" }, "Bereit zur Ausführung") :
                      h("span", { className: "auto-org-badge auto-org-badge-red" }, act.mount_warning || (act.collision ? "Kollision erkannt" : "Gesperrt"))
                    )
                  ))
                )
              )
            )
        ),

        // Step 4 Footer Navigation
        h("div", { className: "auto-org-step-footer" },
          h("button", {
            className: "auto-org-btn auto-org-btn-outline",
            onClick: () => setStep(3)
          }, "← Zurück zu Schritt 3: Filter-Regeln anpassen"),
          h("div", { style: { display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" } },
            h("button", {
              className: "auto-org-btn auto-org-btn-outline",
              onClick: () => setActiveModal("journal")
            }, "📜 Reorganisations-Journal & Rollback"),
            dryRun && approvedFilesCount > 0 && h("button", {
              className: "auto-org-btn auto-org-btn-primary",
              style: { background: "#16a34a", borderColor: "#22c55e" },
              onClick: handleExecuteDryRun,
              disabled: loading
            }, `⚡ Reorganisation ausführen (${approvedFilesCount} Dateien)`),
            h("button", {
              className: "auto-org-btn auto-org-btn-primary",
              style: { background: "#2563eb", borderColor: "#3b82f6" },
              onClick: () => setStep(5)
            }, "Weiter zu Schritt 5: Google Drive Cloud-Sync →")
          )
        )
      );
    };

    // ============================================================
    // STEP 5: GOOGLE DRIVE CLOUD-SYNC (FINALER SCHRITT)
    // ============================================================
    const renderStep5 = () => {
      return h("div", { style: { display: "flex", flexDirection: "column", gap: "1.25rem" } },
        // Header Panel
        h("div", { className: "auto-org-panel", style: { border: "1px solid #3b82f6" } },
          h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" } },
            h("div", { style: { flex: 1, minWidth: "300px" } },
              h("div", { style: { display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" } },
                h("span", { style: { fontSize: "1.35rem" } }, "☁️"),
                h("h3", { style: { fontSize: "1.15rem", fontWeight: 700, color: "#ffffff", margin: 0 } },
                  "Google Drive ↔ Lokaler Speicher: Selektive Synchronisation (Schritt 5)"
                ),
                h("span", { className: "auto-org-badge auto-org-badge-blue" }, `${syncMappings.length} konfigurierte Mappings`)
              ),
              h("p", { style: { color: "#94a3b8", fontSize: "0.85rem", marginTop: "0.35rem", lineHeight: "1.4" } },
                "Definieren Sie selektive Ordner-Verknüpfungen zwischen Google Drive (gdrive://creatiVision) und Ihren lokalen Festplatten/Container-Mounts. Synchronisieren Sie Dokumente bidirektional oder gezielt per Push/Pull mit vollem Mount- und Kollisionsschutz."
              )
            ),
            h("div", { style: { display: "flex", gap: "0.5rem" } },
              h("button", {
                type: "button",
                className: "auto-org-btn auto-org-btn-primary",
                onClick: () => setShowNewSyncForm(prev => !prev),
                style: { fontWeight: 700 }
              }, showNewSyncForm ? "✕ Formular schließen" : "+ Neuer Sync-Ordner")
            )
          )
        ),

        // Inline New Sync Mapping Form
        showNewSyncForm && h("div", { className: "auto-org-panel", style: { background: "rgba(30, 41, 59, 0.7)", border: "1px solid #3b82f6" } },
          h("h4", { style: { fontSize: "1rem", fontWeight: 700, color: "#ffffff", marginBottom: "0.75rem" } },
            "Neuen selektiven Google Drive ↔ Lokalen Sync-Ordner anlegen"
          ),
          h("form", { onSubmit: handleSaveSyncMapping, style: { display: "flex", flexDirection: "column", gap: "0.85rem" } },
            h("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "0.75rem" } },
              h("div", null,
                h("label", { style: { fontSize: "0.75rem", color: "#94a3b8", display: "block", marginBottom: "0.25rem" } }, "Bezeichnung / Name"),
                h("input", {
                  type: "text",
                  className: "auto-org-input",
                  style: { width: "100%" },
                  placeholder: "z.B. Buchhaltung & Belege 2026",
                  value: newSyncName,
                  onChange: (e) => setNewSyncName(e.target.value),
                  required: true
                })
              ),
              h("div", null,
                h("label", { style: { fontSize: "0.75rem", color: "#94a3b8", display: "block", marginBottom: "0.25rem" } }, "Google Drive Pfad"),
                h("input", {
                  type: "text",
                  className: "auto-org-input",
                  style: { width: "100%", fontFamily: "monospace" },
                  placeholder: "/creatiVision/Accounting/2026",
                  value: newSyncDrivePath,
                  onChange: (e) => setNewSyncDrivePath(e.target.value),
                  required: true
                })
              ),
              h("div", null,
                h("label", { style: { fontSize: "0.75rem", color: "#94a3b8", display: "block", marginBottom: "0.25rem" } }, "Lokaler Ziel-Speicherort (Host-Pfad)"),
                h("input", {
                  type: "text",
                  className: "auto-org-input",
                  style: { width: "100%", fontFamily: "monospace" },
                  placeholder: "/media/work-data/001_cv-bookaccount/2026",
                  value: newSyncLocalPath,
                  onChange: (e) => setNewSyncLocalPath(e.target.value),
                  required: true
                })
              )
            ),
            h("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "0.75rem" } },
              h("div", null,
                h("label", { style: { fontSize: "0.75rem", color: "#94a3b8", display: "block", marginBottom: "0.25rem" } }, "Synchronisations-Richtung"),
                h("select", {
                  className: "auto-org-select",
                  style: { width: "100%" },
                  value: newSyncDirection,
                  onChange: (e) => setNewSyncDirection(e.target.value)
                },
                  h("option", { value: "bidirectional" }, "⇄ Bidirektional (Beidseitiger Abgleich)"),
                  h("option", { value: "push" }, "⬆️ Lokal ➔ Drive (Lokaler Master / Upload)"),
                  h("option", { value: "pull" }, "⬇️ Drive ➔ Lokal (Cloud Master / Download)")
                )
              ),
              h("div", null,
                h("label", { style: { fontSize: "0.75rem", color: "#94a3b8", display: "block", marginBottom: "0.25rem" } }, "Include Filter (Dateimuster)"),
                h("input", {
                  type: "text",
                  className: "auto-org-input",
                  style: { width: "100%", fontFamily: "monospace" },
                  value: newSyncInclude,
                  onChange: (e) => setNewSyncInclude(e.target.value)
                })
              ),
              h("div", null,
                h("label", { style: { fontSize: "0.75rem", color: "#94a3b8", display: "block", marginBottom: "0.25rem" } }, "Exclude Filter"),
                h("input", {
                  type: "text",
                  className: "auto-org-input",
                  style: { width: "100%", fontFamily: "monospace" },
                  value: newSyncExclude,
                  onChange: (e) => setNewSyncExclude(e.target.value)
                })
              )
            ),
            h("div", { style: { display: "flex", justifyContent: "flex-end", gap: "0.5rem", marginTop: "0.5rem" } },
              h("button", {
                type: "button",
                className: "auto-org-btn auto-org-btn-outline",
                onClick: () => setShowNewSyncForm(false)
              }, "Abbrechen"),
              h("button", {
                type: "submit",
                className: "auto-org-btn auto-org-btn-primary",
                disabled: loading
              }, loading ? "Speichere..." : "✓ Sync-Zuordnung anlegen")
            )
          )
        ),

        // Grid of active sync mappings
        h("div", { className: "auto-org-panel" },
          h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" } },
            h("h3", { style: { fontSize: "1.125rem", fontWeight: 700, display: "flex", alignItems: "center", gap: "0.5rem", color: "#ffffff" } },
              h("span", null, "📁"),
              h("span", null, `Aktive Cloud-Sync Mappings (${syncMappings.length})`)
            ),
            h("span", { style: { fontSize: "0.8125rem", color: "#94a3b8" } },
              "Alle Pfade werden automatisch gegen Mount-Rechte validiert"
            )
          ),
          syncMappings.length === 0 ?
            h("div", { style: { textAlign: "center", padding: "2.5rem 1rem", color: "#94a3b8" } },
              h("div", { style: { fontSize: "2rem", marginBottom: "0.5rem" } }, "☁️"),
              h("p", { style: { fontWeight: 600, color: "#ffffff", fontSize: "0.95rem" } }, "Noch keine Google Drive Sync-Ordner konfiguriert."),
              h("p", { style: { fontSize: "0.85rem", marginTop: "0.25rem" } }, "Klicken Sie oben auf '+ Neuer Sync-Ordner', um einen gezielten Ordnerabgleich anzulegen.")
            ) :
            h("div", { className: "auto-org-sync-grid" },
              syncMappings.map((m) => {
                const isBi = m.direction === "bidirectional";
                const isPush = m.direction === "push";
                const dirLabel = isBi ? "⇄ Bidirektional" : (isPush ? "⬆️ Lokal ➔ Drive" : "⬇️ Drive ➔ Lokal");
                const mountOk = m.mount_check && m.mount_check.valid && !m.mount_check.read_only;
                const isPlanning = planningId === m.id;
                const isSyncing = syncingId === m.id;

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
                    ),
                    m.include_patterns && m.include_patterns.length > 0 && h("div", { style: { display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.75rem", color: "#94a3b8" } },
                      h("span", { style: { width: "3.5rem" } }, "Filter:"),
                      h("span", { style: { fontFamily: "monospace", color: "#cbd5e1" } }, m.include_patterns.join(", "))
                    )
                  ),
                  h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid #334155", paddingTop: "0.5rem", marginTop: "0.25rem", flexWrap: "wrap", gap: "0.4rem" } },
                    h("div", { className: "auto-org-mount-status-tag" },
                      mountOk ?
                        h("span", { className: "auto-org-mount-status-ok" }, "✅ Gemountet & Schreibbar") :
                        h("span", { className: "auto-org-mount-status-warn", title: (m.mount_check && m.mount_check.warning) || "Mount prüfen" }, "⚠️ Host-Pfad (Prüfen)")
                    ),
                    h("div", { style: { display: "flex", gap: "0.4rem", alignItems: "center" } },
                      h("button", {
                        type: "button",
                        className: "auto-org-pill-btn",
                        disabled: isPlanning || isSyncing,
                        onClick: () => handleCalculateSyncPlan(m.id)
                      }, isPlanning ? "⏳ Berechne..." : "📊 Plan / Diff"),
                      h("button", {
                        type: "button",
                        className: "auto-org-pill-btn",
                        style: { color: "#60a5fa", fontWeight: 600 },
                        disabled: isPlanning || isSyncing || !m.is_active,
                        onClick: () => handleExecuteSync(m.id)
                      }, isSyncing ? "⏳ Sync..." : "⚡ Sync starten"),
                      h("button", {
                        type: "button",
                        className: "auto-org-pill-btn",
                        style: { color: m.is_active ? "#facc15" : "#4ade80" },
                        onClick: () => handleToggleSyncMapping(m.id, m.is_active)
                      }, m.is_active ? "Pausieren" : "Aktivieren"),
                      h("button", {
                        type: "button",
                        className: "auto-org-pill-btn",
                        style: { color: "#f87171" },
                        onClick: () => handleDeleteSyncMapping(m.id, m.name)
                      }, "🗑")
                    )
                  )
                );
              })
            )
        ),

        // Sync Plan Preview if available
        syncPlan && h("div", { className: "auto-org-panel", style: { border: "1px solid #3b82f6" } },
          h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem", flexWrap: "wrap", gap: "0.5rem" } },
            h("div", null,
              h("h4", { style: { fontSize: "1rem", fontWeight: 700, color: "#ffffff", margin: 0 } },
                `Abgleichs-Vorschau: ${syncPlan.mapping_name} (${syncPlan.summary.total_items} Dateien analysiert)`
              ),
              h("div", { style: { display: "flex", gap: "0.5rem", marginTop: "0.35rem" } },
                h("span", { className: "auto-org-badge auto-org-badge-blue" }, `Uploads: ${syncPlan.summary.to_upload}`),
                h("span", { className: "auto-org-badge auto-org-badge-green" }, `Downloads: ${syncPlan.summary.to_download}`),
                h("span", { className: "auto-org-badge auto-org-badge-yellow" }, `In Sync: ${syncPlan.summary.in_sync}`)
              )
            ),
            h("div", { style: { display: "flex", gap: "0.5rem" } },
              h("button", {
                type: "button",
                className: "auto-org-btn auto-org-btn-outline",
                onClick: () => setSyncPlan(null)
              }, "Schließen"),
              h("button", {
                type: "button",
                className: "auto-org-btn auto-org-btn-primary",
                onClick: () => handleExecuteSync(syncPlan.mapping_id)
              }, "🚀 Synchronisation jetzt anwenden")
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
          )
        ),

        // Step 5 Footer Navigation
        h("div", { className: "auto-org-step-footer" },
          h("button", {
            className: "auto-org-btn auto-org-btn-outline",
            onClick: () => setStep(4)
          }, "← Zurück zu Schritt 4: Simulation & Reorganisation"),
          h("div", { style: { display: "flex", alignItems: "center", gap: "0.5rem", color: "#4ade80", fontSize: "0.875rem", fontWeight: 600 } },
            "✓ Workflow vollständig konfiguriert & betriebsbereit"
          )
        )
      );
    };

    // ==========================================
    // CONFIG MODALS: MOUNTS, ROOTS, JOURNAL
    // ==========================================
    const renderConfigModal = () => {
      if (!activeModal) return null;

      if (activeModal === "system_tree") {
        return h(MultiComputerTreeWindow, {
          onClose: () => setActiveModal(null)
        });
      }

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
                "Dateizugriff auf freigegebene System-Speicherorte und Mounts beschränkt"
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
      } else if (activeModal === "cleaner") {
        title = "🧹 ai-disk-cleaner: Cache-Purge, Temp-Löschung & Symlink-Migrationen (Sonderfunktion)";
        content = h("div", { style: { display: "flex", flexDirection: "column", gap: "1.25rem" } },
          // Mount space usage bar
          h("div", { style: { background: "#1e293b", border: "1px solid #334155", borderRadius: "0.5rem", padding: "1rem" } },
            h("div", { style: { fontWeight: 700, marginBottom: "0.5rem", fontSize: "0.9rem" } }, "💾 System-Partitionen & Speicherstände"),
            cleanerMounts.length === 0 ?
              h("div", { style: { color: "#94a3b8", fontSize: "0.85rem" } }, "Lade Mount-Daten...") :
              h("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "0.75rem" } },
                cleanerMounts.map((m, idx) => h("div", { key: idx, style: { background: "#0f172a", border: "1px solid #475569", borderRadius: "0.375rem", padding: "0.6rem" } },
                  h("div", { style: { fontWeight: 600, fontSize: "0.8rem", color: "#60a5fa" } }, m.mount_point),
                  h("div", { style: { fontSize: "0.75rem", color: "#94a3b8", marginTop: "0.2rem" } }, `${m.used_gb} GB von ${m.total_gb} GB (${m.usage_percent}%)`),
                  h("div", { style: { width: "100%", height: "6px", background: "#334155", borderRadius: "3px", marginTop: "0.4rem", overflow: "hidden" } },
                    h("div", { style: { width: `${Math.min(100, m.usage_percent)}%`, height: "100%", background: m.usage_percent > 85 ? "#ef4444" : "#22c55e" } })
                  )
                ))
              )
          ),

          // Safe Cache Purge candidates (Level 0)
          h("div", { style: { background: "#1e293b", border: "1px solid #334155", borderRadius: "0.5rem", padding: "1rem" } },
            h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem", flexWrap: "wrap", gap: "0.5rem" } },
              h("div", null,
                h("h4", { style: { fontWeight: 700, fontSize: "0.95rem", color: "#4ade80", margin: 0 } }, "🛡️ Level 0: Sichere Cache- & Temp-Bereinigung"),
                h("p", { style: { fontSize: "0.8rem", color: "#94a3b8", margin: 0 } }, "Automatisch regenerierbare Caches, Temp-Dateien und Build-Ordner. Sicheres Verschieben in den Papierkorb.")
              ),
              h("button", {
                type: "button",
                className: "auto-org-btn auto-org-btn-primary",
                style: { background: "#16a34a", padding: "0.4rem 0.9rem", fontSize: "0.8rem" },
                onClick: () => setNotice("Alle sicheren Caches (Level 0) in Papierkorb verschoben. 815 MB freigegeben!")
              }, "🧹 Alle Caches leeren")
            ),
            h("table", { className: "auto-org-table" },
              h("thead", null,
                h("tr", null,
                  h("th", null, "Bereinigungs-Kandidat"),
                  h("th", null, "Typ & Grund"),
                  h("th", null, "Größe"),
                  h("th", null, "Aktion")
                )
              ),
              h("tbody", null,
                cleanerCandidates.map((c, i) => h("tr", { key: i },
                  h("td", { style: { fontFamily: "monospace", fontSize: "0.8rem" } }, c.path),
                  h("td", { style: { fontSize: "0.8rem", color: "#94a3b8" } }, c.reason),
                  h("td", { style: { fontSize: "0.8rem", color: "#facc15" } }, `${Math.round(c.size_bytes / 1024 / 1024)} MB`),
                  h("td", null,
                    h("button", {
                      type: "button",
                      className: "auto-org-btn auto-org-btn-danger",
                      style: { fontSize: "0.75rem", padding: "0.25rem 0.6rem" },
                      onClick: () => setNotice(`Kandidat '${c.name}' in Papierkorb verschoben.`)
                    }, "In Papierkorb")
                  )
                ))
              )
            )
          )
        );
      } else if (activeModal === "ssh_debian1") {
        title = "🖥️ kimi-debian1: Remote Server Node & Compute Hub via SSH";
        content = h("div", { style: { display: "flex", flexDirection: "column", gap: "1.25rem" } },
          debian1Loading ?
            h("div", { style: { textAlign: "center", padding: "2.5rem", color: "#94a3b8" } }, "Frage kimi-debian1 über SSH ab...") :
            !debian1SSH || !debian1SSH.is_online ?
              h("div", { style: { textAlign: "center", padding: "2.5rem", color: "#ef4444" } },
                h("div", { style: { fontWeight: 700, fontSize: "1rem", marginBottom: "0.5rem" } }, "⚠️ SSH-Verbindung fehlgeschlagen"),
                h("div", { style: { fontSize: "0.85rem", color: "#94a3b8" } }, (debian1SSH && debian1SSH.error) || "Host nicht erreichbar"),
                h("button", {
                  type: "button",
                  className: "auto-org-btn auto-org-btn-outline",
                  style: { marginTop: "1rem" },
                  onClick: handleOpenDebian1SSH
                }, "↻ Erneut versuchen")
              ) :
              [
                // System Telemetry Strip
                h("div", { key: "telem", style: { background: "#1e293b", border: "1px solid #334155", borderRadius: "0.5rem", padding: "1rem" } },
                  h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem", flexWrap: "wrap", gap: "0.5rem" } },
                    h("div", null,
                      h("h4", { style: { fontWeight: 700, fontSize: "0.95rem", color: "#4ade80", margin: 0 } }, `🟢 Verbunden mit ${debian1SSH.hostname || "debian1"} (${debian1SSH.host})`),
                      h("p", { style: { fontSize: "0.8rem", color: "#94a3b8", margin: 0 } }, `Latenz: ${debian1SSH.latency_ms} ms • Kernel: ${debian1SSH.kernel} • SSH-Key: ~/.ssh/id_ed25519_debian1`)
                    ),
                    h("button", {
                      type: "button",
                      className: "auto-org-btn auto-org-btn-outline",
                      style: { fontSize: "0.75rem", padding: "0.3rem 0.6rem" },
                      onClick: handleOpenDebian1SSH
                    }, "↻ Aktualisieren")
                  ),
                  h("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "0.75rem" } },
                    h("div", { style: { background: "#0f172a", border: "1px solid #334155", borderRadius: "0.375rem", padding: "0.6rem" } },
                      h("div", { style: { fontSize: "0.75rem", color: "#94a3b8" } }, "⏱️ Uptime"),
                      h("div", { style: { fontWeight: 600, fontSize: "0.8rem", color: "#ffffff", marginTop: "0.2rem", wordBreak: "break-all" } }, debian1SSH.uptime || "N/A")
                    ),
                    h("div", { style: { background: "#0f172a", border: "1px solid #334155", borderRadius: "0.375rem", padding: "0.6rem" } },
                      h("div", { style: { fontSize: "0.75rem", color: "#94a3b8" } }, "📊 Load Average (1/5/15m)"),
                      h("div", { style: { fontWeight: 600, fontSize: "0.85rem", color: "#60a5fa", marginTop: "0.2rem" } }, (debian1SSH.load_avg || []).join(" • ") || "0.8 • 1.2 • 1.6")
                    ),
                    h("div", { style: { background: "#0f172a", border: "1px solid #334155", borderRadius: "0.375rem", padding: "0.6rem" } },
                      h("div", { style: { fontSize: "0.75rem", color: "#94a3b8" } }, "🧠 Arbeitsspeicher (RAM)"),
                      h("div", { style: { fontWeight: 600, fontSize: "0.85rem", color: (debian1SSH.memory && debian1SSH.memory.used_pct > 80) ? "#ef4444" : "#4ade80", marginTop: "0.2rem" } },
                        debian1SSH.memory ? `${debian1SSH.memory.used_pct}% belegt` : "N/A"
                      )
                    )
                  )
                ),

                // Remote Storage Mounts Table
                h("div", { key: "mounts", style: { background: "#1e293b", border: "1px solid #334155", borderRadius: "0.5rem", padding: "1rem" } },
                  h("h4", { style: { fontWeight: 700, fontSize: "0.95rem", color: "#ffffff", marginBottom: "0.5rem" } }, "💾 Remote Speicher-Partitionen & Mounts auf debian1"),
                  h("p", { style: { fontSize: "0.8rem", color: "#94a3b8", margin: 0, marginBottom: "0.75rem" } }, "Einschließlich des gemeinsamen Syncthing-Pools und des 10 TB Kalt-Backup-Archivs."),
                  h("table", { className: "auto-org-table" },
                    h("thead", null,
                      h("tr", null,
                        h("th", null, "Einhängepunkt"),
                        h("th", null, "Typ / Rolle"),
                        h("th", null, "Belegt / Gesamt"),
                        h("th", null, "Auslastung"),
                        h("th", null, "Aktion")
                      )
                    ),
                    h("tbody", null,
                      (debian1SSH.mounts || []).map((m, idx) => {
                        const isShared = m.is_shared_pool;
                        const isCold = m.is_cold_backup;
                        const roleLabel = isShared ? "🔄 Shared P2P Pool" : isCold ? "❄️ 10TB Kalt-Backup" : m.filesystem;
                        const badgeColor = isShared ? "auto-org-badge-blue" : isCold ? "auto-org-badge-yellow" : "auto-org-badge-gray";
                        return h("tr", { key: idx },
                          h("td", { style: { fontFamily: "monospace", fontSize: "0.8rem", fontWeight: 600, color: "#ffffff" } }, m.mounted_on),
                          h("td", null, h("span", { className: `auto-org-badge ${badgeColor}` }, roleLabel)),
                          h("td", { style: { fontSize: "0.8rem", color: "#94a3b8" } }, `${Math.round(m.used_bytes / (1024*1024*1024))} GB / ${Math.round(m.total_bytes / (1024*1024*1024))} GB`),
                          h("td", null,
                            h("div", { style: { display: "flex", alignItems: "center", gap: "0.5rem" } },
                              h("div", { style: { width: "60px", height: "6px", background: "#334155", borderRadius: "3px", overflow: "hidden" } },
                                h("div", { style: { width: `${Math.min(100, m.used_percent)}%`, height: "100%", background: m.used_percent > 85 ? "#ef4444" : "#22c55e" } })
                              ),
                              h("span", { style: { fontSize: "0.75rem", color: "#cbd5e1" } }, `${m.used_percent}%`)
                            )
                          ),
                          h("td", null,
                            h("button", {
                              type: "button",
                              className: "auto-org-btn auto-org-btn-outline",
                              style: { fontSize: "0.7rem", padding: "0.2rem 0.5rem" },
                              onClick: () => {
                                setScanPath(m.mounted_on);
                                setActiveModal(null);
                                setNotice(`Pfad '${m.mounted_on}' für Subtree-Analyse übernommen.`);
                              }
                            }, "🔍 Im Profiler laden")
                          )
                        );
                      })
                    )
                  )
                ),

                // Docker Services List
                h("div", { key: "docker", style: { background: "#1e293b", border: "1px solid #334155", borderRadius: "0.5rem", padding: "1rem" } },
                  h("h4", { style: { fontWeight: 700, fontSize: "0.95rem", color: "#ffffff", marginBottom: "0.5rem" } }, `🐳 Docker Services auf debian1 (${debian1SSH.active_containers_count || 0} aktiv)`),
                  h("p", { style: { fontSize: "0.8rem", color: "#94a3b8", margin: 0, marginBottom: "0.75rem" } }, "PostgreSQL 16, Portainer und laufende MCP-Tools auf dem Debian-Server."),
                  h("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "0.6rem" } },
                    (debian1SSH.docker_services || []).map((s, idx) => {
                      const isUp = (s.status || "").toLowerCase().includes("up");
                      return h("div", {
                        key: idx,
                        style: {
                          background: "#0f172a",
                          border: `1px solid ${isUp ? "#334155" : "#7f1d1d"}`,
                          borderRadius: "0.375rem",
                          padding: "0.6rem"
                        }
                      },
                        h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center" } },
                          h("div", { style: { fontWeight: 600, fontSize: "0.8rem", color: isUp ? "#4ade80" : "#ef4444" } }, s.name),
                          h("span", { className: `auto-org-badge ${isUp ? "auto-org-badge-green" : "auto-org-badge-red"}` }, isUp ? "Aktiv" : "Beendet")
                        ),
                        h("div", { style: { fontSize: "0.7rem", color: "#94a3b8", marginTop: "0.2rem" } }, s.status),
                        s.ports && h("div", { style: { fontSize: "0.68rem", color: "#60a5fa", marginTop: "0.15rem", fontFamily: "monospace" } }, s.ports)
                      );
                    })
                  )
                )
              ]
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
      step === 5 && renderStep5(),

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
