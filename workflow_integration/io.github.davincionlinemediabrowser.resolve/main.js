// DaVinci Resolve Studio Workflow Integration wrapper.
// It starts the local Python API server, loads the shared web UI, and uses
// Resolve's JavaScript API for Media Pool imports when running inside WFI.

const { app, BrowserWindow, ipcMain, screen, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const os = require('os');
const { spawn } = require('child_process');
const WorkflowIntegration = require('./WorkflowIntegration.node');

const PLUGIN_ID = 'io.github.davincionlinemediabrowser.resolve';
const IMPORT_BIN_NAME = 'Online Media Browser';
// Default to a slim, full-height sidebar flush against the right screen edge so
// the floating WFI window reads like a docked Resolve panel rather than a window.
const DEFAULT_WIDTH = 460;
const MIN_WIDTH = 360;
const MIN_HEIGHT = 480;
// How close (px) to a screen edge a drag must end to snap the window flush.
const EDGE_SNAP_THRESHOLD = 36;
// Keep the panel above Resolve so it stays visible like an embedded sidebar.
const KEEP_ABOVE = true;
// Bump when the default window geometry changes so stale saved states reset once.
const STATE_VERSION = 2;

let mainWindow = null;
let serverProcess = null;
let serverInfo = null;
let resolveObj = null;
let projectManagerObj = null;
let saveBoundsTimer = null;

function runtimeConfig() {
  const configPath = path.join(__dirname, 'runtime-config.json');
  const defaults = {
    projectRoot: path.join(os.homedir(), '.davinci_plugins', 'media_browser'),
    configPath: path.join(os.homedir(), '.davinci_plugins', 'api_keys.json'),
    python: '',
  };

  try {
    if (fs.existsSync(configPath)) {
      return Object.assign(defaults, JSON.parse(fs.readFileSync(configPath, 'utf8')));
    }
  } catch (error) {
    writeRuntimeLog(`Could not read runtime-config.json: ${error.message}`);
  }

  return defaults;
}

function pythonCandidates(config) {
  const candidates = [
    process.env.DAVINCI_ONLINE_BROWSER_PYTHON,
    config.python,
    path.join(config.projectRoot, '.venv', 'bin', 'python'),
    '/usr/bin/python3',
    '/opt/homebrew/bin/python3',
    '/usr/local/bin/python3',
    'python3',
  ];

  return candidates.filter((candidate, index) => {
    return Boolean(candidate) && candidates.indexOf(candidate) === index;
  });
}

function pythonEnv(config) {
  const env = Object.assign({}, process.env);
  const pathParts = [
    '/usr/bin',
    '/bin',
    '/usr/sbin',
    '/sbin',
    '/opt/homebrew/bin',
    '/usr/local/bin',
    env.PATH || '',
  ].filter(Boolean);

  env.PATH = pathParts.join(':');
  env.PYTHONPATH = [config.projectRoot, env.PYTHONPATH || ''].filter(Boolean).join(':');
  return env;
}

function windowStatePath() {
  return path.join(os.homedir(), '.davinci_plugins', 'wfi-window-state.json');
}

function readWindowState() {
  try {
    const filePath = windowStatePath();
    if (fs.existsSync(filePath)) {
      return JSON.parse(fs.readFileSync(filePath, 'utf8'));
    }
  } catch (error) {
    writeRuntimeLog(`Could not read window state: ${error.message}`);
  }
  return null;
}

function writeWindowState(bounds) {
  try {
    const filePath = windowStatePath();
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    const payload = Object.assign({ version: STATE_VERSION }, bounds);
    fs.writeFileSync(filePath, JSON.stringify(payload, null, 2));
  } catch (error) {
    writeRuntimeLog(`Could not write window state: ${error.message}`);
  }
}

function boundsIntersectWorkArea(bounds, workArea) {
  const left = Math.max(bounds.x, workArea.x);
  const right = Math.min(bounds.x + bounds.width, workArea.x + workArea.width);
  const top = Math.max(bounds.y, workArea.y);
  const bottom = Math.min(bounds.y + bounds.height, workArea.y + workArea.height);
  return right - left > 120 && bottom - top > 120;
}

function defaultWindowBounds() {
  const { workArea } = screen.getPrimaryDisplay();
  const width = Math.min(DEFAULT_WIDTH, Math.max(MIN_WIDTH, Math.round(workArea.width * 0.46)));
  return {
    x: workArea.x + workArea.width - width,
    y: workArea.y,
    width,
    height: workArea.height,
  };
}

function loadWindowBounds() {
  const saved = readWindowState();
  if (
    saved
    && saved.version === STATE_VERSION
    && Number.isFinite(saved.x)
    && Number.isFinite(saved.y)
    && Number.isFinite(saved.width)
    && Number.isFinite(saved.height)
    && saved.width >= MIN_WIDTH
    && saved.height >= MIN_HEIGHT
    && screen.getAllDisplays().some((display) => boundsIntersectWorkArea(saved, display.workArea))
  ) {
    return saved;
  }
  return defaultWindowBounds();
}

// Snap a window flush against the nearest left/right screen edge (and to full
// height) when a drag ends close to it, so it behaves like a docked sidebar.
function snapBoundsToEdges(bounds) {
  const display = screen.getDisplayMatching(bounds);
  const wa = display.workArea;
  const snapped = Object.assign({}, bounds);
  const nearRight = Math.abs((bounds.x + bounds.width) - (wa.x + wa.width)) <= EDGE_SNAP_THRESHOLD;
  const nearLeft = Math.abs(bounds.x - wa.x) <= EDGE_SNAP_THRESHOLD;
  if (nearRight) {
    snapped.x = wa.x + wa.width - bounds.width;
  } else if (nearLeft) {
    snapped.x = wa.x;
  }
  if (nearRight || nearLeft) {
    snapped.y = wa.y;
    snapped.height = wa.height;
  } else if (Math.abs(bounds.y - wa.y) <= EDGE_SNAP_THRESHOLD) {
    snapped.y = wa.y;
  }
  return snapped;
}

function saveWindowBounds() {
  if (!mainWindow || mainWindow.isDestroyed() || mainWindow.isMinimized()) return;
  writeWindowState(mainWindow.getBounds());
}

// After a move/resize settles, snap to the edge if appropriate and persist.
function settleWindow() {
  if (!mainWindow || mainWindow.isDestroyed() || mainWindow.isMinimized()) return;
  const current = mainWindow.getBounds();
  const snapped = snapBoundsToEdges(current);
  if (
    snapped.x !== current.x
    || snapped.y !== current.y
    || snapped.width !== current.width
    || snapped.height !== current.height
  ) {
    mainWindow.setBounds(snapped);
  }
  writeWindowState(mainWindow.getBounds());
}

function scheduleSaveWindowBounds() {
  if (saveBoundsTimer) clearTimeout(saveBoundsTimer);
  saveBoundsTimer = setTimeout(settleWindow, 220);
}

function writeRuntimeLog(message) {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  const safe = String(message).replace(/\\/g, '\\\\').replace(/`/g, '\\`');
  mainWindow.webContents.executeJavaScript(
    "console.log('%cWFI:', 'color: #51d6ff', `" + safe + "`);",
  ).catch(() => {});
}

function setLoadingStatus(message, isError) {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  const safe = String(message).replace(/\\/g, '\\\\').replace(/`/g, '\\`');
  mainWindow.webContents.executeJavaScript(`
    (() => {
      const node = document.getElementById('status');
      if (!node) return;
      node.textContent = \`${safe}\`;
      node.classList.toggle('error', ${isError ? 'true' : 'false'});
    })();
  `).catch(() => {});
}

function startServerWith(candidate, config) {
  return new Promise((resolve, reject) => {
    const args = ['-m', 'media_browser.server', '--config', config.configPath];
    const child = spawn(candidate, args, {
      cwd: config.projectRoot,
      env: pythonEnv(config),
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    let settled = false;
    let stdoutBuffer = '';
    let stderrBuffer = '';
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      child.kill();
      reject(new Error(`Timed out starting server with ${candidate}`));
    }, 15000);

    child.stdout.on('data', (chunk) => {
      stdoutBuffer += chunk.toString();
      const lines = stdoutBuffer.split(/\r?\n/);
      stdoutBuffer = lines.pop() || '';
      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const info = JSON.parse(line);
          if (!info.base_url || !info.token) continue;
          settled = true;
          clearTimeout(timer);
          serverProcess = child;
          resolve(Object.assign({ python: candidate }, info));
          return;
        } catch (_error) {
          writeRuntimeLog(line);
        }
      }
    });

    child.stderr.on('data', (chunk) => {
      stderrBuffer += chunk.toString();
      writeRuntimeLog(stderrBuffer.slice(-1000));
    });

    child.on('error', (error) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      reject(error);
    });

    child.on('exit', (code, signal) => {
      if (serverProcess === child) {
        serverProcess = null;
      }
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      reject(new Error(`Server exited before ready (${candidate}, code=${code}, signal=${signal}). ${stderrBuffer}`));
    });
  });
}

