const { app, BrowserWindow } = require('electron');
const { spawn } = require('child_process');
const http = require('http');
const path = require('path');

let serverProcess = null;
let mainWindow = null;

const SERVER_URL = 'http://localhost:8765';
const PROJECT_ROOT = path.join(__dirname, '..', '..');

function waitForServer(url, timeout = 30000) {
    return new Promise((resolve, reject) => {
        const startTime = Date.now();

        function check() {
            http.get(url, (res) => {
                if (res.statusCode === 200) {
                    resolve();
                } else {
                    retry();
                }
            }).on('error', retry);
        }

        function retry() {
            if (Date.now() - startTime > timeout) {
                reject(new Error('Server start timeout'));
            } else {
                setTimeout(check, 500);
            }
        }

        check();
    });
}

function startServer() {
    console.log('Starting web server...');
    serverProcess = spawn('uv', ['run', 'lsimons-agent-web'], {
        cwd: PROJECT_ROOT,
        stdio: ['ignore', 'pipe', 'pipe']
    });

    serverProcess.stdout.on('data', (data) => {
        console.log(`server: ${data}`);
    });

    serverProcess.stderr.on('data', (data) => {
        console.error(`server error: ${data}`);
    });

    serverProcess.on('close', (code) => {
        console.log(`Server exited with code ${code}`);
        serverProcess = null;
    });

    return waitForServer(SERVER_URL);
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 900,
        height: 700,
        title: 'lsimons-agent',
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true
        }
    });

    mainWindow.loadURL(SERVER_URL);

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

app.whenReady().then(async () => {
    try {
        await startServer();
        createWindow();
    } catch (error) {
        console.error('Failed to start:', error);
        app.quit();
    }
});

app.on('window-all-closed', () => {
    app.quit();
});

app.on('quit', () => {
    if (serverProcess) {
        console.log('Stopping web server...');
        serverProcess.kill();
    }
});
