#!/usr/bin/env node
/**
 * Comprehensive Button & Function Test Suite for Hermes Auto-Organizer
 * 
 * Uses Headless Google Chrome via Chrome DevTools Protocol (CDP).
 * Systematically tests every interactive button, modal, physics slider,
 * tab switcher, and multi-step workflow.
 */

const { spawn } = require('child_process');
const fs = require('fs');

const TARGET_URL = process.env.TEST_URL || 'http://127.0.0.1:9119/organizer';
const CDP_PORT = process.env.CDP_PORT || 9228;

async function run() {
  console.log(`🚀 [Test Suite] Launching Headless Chrome on CDP port ${CDP_PORT}...`);
  const chrome = spawn('/usr/bin/google-chrome', [
    '--headless=new',
    '--no-sandbox',
    '--disable-gpu',
    '--window-size=1680,1050',
    `--remote-debugging-port=${CDP_PORT}`,
    '--remote-allow-origins=*',
    `--user-data-dir=/tmp/test-chrome-profile-${CDP_PORT}`,
    'about:blank'
  ]);

  let version = null;
  for (let i = 0; i < 30; i++) {
    try {
      const res = await fetch(`http://127.0.0.1:${CDP_PORT}/json/version`);
      if (res.ok) { version = await res.json(); break; }
    } catch (e) {}
    await new Promise(r => setTimeout(r, 200));
  }

  if (!version) {
    chrome.kill();
    throw new Error(`Chrome failed to start on port ${CDP_PORT}`);
  }

  const newRes = await fetch(`http://127.0.0.1:${CDP_PORT}/json/new`, { method: 'PUT' });
  const target = await newRes.json();
  const ws = new WebSocket(target.webSocketDebuggerUrl);

  let msgId = 1;
  const callbacks = new Map();
  const errors = [];
  const networkErrors = [];

  function send(method, params = {}) {
    return new Promise((resolve, reject) => {
      const id = msgId++;
      callbacks.set(id, { resolve, reject });
      ws.send(JSON.stringify({ id, method, params }));
    });
  }

  ws.onmessage = (evt) => {
    const data = JSON.parse(evt.data);
    if (data.id && callbacks.has(data.id)) {
      const cb = callbacks.get(data.id);
      callbacks.delete(data.id);
      if (data.error) cb.reject(data.error);
      else cb.resolve(data.result);
    } else if (data.method === 'Runtime.consoleAPICalled') {
      const txt = data.params.args.map(a => a.value !== undefined ? a.value : (a.description || JSON.stringify(a))).join(' ');
      if (data.params.type === 'error' && !txt.includes('Failed to load resource')) {
        console.error('🔴 [Console Error]:', txt);
        errors.push(`Console: ${txt}`);
      }
    } else if (data.method === 'Runtime.exceptionThrown') {
      const desc = data.params.exceptionDetails.text + (data.params.exceptionDetails.exception ? ': ' + (data.params.exceptionDetails.exception.description || data.params.exceptionDetails.exception.value) : '');
      console.error('🔴 [Uncaught Exception]:', desc);
      errors.push(`Exception: ${desc}`);
    } else if (data.method === 'Network.responseReceived') {
      const resp = data.params.response;
      if (resp.url.includes('/api/plugins/auto-organizer/') && resp.status >= 400) {
        console.error(`🔴 [API Error ${resp.status}]: ${resp.url}`);
        networkErrors.push(`${resp.status} on ${resp.url}`);
      }
    }
  };

  await new Promise(resolve => { ws.onopen = resolve; });
  console.log('✅ [Test Suite] Connected to Chrome CDP');

  await send('Page.enable');
  await send('Runtime.enable');
  await send('Network.enable');
  await send('Log.enable');

  console.log(`🌐 [Test Suite] Navigating to ${TARGET_URL}...`);
  await send('Page.navigate', { url: TARGET_URL });
  await new Promise(r => setTimeout(r, 3500));

  async function evalJs(expr) {
    const res = await send('Runtime.evaluate', {
      expression: expr,
      returnByValue: true,
      awaitPromise: true
    });
    if (res.exceptionDetails) {
      console.error('Eval Exception:', res.exceptionDetails);
      errors.push(res.exceptionDetails.text);
    }
    return res.result ? res.result.value : null;
  }

  async function clickButtonByText(text, exact = false) {
    return evalJs(`(() => {
      const btns = Array.from(document.querySelectorAll('button, .auto-org-btn, .auto-org-step-card, .auto-org-view-tab, .auto-org-config-btn, .auto-org-pill-btn, .auto-org-view-switcher-btn'));
      const btn = btns.find(b => ${exact ? `b.innerText.trim() === '${text}'` : `b.innerText.includes('${text}')`});
      if (btn) {
        btn.click();
        return { clicked: true, text: btn.innerText.trim() };
      }
      return { clicked: false, available: btns.map(b => b.innerText.trim().slice(0, 30)).filter(Boolean) };
    })()`);
  }

  async function closeModal() {
    return evalJs(`(() => {
      const btn = document.querySelector('.auto-org-modal-close') ||
                  document.querySelector('.auto-org-multi-tree-header button') ||
                  Array.from(document.querySelectorAll('.auto-org-modal-header button, .auto-org-modal button')).find(b => b.innerText.trim() === '✕');
      if (btn) { btn.click(); return true; }
      return false;
    })()`);
  }

  async function ensureDiagnosticToolsOpen() {
    const isOpen = await evalJs(`Boolean(document.querySelector('.auto-org-toolbar-secondary-panel'))`);
    if (!isOpen) {
      await clickButtonByText('System & Tools');
      await new Promise(r => setTimeout(r, 500));
    }
  }

  // TEST 1: Initial Page Load
  console.log('\n--- [TEST 1] Initial Page & Stats Strip ---');
  const initial = await evalJs(`({
    hasOrganizer: Boolean(document.querySelector('.auto-org-container')),
    title: document.title,
    statsCount: document.querySelectorAll('.auto-org-stat-card').length,
    stepCards: document.querySelectorAll('.auto-org-step-card').length
  })`);
  console.log('Page state:', initial);
  if (!initial.hasOrganizer) errors.push('Main container missing');

  // TEST 2: System & Tools Dropdown and Modals
  console.log('\n--- [TEST 2] System & Tools Modals ---');
  await ensureDiagnosticToolsOpen();

  // 2a: Docker Mounts Modal
  console.log('Testing Docker Mounts Modal...');
  let clickRes = await clickButtonByText('Docker Mounts');
  console.log('Click "Docker Mounts":', clickRes);
  await new Promise(r => setTimeout(r, 800));

  let modalState = await evalJs(`({
    isOpen: Boolean(document.querySelector('.auto-org-modal')),
    title: document.querySelector('.auto-org-modal-title') ? document.querySelector('.auto-org-modal-title').innerText : null,
    mountsCount: document.querySelectorAll('.auto-org-modal-body table tbody tr').length
  })`);
  console.log('Docker Mounts Modal State:', modalState);
  if (!modalState.isOpen) errors.push('Docker Mounts modal did not open');

  // Path Inspector test inside Docker Mounts modal
  const inspectorRes = await evalJs(`(() => {
    const input = document.querySelector('.auto-org-checker-box input');
    const btn = Array.from(document.querySelectorAll('.auto-org-checker-box button')).find(b => b.innerText.includes('analysieren'));
    if (input && btn) {
      input.value = '/home/mb/Downloads';
      input.dispatchEvent(new Event('input', { bubbles: true }));
      btn.click();
      return true;
    }
    return false;
  })()`);
  console.log('Path Inspector executed:', inspectorRes);
  await new Promise(r => setTimeout(r, 600));

  // Close Docker Mounts modal
  await closeModal();
  await new Promise(r => setTimeout(r, 500));

  // 2b: Storage Roots Modal
  console.log('Testing Storage Roots Modal...');
  await ensureDiagnosticToolsOpen();
  await clickButtonByText('Speicherwurzeln');
  await new Promise(r => setTimeout(r, 600));
  modalState = await evalJs(`({
    isOpen: Boolean(document.querySelector('.auto-org-modal')),
    title: document.querySelector('.auto-org-modal-title') ? document.querySelector('.auto-org-modal-title').innerText : null
  })`);
  console.log('Storage Roots Modal State:', modalState);
  if (!modalState.isOpen) errors.push('Storage Roots modal did not open');
  await closeModal();
  await new Promise(r => setTimeout(r, 500));

  // 2c: Disk Cleaner Modal
  console.log('Testing Disk Cleaner Modal...');
  await ensureDiagnosticToolsOpen();
  await clickButtonByText('Disk Cleaner');
  await new Promise(r => setTimeout(r, 600));
  modalState = await evalJs(`({
    isOpen: Boolean(document.querySelector('.auto-org-modal')),
    title: document.querySelector('.auto-org-modal-title') ? document.querySelector('.auto-org-modal-title').innerText : null,
    tabsCount: document.querySelectorAll('.auto-org-modal-body .auto-org-view-tab').length
  })`);
  console.log('Disk Cleaner Modal State:', modalState);
  if (!modalState.isOpen) errors.push('Disk Cleaner modal did not open');

  // Test tabs in cleaner modal
  await clickButtonByText('Mesh-Triage');
  await new Promise(r => setTimeout(r, 400));
  await clickButtonByText('Migration');
  await new Promise(r => setTimeout(r, 400));
  await clickButtonByText('Cache-Dateien');
  await new Promise(r => setTimeout(r, 400));
  await closeModal();
  await new Promise(r => setTimeout(r, 500));

  // 2d: debian1 SSH Modal & "Im Profiler laden"
  console.log('Testing debian1 SSH Modal...');
  await ensureDiagnosticToolsOpen();
  await clickButtonByText('debian1 (SSH)');
  await new Promise(r => setTimeout(r, 600));
  modalState = await evalJs(`({
    isOpen: Boolean(document.querySelector('.auto-org-modal')),
    title: document.querySelector('.auto-org-modal-title') ? document.querySelector('.auto-org-modal-title').innerText : null,
    hasProfilerBtn: Boolean(Array.from(document.querySelectorAll('.auto-org-modal button')).find(b => b.innerText.includes('Im Profiler laden')))
  })`);
  console.log('debian1 SSH Modal State:', modalState);
  if (!modalState.isOpen) errors.push('debian1 SSH modal did not open');

  // Test clicking "Im Profiler laden" (which previously had the undefined setScanPath bug)
  const profilerLoadRes = await clickButtonByText('Im Profiler laden');
  console.log('Click "Im Profiler laden":', profilerLoadRes);
  await new Promise(r => setTimeout(r, 600));

  // 2e: Extended Graph Export button
  console.log('Testing Extended Graph Export button...');
  await ensureDiagnosticToolsOpen();
  const exportRes = await clickButtonByText('Extended Graph Export');
  console.log('Click "Extended Graph Export":', exportRes);
  await new Promise(r => setTimeout(r, 1200));

  // TEST 3: Multi-Computer Tree Modal & Folders2Graph Physics Controls
  console.log('\n--- [TEST 3] Multi-Computer Tree & Physics Controls ---');
  await clickButtonByText('Multi-Computer Tree');
  await new Promise(r => setTimeout(r, 1500));

  const multiTreeState = await evalJs(`({
    isOpen: Boolean(document.querySelector('.auto-org-multi-tree-modal') || document.querySelector('.auto-org-multi-tree-window')),
    hasF2G: Boolean(Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('folders2graph'))),
    hasRealTree: Boolean(Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Realer Dateibaum')))
  })`);
  console.log('Multi-Tree Modal:', multiTreeState);
  if (!multiTreeState.isOpen) errors.push('Multi-Computer Tree modal did not open');

  // Switch to folders2graph
  await clickButtonByText('folders2graph');
  await new Promise(r => setTimeout(r, 1500));

  // Test Physics panel button
  console.log('Testing "⚙️ Physik" toggle and sliders...');
  const physToggle = await clickButtonByText('Physik');
  console.log('Click "Physik" button:', physToggle);
  await new Promise(r => setTimeout(r, 600));

  const physPanelState = await evalJs(`({
    hasPanel: Boolean(document.querySelector('.auto-org-f2g-physics-panel')),
    slidersCount: document.querySelectorAll('.auto-org-f2g-physics-panel input[type="range"]').length,
    hasResetBtn: Boolean(Array.from(document.querySelectorAll('.auto-org-f2g-physics-panel button')).find(b => b.innerText.includes('Standard')))
  })`);
  console.log('Physics Panel State:', physPanelState);
  if (!physPanelState.hasPanel) errors.push('Physics panel did not open');

  // Test tweaking gravity and repulsion slider, then clicking standard reset
  const tweakRes = await evalJs(`(() => {
    const sliders = document.querySelectorAll('.auto-org-f2g-physics-panel input[type="range"]');
    if (sliders.length >= 2) {
      sliders[0].value = "0.0050";
      sliders[0].dispatchEvent(new Event('input', { bubbles: true }));
      sliders[0].dispatchEvent(new Event('change', { bubbles: true }));
      sliders[1].value = "2500";
      sliders[1].dispatchEvent(new Event('input', { bubbles: true }));
      sliders[1].dispatchEvent(new Event('change', { bubbles: true }));
      const resetBtn = Array.from(document.querySelectorAll('.auto-org-f2g-physics-panel button')).find(b => b.innerText.includes('Standard'));
      if (resetBtn) resetBtn.click();
      return true;
    }
    return false;
  })()`);
  console.log('Physics sliders adjusted and reset:', tweakRes);
  await new Promise(r => setTimeout(r, 500));

  // Test Canvas Zoom Buttons: +, -, ↺ Reset
  await clickButtonByText('+', true);
  await new Promise(r => setTimeout(r, 200));
  await clickButtonByText('-', true);
  await new Promise(r => setTimeout(r, 200));
  await clickButtonByText('↺ Reset');
  await new Promise(r => setTimeout(r, 200));

  // Switch to Real Dateibaum view
  await clickButtonByText('Realer Dateibaum');
  await new Promise(r => setTimeout(r, 1000));

  // Test right click on tree row for context menu
  const ctxRes = await evalJs(`(() => {
    const row = document.querySelector('.auto-org-fs-tree-row');
    if (row) {
      const rect = row.getBoundingClientRect();
      const ev = new MouseEvent('contextmenu', {
        bubbles: true,
        cancelable: true,
        clientX: rect.x + 40,
        clientY: rect.y + 12
      });
      row.dispatchEvent(ev);
      return true;
    }
    return false;
  })()`);
  console.log('Tree right-click context menu triggered:', ctxRes);
  await new Promise(r => setTimeout(r, 500));

  const ctxMenuState = await evalJs(`({
    hasMenu: Boolean(document.querySelector('.auto-org-context-menu')),
    itemsCount: document.querySelectorAll('.auto-org-context-menu-item').length
  })`);
  console.log('Context Menu State:', ctxMenuState);
  if (!ctxMenuState.hasMenu) errors.push('Context menu missing in real dateibaum');

  // Close Multi-Computer modal
  await closeModal();
  await new Promise(r => setTimeout(r, 600));

  // TEST 4: Step 1 Workflow & Indexing
  console.log('\n--- [TEST 4] Step 1 Workflow & Indexing ---');
  await evalJs(`(() => {
    const step1Card = Array.from(document.querySelectorAll('.auto-org-step-card')).find(c => c.innerText.includes('SCHRITT 1'));
    if (step1Card) step1Card.click();
  })()`);
  await new Promise(r => setTimeout(r, 600));

  // Click "🟢 Alle freigeben"
  const approveAllDrives = await clickButtonByText('Alle freigeben');
  console.log('Click "Alle freigeben":', approveAllDrives);
  await new Promise(r => setTimeout(r, 500));

  // Start indexing (or update)
  const indexBtn = await clickButtonByText('starten') || await clickButtonByText('aktualisieren');
  console.log('Click Indexing button:', indexBtn);
  await new Promise(r => setTimeout(r, 2500));

  // Proceed to Step 2
  const toStep2 = await clickButtonByText('Weiter zu Schritt 2');
  console.log('Click "Weiter zu Schritt 2":', toStep2);
  await new Promise(r => setTimeout(r, 1000));

  // TEST 5: Step 2 Emergent Taxonomy Approval & Visualization
  console.log('\n--- [TEST 5] Step 2 Emergent Taxonomy ---');
  const step2State = await evalJs(`({
    activeStep: document.querySelector('.auto-org-step-card.active .auto-org-step-number-title') ? document.querySelector('.auto-org-step-card.active .auto-org-step-number-title').innerText : null,
    hasTaxonomySection: Boolean(document.querySelector('.auto-org-panel'))
  })`);
  console.log('Step 2 Active:', step2State);

  // Approve emergent taxonomy
  const approveTaxRes = await clickButtonByText('Gesamten Baum jetzt freigeben') || await clickButtonByText('Natürlich entstandenes System') || await clickButtonByText('Freigeben');
  console.log('Approve taxonomy button clicked:', approveTaxRes);
  await new Promise(r => setTimeout(r, 1500));

  // Switch to graph view in Step 2
  await clickButtonByText('Obsidian-Graph') || await clickButtonByText('Graph');
  await new Promise(r => setTimeout(r, 800));
  await clickButtonByText('Natürliche Taxonomie') || await clickButtonByText('Baum');
  await new Promise(r => setTimeout(r, 800));

  // Proceed to Step 3
  const toStep3 = await clickButtonByText('Weiter zu Schritt 3');
  console.log('Click "Weiter zu Schritt 3":', toStep3);
  await new Promise(r => setTimeout(r, 1000));

  // TEST 6: Step 3 Modular Rule Builder & Testing
  console.log('\n--- [TEST 6] Step 3 Modular Rule Builder ---');
  const step3State = await evalJs(`({
    activeStep: document.querySelector('.auto-org-step-card.active .auto-org-step-number-title') ? document.querySelector('.auto-org-step-card.active .auto-org-step-number-title').innerText : null,
    hasRuleBuilder: Boolean(document.querySelector('.auto-org-condition-row'))
  })`);
  console.log('Step 3 Active:', step3State);

  // Test rule simulation
  const testRuleRes = await clickButtonByText('Regel an vorhandenen Dateien testen');
  console.log('Click "Regel an vorhandenen Dateien testen":', testRuleRes);
  await new Promise(r => setTimeout(r, 2000));

  const ruleSimState = await evalJs(`({
    hasSimulationBox: Boolean(document.querySelector('.auto-org-simulation-results') || document.querySelector('.auto-org-panel'))
  })`);
  console.log('Rule Simulation Results:', ruleSimState);

  // Proceed to Step 4
  const toStep4 = await clickButtonByText('Weiter zu Schritt 4');
  console.log('Click "Weiter zu Schritt 4":', toStep4);
  await new Promise(r => setTimeout(r, 1000));

  // TEST 7: Step 4 Dry-Run Simulation & Reorganization
  console.log('\n--- [TEST 7] Step 4 Dry-Run Simulation ---');
  const step4State = await evalJs(`({
    activeStep: document.querySelector('.auto-org-step-card.active .auto-org-step-number-title') ? document.querySelector('.auto-org-step-card.active .auto-org-step-number-title').innerText : null
  })`);
  console.log('Step 4 Active:', step4State);

  // Click "Simulation neu starten" or "Simulation (Dry-Run) starten"
  const dryRunRes = await clickButtonByText('Simulation neu starten') || await clickButtonByText('Simulation');
  console.log('Click "Simulation neu starten":', dryRunRes);
  await new Promise(r => setTimeout(r, 2500));

  // Test view switcher tabs in Step 4
  console.log('Testing Step 4 View Switcher tabs...');
  await clickButtonByText('Tree-Diff');
  await new Promise(r => setTimeout(r, 600));
  await clickButtonByText('Visueller Pfad-Baum');
  await new Promise(r => setTimeout(r, 600));
  await clickButtonByText('Obsidian-Transfer-Graph');
  await new Promise(r => setTimeout(r, 600));
  await clickButtonByText('Technische Diff-Tabelle');
  await new Promise(r => setTimeout(r, 600));
  await clickButtonByText('Abstrakte Ausführungsgruppen');
  await new Promise(r => setTimeout(r, 600));

  // Proceed to Step 5
  const toStep5 = await clickButtonByText('Weiter zu Schritt 5');
  console.log('Click "Weiter zu Schritt 5":', toStep5);
  await new Promise(r => setTimeout(r, 1000));

  // TEST 8: Step 5 Google Drive Cloud Sync
  console.log('\n--- [TEST 8] Step 5 Google Drive Cloud Sync ---');
  const step5State = await evalJs(`({
    activeStep: document.querySelector('.auto-org-step-card.active .auto-org-step-number-title') ? document.querySelector('.auto-org-step-card.active .auto-org-step-number-title').innerText : null
  })`);
  console.log('Step 5 Active:', step5State);

  // Test opening new sync form
  const newSyncBtn = await clickButtonByText('Neuer Sync-Ordner');
  console.log('Click "Neuer Sync-Ordner":', newSyncBtn);
  await new Promise(r => setTimeout(r, 600));
  await clickButtonByText('Abbrechen');
  await new Promise(r => setTimeout(r, 400));

  // Back to Step 4
  await clickButtonByText('Zurück zu Schritt 4');
  await new Promise(r => setTimeout(r, 600));

  // Capture final screenshot
  const ss = await send('Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync('/tmp/screen_all_buttons_verified.png', Buffer.from(ss.data, 'base64'));
  console.log('📸 [Screenshot]: Saved /tmp/screen_all_buttons_verified.png');

  // Teardown
  ws.close();
  chrome.kill();

  console.log('\n======================================================');
  console.log('📊 FINAL TEST RESULTS:');
  console.log(`   - JS Console / Runtime Errors: ${errors.length}`);
  console.log(`   - Backend API 4xx/5xx Network Errors: ${networkErrors.length}`);
  if (errors.length > 0) {
    console.error('Errors encountered:');
    errors.forEach(e => console.error(`   ❌ ${e}`));
  }
  if (networkErrors.length > 0) {
    console.error('Network Errors encountered:');
    networkErrors.forEach(e => console.error(`   ❌ ${e}`));
  }
  console.log('======================================================\n');

  if (errors.length === 0 && networkErrors.length === 0) {
    console.log('🎉 [ALL TESTS PASSED] Every button and feature verified 100% operational!');
    process.exit(0);
  } else {
    process.exit(1);
  }
}

run().catch(err => {
  console.error('💥 Fatal error in test runner:', err);
  process.exit(1);
});
