const { app, BrowserWindow, Menu, shell } = require("electron");

const { startManagedServer } = require("./server_runtime");

let mainWindow = null;
let managedServer = null;
let isQuitting = false;

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function buildStatusPage(title, body, detail = "") {
  const html = `<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(title)}</title>
  <style>
    :root {
      color-scheme: light;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f2efe8;
      color: #23201a;
    }
    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background:
        radial-gradient(circle at top, rgba(150, 120, 80, 0.16), transparent 48%),
        linear-gradient(160deg, #f6f2ea, #e7ddd0);
    }
    main {
      width: min(760px, calc(100vw - 48px));
      padding: 32px;
      border-radius: 24px;
      background: rgba(255, 255, 255, 0.78);
      box-shadow: 0 20px 60px rgba(73, 54, 29, 0.18);
      border: 1px solid rgba(73, 54, 29, 0.12);
    }
    h1 {
      margin: 0 0 12px;
      font-size: 28px;
    }
    p {
      margin: 0;
      line-height: 1.6;
    }
    pre {
      margin: 20px 0 0;
      padding: 16px;
      overflow: auto;
      border-radius: 16px;
      background: #1f1d1a;
      color: #f7f2eb;
      font-size: 13px;
      line-height: 1.5;
      white-space: pre-wrap;
    }
  </style>
</head>
<body>
  <main>
    <h1>${escapeHtml(title)}</h1>
    <p>${escapeHtml(body)}</p>
    ${detail ? `<pre>${escapeHtml(detail)}</pre>` : ""}
  </main>
</body>
</html>`;

  return `data:text/html;charset=UTF-8,${encodeURIComponent(html)}`;
}

function installApplicationMenu() {
  const template = [
    {
      label: "App",
      submenu: [
        {
          label: "Intro",
          click: () => loadRoute("/intro"),
        },
        {
          label: "User UI",
          click: () => loadRoute("/app"),
        },
        {
          label: "Admin UI",
          click: () => loadRoute("/admin"),
        },
        {
          type: "separator",
        },
        {
          label: "Open In Browser",
          click: () => {
            if (managedServer?.entryUrl) {
              shell.openExternal(managedServer.entryUrl);
            }
          },
        },
        {
          type: "separator",
        },
        {
          role: "quit",
        },
      ],
    },
    {
      label: "View",
      submenu: [
        { role: "reload" },
        { role: "forcereload" },
        { role: "toggledevtools" },
        { type: "separator" },
        { role: "resetzoom" },
        { role: "zoomin" },
        { role: "zoomout" },
      ],
    },
  ];

  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

function createMainWindow() {
  const window = new BrowserWindow({
    width: 1440,
    height: 960,
    minWidth: 1100,
    minHeight: 760,
    show: false,
    backgroundColor: "#f2efe8",
    title: "doc_rag desktop PoC",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  window.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  window.once("ready-to-show", () => {
    window.show();
  });

  return window;
}

async function loadRoute(route) {
  if (!mainWindow || !managedServer?.entryUrl) {
    return;
  }
  const targetUrl = new URL(route, managedServer.entryUrl).toString();
  await mainWindow.loadURL(targetUrl);
}

async function bootstrap() {
  installApplicationMenu();
  mainWindow = createMainWindow();
  await mainWindow.loadURL(
    buildStatusPage(
      "doc_rag desktop PoC",
      "FastAPI 런타임을 확인하고 로컬 UI를 연결하는 중입니다.",
    ),
  );

  try {
    managedServer = await startManagedServer();
    await mainWindow.loadURL(managedServer.entryUrl);
  } catch (error) {
    const detail = error && error.stack ? error.stack : String(error);
    await mainWindow.loadURL(
      buildStatusPage(
        "doc_rag desktop PoC start failed",
        "Python 런타임, requirements 설치, 포트 충돌 여부를 확인하세요.",
        detail,
      ),
    );
  }
}

async function shutdownManagedServer() {
  if (managedServer?.started) {
    await managedServer.stop();
  }
}

app.on("before-quit", (event) => {
  if (isQuitting) {
    return;
  }

  if (managedServer?.started) {
    event.preventDefault();
    isQuitting = true;
    shutdownManagedServer()
      .catch(() => {})
      .finally(() => {
        app.quit();
      });
  }
});

app.on("window-all-closed", () => {
  app.quit();
});

app.whenReady().then(bootstrap);
