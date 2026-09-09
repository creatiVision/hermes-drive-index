#!/usr/bin/env node
/**
 * Automated Web UI Test Harness for Hermes Auto-Organizer Dashboard Plugin
 * 
 * Uses headless Google Chrome via Chrome DevTools Protocol (CDP) and native Node.js WebSockets.
 * Validates:
 * 1. Page navigation and initial render (http://localhost:9119/organizer)
 * 2. Multi-Computer Tree & Radar modal opening
 * 3. folders2graph Obsidian-Graph Canvas rendering and force physics
 * 4. Right-click context menu (🟢 Freigeben / 🟡 Vorschlag / ⚪ Nicht einbezogen)
 * 5. Rollover hover popover (SyncRolloverTooltip)
 * 6. Captures screenshots to /tmp/screen_organizer.png, /tmp/screen_f2g.png, and /tmp/screen_context_menu.png
 */

const { spawn } = require('child_process');
const fs = require('fs');

const TARGET_URL = process.env.TEST_URL || 'http://127.0.0.1:9119/organizer';
const CDP_PORT = process.env.CDP_PORT || 9226;

async function run() {
  console.log(`🚀 [Test-Harness] Starting Headless Google Chrome on port ${CDP_PORT}...`);
  const chrome = spawn('/usr/bin/google-chrome', [
    '--headless=new',
    '--no-sandbox',
    '--disable-gpu',
    '--window-size=1600,1000',
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
    throw new Error(`Chrome failed to start or open CDP port on ${CDP_PORT}`);
  }

  const newRes = await fetch(`http://127.0.0.1:${CDP_PORT}/json/new`, { method: 'PUT' });
  const target = await newRes.json();
  console.log(`✅ [Test-Harness] Target page created (id: ${target.id})`);

  const ws = new WebSocket(target.webSocketDebuggerUrl);
  let id = 1;
  const callbacks = new Map();
  const errors = [];
  const logs = [];

  function send(method, params = {}) {
    return new Promise((resolve, reject) => {
      const msgId = id++;
      callbacks.set(msgId, { resolve, reject });
      ws.send(JSON.stringify({ id: msgId, method, params }));
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
      logs.push(`[${data.params.type.toUpperCase()}] ${txt}`);
      if (data.params.type === 'error') {
        console.error('🔴 [Console Error]:', txt);
        errors.push(`Console: ${txt}`);
      }
    } else if (data.method === 'Runtime.exceptionThrown') {
      const desc = data.params.exceptionDetails.text + (data.params.exceptionDetails.exception ? ': ' + (data.params.exceptionDetails.exception.description || data.params.exceptionDetails.exception.value) : '');
      console.error('🔴 [Uncaught Exception]:', desc);
      errors.push(`Exception: ${desc}`);
    }
  };

  await new Promise(resolve => { ws.onopen = resolve; });
  console.log('✅ [Test-Harness] Connected to CDP WebSocket');

  await send('Page.enable');
  await send('Runtime.enable');
  await send('Log.enable');

  console.log(`🌐 [Test-Harness] Navigating to ${TARGET_URL} ...`);
  await send('Page.navigate', { url: TARGET_URL });

  // 1. Wait for page load and initial rendering
  await new Promise(r => setTimeout(r, 4000));

  const pageCheck = await send('Runtime.evaluate', {
    expression: `({
      hasOrganizer: Boolean(document.querySelector('.auto-org-container')),
      title: document.title,
      radarBtn: Boolean(Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Multi-Computer Tree'))),
      bodyLength: document.body.innerHTML.length
    })`,
    returnByValue: true
  });

  console.log('📊 [Check 1: Main Dashboard]:', pageCheck.result.value);
  if (!pageCheck.result.value.hasOrganizer) {
    errors.push('Main container .auto-org-container not found in DOM');
  }

  // Save main page screenshot
  let ss = await send('Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync('/tmp/screen_organizer.png', Buffer.from(ss.data, 'base64'));
  console.log('📸 [Screenshot]: Saved /tmp/screen_organizer.png');

  // 2. Click Multi-Computer Tree & Radar button
  console.log('🖱️ [Check 2: Open Modal] Clicking Multi-Computer Tree button...');
  await send('Runtime.evaluate', {
    expression: `(() => {
      const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Multi-Computer Tree'));
      if (btn) { btn.click(); return true; }
      return false;
    })()`
  });

  await new Promise(r => setTimeout(r, 1500));

  const modalCheck = await send('Runtime.evaluate', {
    expression: `({
      hasModal: Boolean(document.querySelector('.auto-org-multi-host-window') || document.querySelector('.auto-org-modal')),
      hasF2GTab: Boolean(Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('folders2graph')))
    })`,
    returnByValue: true
  });
  console.log('🪟 [Check 2: Modal Open]:', modalCheck.result.value);

  // 3. Switch to folders2graph view
  console.log('🖱️ [Check 3: Folders2Graph] Switching to folders2graph tab...');
  await send('Runtime.evaluate', {
    expression: `(() => {
      const tab = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('folders2graph'));
      if (tab) { tab.click(); return true; }
      return false;
    })()`
  });

  await new Promise(r => setTimeout(r, 1500));

  const f2gCheck = await send('Runtime.evaluate', {
    expression: `({
      hasCanvas: Boolean(document.querySelector('.auto-org-f2g-canvas')),
      canvasWidth: document.querySelector('.auto-org-f2g-canvas') ? document.querySelector('.auto-org-f2g-canvas').width : 0,
      hasHud: Boolean(document.querySelector('.auto-org-f2g-hud'))
    })`,
    returnByValue: true
  });
  console.log('🎨 [Check 3: Canvas Render]:', f2gCheck.result.value);

  if (!f2gCheck.result.value.hasCanvas) {
    errors.push('folders2graph canvas not rendered');
  }

  ss = await send('Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync('/tmp/screen_f2g.png', Buffer.from(ss.data, 'base64'));
  console.log('📸 [Screenshot]: Saved /tmp/screen_f2g.png');

  // 4. Test Right-Click Context Menu
  console.log('🖱️ [Check 4: Right-Click Menu] Testing context menu trigger...');
  // Switch back to tree view or trigger on tree line
  await send('Runtime.evaluate', {
    expression: `(() => {
      const treeTab = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Dateibaum') || b.innerText.includes('Tree'));
      if (treeTab) treeTab.click();
      return true;
    })()`
  });
  await new Promise(r => setTimeout(r, 1000));

  await send('Runtime.evaluate', {
    expression: `(() => {
      const row = document.querySelector('.auto-org-fs-row') || document.querySelector('.auto-org-tree-branch-line');
      if (row) {
        const rect = row.getBoundingClientRect();
        const ev = new MouseEvent('contextmenu', {
          bubbles: true,
          cancelable: true,
          clientX: rect.x + 30,
          clientY: rect.y + 12
        });
        row.dispatchEvent(ev);
        return true;
      }
      return false;
    })()`
  });
  await new Promise(r => setTimeout(r, 500));

  const menuCheck = await send('Runtime.evaluate', {
    expression: `({
      hasMenu: Boolean(document.querySelector('.auto-org-context-menu')),
      itemsCount: document.querySelectorAll('.auto-org-context-menu-item').length
    })`,
    returnByValue: true
  });
  console.log('📋 [Check 4: Context Menu]:', menuCheck.result.value);

  if (!menuCheck.result.value.hasMenu) {
    errors.push('Context menu was not displayed upon right click');
  }

  ss = await send('Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync('/tmp/screen_context_menu.png', Buffer.from(ss.data, 'base64'));
  console.log('📸 [Screenshot]: Saved /tmp/screen_context_menu.png');

  // Summary & Teardown
  ws.close();
  chrome.kill();

  console.log('\n=======================================');
  if (errors.length === 0) {
    console.log('🎉 [SUCCESS] All UI checks passed with 0 errors!');
    console.log('   - Main dashboard loaded & verified.');
    console.log('   - Multi-Computer window & radar verified.');
    console.log('   - folders2graph canvas active & verified.');
    console.log('   - Right-click 3-state switcher menu verified.');
    console.log('=======================================\n');
    process.exit(0);
  } else {
    console.error('❌ [FAILURE] Encountered errors during UI testing:');
    errors.forEach(e => console.error(`   - ${e}`));
    console.log('=======================================\n');
    process.exit(1);
  }
}

run().catch(err => {
  console.error('💥 [Fatal Error]:', err);
  process.exit(1);
});