async function startServer() {
  if (serverInfo) return serverInfo;
  const config = runtimeConfig();
  let lastError = null;

  if (!fs.existsSync(config.projectRoot)) {
    throw new Error(`Project runtime not found: ${config.projectRoot}`);
  }

  for (const candidate of pythonCandidates(config)) {
    try {
      setLoadingStatus(`Starting local media service with ${candidate}...`, false);
      serverInfo = await startServerWith(candidate, config);
      return serverInfo;
    } catch (error) {
      lastError = error;
      writeRuntimeLog(`Python candidate failed: ${candidate}: ${error.message}`);
    }
  }

  throw lastError || new Error('No usable Python interpreter found.');
}

async function initResolveInterface() {
  if (resolveObj) return resolveObj;
  const initialized = await WorkflowIntegration.Initialize(PLUGIN_ID);
  if (!initialized) {
    throw new Error('Failed to initialize DaVinci Resolve Workflow Integration.');
  }
  resolveObj = await WorkflowIntegration.GetResolve();
  if (!resolveObj) {
    throw new Error('Failed to get DaVinci Resolve scripting object.');
  }
  return resolveObj;
}

async function getProjectManager() {
  if (projectManagerObj) return projectManagerObj;
  const resolve = await initResolveInterface();
  projectManagerObj = await resolve.GetProjectManager();
  if (!projectManagerObj) {
    throw new Error('No Project Manager is available.');
  }
  return projectManagerObj;
}

