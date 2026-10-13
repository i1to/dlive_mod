const { app, BrowserWindow, dialog, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const readline = require('readline');
const http = require('http');

let mainWindow = null;
let splashWindow = null;
let backendProcess = null;
let backendPort = 17820;
const backendLogs = [];

function pushBackendLog(line) {
  backendLogs.push(line);
  if (backendLogs.length > 200) backendLogs.shift();
}

/** 用户数据目录：打包后为 exe 同级目录，开发时为项目根目录 */
function resolveDataDir() {
  if (!app.isPackaged) return path.resolve(__dirname, '..', '..');
  // portable 模式下 exe 会解压到临时目录，PORTABLE_EXECUTABLE_DIR 才是用户双击的位置
  const candidates = [
    process.env.PORTABLE_EXECUTABLE_DIR,
    path.dirname(app.getPath('exe')),
  ].filter(Boolean);
  for (const dir of candidates) {
    try {
      fs.accessSync(dir, fs.constants.W_OK);
      return dir;
    } catch (_) {}
  }
  return app.getPath('userData');
}

/** 后端启动命令：打包后优先用内置 blive-vod-backend.exe，开发时用 python */
function resolveBackendCommand() {
  const projectRoot = path.resolve(__dirname, '..', '..');
  if (app.isPackaged) {
    const bundled = path.join(process.resourcesPath, 'backend', 'blive-vod-backend.exe');
    if (fs.existsSync(bundled)) {
      return { command: bundled, args: [], cwd: path.dirname(bundled) };
    }
  }
  const pythonCmd = process.env.BLIVE_PYTHON || 'python';
  return {
    command: pythonCmd,
    args: [path.join(projectRoot, 'desktop_backend.py')],
    cwd: projectRoot,
  };
}

function createSplash() {
  splashWindow = new BrowserWindow({
    width: 420,
    height: 220,
    frame: false,
    resizable: false,
    center: true,
    backgroundColor: '#0f1115',
    show: true,
    webPreferences: { contextIsolation: true },
  });
  splashWindow.loadFile(path.join(__dirname, '..', 'renderer', 'splash.html'));
  splashWindow.on('closed', () => {
    splashWindow = null;
  });
}

function closeSplash() {
  if (splashWindow && !splashWindow.isDestroyed()) splashWindow.close();
  splashWindow = null;
}

function createWindow(port) {
  mainWindow = new BrowserWindow({
    width: 1180,
    height: 760,
    minWidth: 980,
    minHeight: 640,
    backgroundColor: '#0f1115',
    title: 'B站直播点歌机',
    autoHideMenuBar: true,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, '..', 'renderer', 'index.html'), {
    query: { port: String(port) },
  });

  mainWindow.once('ready-to-show', () => {
    closeSplash();
    mainWindow.show();
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

/** 轮询后端健康检查，作为 stdout 握手的兜底方案 */
function probeHealth(port) {
  return new Promise((resolve) => {
    const req = http.get(
      { host: '127.0.0.1', port, path: '/api/health', timeout: 1500 },
      (res) => {
        res.resume();
        resolve(res.statusCode === 200);
      }
    );
    req.on('error', () => resolve(false));
    req.on('timeout', () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function waitHealth(port, attempts = 40) {
  for (let i = 0; i < attempts; i += 1) {
    if (await probeHealth(port)) return true;
    await new Promise((r) => setTimeout(r, 500));
  }
  return false;
}

function startBackend(dataDir) {
  return new Promise((resolve, reject) => {
    const { command, args, cwd } = resolveBackendCommand();
    backendProcess = spawn(command, [...args, '--host', '127.0.0.1', '--port', String(backendPort)], {
      cwd,
      env: {
        ...process.env,
        BLIVE_DATA_DIR: dataDir,
        PYTHONIOENCODING: 'utf-8',
        PYTHONUTF8: '1',
      },
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    });

    let settled = false;
    const timer = setTimeout(() => {
      if (!settled) {
        settled = true;
        reject(new Error('后端启动超时（30 秒）'));
      }
    }, 30000);

    const finish = (err, port) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (err) reject(err);
      else resolve(port);
    };

    const rlOut = readline.createInterface({ input: backendProcess.stdout });
    rlOut.on('line', (line) => {
      pushBackendLog(line);
      try {
        const data = JSON.parse(line.trim());
        if (data && data.type === 'ready' && data.port) {
          backendPort = data.port;
          finish(null, data.port);
        }
      } catch (_) {}
    });

    const rlErr = readline.createInterface({ input: backendProcess.stderr });
    rlErr.on('line', (line) => {
      pushBackendLog(line);
      console.error('[backend]', line);
    });

    backendProcess.on('error', (err) => finish(err));
    backendProcess.on('exit', (code) => {
      finish(new Error(`后端进程退出，代码 ${code}`));
    });
  });
}

function stopBackend() {
  if (!backendProcess) return;
  const pid = backendProcess.pid;
  backendProcess = null;
  try {
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', String(pid), '/f', '/t'], { windowsHide: true });
    } else {
      process.kill(pid, 'SIGTERM');
    }
  } catch (_) {}
}

app.whenReady().then(async () => {
  createSplash();
  const dataDir = resolveDataDir();
  try {
    const port = await startBackend(dataDir);
    createWindow(port);
  } catch (err) {
    // 握手失败时再尝试健康检查，兼容打包环境下 stdout 不可用的情况
    if (backendProcess && (await waitHealth(backendPort, 10))) {
      createWindow(backendPort);
      return;
    }
    closeSplash();
    const detail = [err && err.message, '', backendLogs.slice(-15).join('\n')]
      .filter(Boolean)
      .join('\n');
    dialog.showErrorBox('启动失败', `无法启动点歌机后端。\n\n${detail}`);
    stopBackend();
    app.exit(1);
    return;
  }
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow(backendPort);
  });
});

app.on('window-all-closed', () => {
  stopBackend();
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => stopBackend());