async function getProjectInfo() {
  const projectManager = await getProjectManager();
  const project = await projectManager.GetCurrentProject();
  if (!project) {
    return { name: '' };
  }

  let name = '';
  try {
    name = await project.GetName();
  } catch (_error) {
    name = '';
  }

  return { name: name || '' };
}

function normalizeClipList(clips) {
  if (!clips) return [];
  if (Array.isArray(clips)) return clips;
  if (typeof clips.length === 'number') {
    return Array.from(clips);
  }
  return [clips];
}

async function getFolderName(folder) {
  try {
    return await folder.GetName();
  } catch (_error) {
    return '';
  }
}

async function getOrCreateImportBin(mediaPool) {
  const rootFolder = await mediaPool.GetRootFolder();
  if (!rootFolder) return null;

  const subfolders = normalizeClipList(await rootFolder.GetSubFolderList());
  for (const folder of subfolders) {
    if (await getFolderName(folder) === IMPORT_BIN_NAME) {
      return folder;
    }
  }

  try {
    return await mediaPool.AddSubFolder(rootFolder, IMPORT_BIN_NAME);
  } catch (_error) {
    return null;
  }
}

async function selectImportBin(mediaPool) {
  const folder = await getOrCreateImportBin(mediaPool);
  if (!folder) return false;
  try {
    return await mediaPool.SetCurrentFolder(folder);
  } catch (_error) {
    return false;
  }
}

async function setClipMetadata(clip, metadata) {
  if (!clip || !metadata || typeof metadata !== 'object') return;
  try {
    const ok = await clip.SetMetadata(metadata);
    if (ok) return;
  } catch (_error) {
    // Some Resolve versions are stricter through WorkflowIntegration.node.
  }

  for (const [key, value] of Object.entries(metadata)) {
    try {
      await clip.SetMetadata(key, String(value));
    } catch (_error) {
      // Metadata support differs by clip type and Resolve version.
    }
  }
}

async function importMedia(_event, payload) {
  const paths = Array.isArray(payload && payload.paths) ? payload.paths.filter(Boolean) : [];
  if (!paths.length) {
    throw new Error('No downloaded media path was provided.');
  }

  const resolve = await initResolveInterface();
  await resolve.OpenPage('media');

  const projectManager = await getProjectManager();
  const project = await projectManager.GetCurrentProject();
  if (!project) {
    throw new Error('No current DaVinci Resolve project is open.');
  }

  const mediaPool = await project.GetMediaPool();
  if (!mediaPool) {
    throw new Error('Current project has no Media Pool.');
  }

  await selectImportBin(mediaPool);

  let clips = normalizeClipList(await mediaPool.ImportMedia(paths));
  if (!clips.length) {
    const mediaStorage = await resolve.GetMediaStorage();
    clips = normalizeClipList(await mediaStorage.AddItemListToMediaPool(paths));
  }
  if (!clips.length) {
    throw new Error('Resolve did not import the downloaded file. Check codec/path support.');
  }

  const metadata = payload.metadata || {};
  for (const clip of clips) {
    await setClipMetadata(clip, metadata);
  }

  try {
    await mediaPool.SetSelectedClip(clips[0]);
  } catch (_error) {
    // Selecting the imported item is a convenience only.
  }

  return {
    imported_count: clips.length,
    paths,
    resolve_available: true,
    bin_name: IMPORT_BIN_NAME,
    project_name: await getProjectInfo().then((info) => info.name).catch(() => ''),
  };
}

function registerHandlers() {
  ipcMain.handle('runtime:getInfo', () => serverInfo || {});
  ipcMain.handle('resolve:getProjectInfo', getProjectInfo);
  ipcMain.handle('resolve:importMedia', importMedia);
}

function createWindow() {
  const bounds = loadWindowBounds();
  mainWindow = new BrowserWindow({
    x: bounds.x,
    y: bounds.y,
    width: bounds.width,
    height: bounds.height,
    minWidth: MIN_WIDTH,
    minHeight: MIN_HEIGHT,
    backgroundColor: '#080a0f',
    title: 'DaVinci Online Media Browser',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  if (typeof mainWindow.setMenu === 'function') {
    mainWindow.setMenu(null);
  }

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:\/\//i.test(url)) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow' };
  });
  if (KEEP_ABOVE && typeof mainWindow.setAlwaysOnTop === 'function') {
    // 'floating' keeps it above Resolve but below system/screen-saver windows.
    mainWindow.setAlwaysOnTop(true, 'floating');
  }

  mainWindow.on('move', scheduleSaveWindowBounds);
  mainWindow.on('resize', scheduleSaveWindowBounds);
  mainWindow.on('close', () => {
    saveWindowBounds();
    app.quit();
  });

  mainWindow.loadFile('index.html');
  mainWindow.webContents.once('did-finish-load', async () => {
    try {
      const info = await startServer();
      setLoadingStatus('Loading media browser...', false);
      mainWindow.loadURL(`${info.base_url}/?token=${encodeURIComponent(info.token)}&mode=wfi`);
    } catch (error) {
      setLoadingStatus(`Could not start media browser:\n${error.message}`, true);
    }
  });
}

function stopServer() {
  if (!serverProcess) return;
  try {
    serverProcess.kill();
  } catch (_error) {
    // The process may already be gone.
  }
  serverProcess = null;
}

function cleanupResolveInterface() {
  try {
    WorkflowIntegration.CleanUp();
  } catch (_error) {
    // Resolve may already be quitting.
  }
  resolveObj = null;
  projectManagerObj = null;
}

app.whenReady().then(() => {
  registerHandlers();
  createWindow();
});

app.on('before-quit', () => {
  stopServer();
  cleanupResolveInterface();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
