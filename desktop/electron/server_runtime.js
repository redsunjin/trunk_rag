const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const { spawn } = require("node:child_process");

const DEFAULT_HOST = process.env.DOC_RAG_DESKTOP_HOST || "127.0.0.1";
const DEFAULT_PORT = Number(process.env.DOC_RAG_DESKTOP_PORT || "8000");
const DEFAULT_STARTUP_TIMEOUT_MS = 45_000;
const HEALTH_REQUEST_TIMEOUT_MS = 2_000;
const POLL_INTERVAL_MS = 500;
const RECENT_LOG_LIMIT = 80;

function repoRoot() {
  return path.resolve(__dirname, "..", "..");
}

function buildEntryUrl(options = {}) {
  const host = options.host || DEFAULT_HOST;
  const port = options.port || DEFAULT_PORT;
  const route = options.route || "/intro";
  return `http://${host}:${port}${route}`;
}

function buildHealthUrl(options = {}) {
  const host = options.host || DEFAULT_HOST;
  const port = options.port || DEFAULT_PORT;
  return `http://${host}:${port}/health`;
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function appendRecentLogs(logBuffer, chunk) {
  const lines = String(chunk)
    .split(/\r?\n/g)
    .map((line) => line.trim())
    .filter(Boolean);
  if (!lines.length) {
    return;
  }

  logBuffer.push(...lines);
  if (logBuffer.length > RECENT_LOG_LIMIT) {
    logBuffer.splice(0, logBuffer.length - RECENT_LOG_LIMIT);
  }
}

function formatRecentLogs(logBuffer) {
  if (!logBuffer.length) {
    return "";
  }
  return `\nRecent logs:\n${logBuffer.join("\n")}`;
}

function requestJson(url, timeoutMs = HEALTH_REQUEST_TIMEOUT_MS) {
  return new Promise((resolve, reject) => {
    const req = http.get(url, (response) => {
      const chunks = [];
      response.on("data", (chunk) => chunks.push(chunk));
      response.on("end", () => {
        const raw = Buffer.concat(chunks).toString("utf-8");
        if (response.statusCode !== 200) {
          reject(new Error(`HTTP ${response.statusCode}: ${raw}`));
          return;
        }

        try {
          resolve(JSON.parse(raw));
        } catch (error) {
          reject(new Error(`Invalid JSON from ${url}: ${error.message}`));
        }
      });
    });

    req.setTimeout(timeoutMs, () => {
      req.destroy(new Error(`Timed out after ${timeoutMs}ms`));
    });
    req.on("error", reject);
  });
}

async function isServerHealthy(options = {}) {
  try {
    const payload = await requestJson(buildHealthUrl(options));
    return { ok: true, payload };
  } catch (error) {
    return { ok: false, error };
  }
}

function isExecutablePath(command) {
  return path.isAbsolute(command) && fs.existsSync(command);
}

function canRunCommand(command) {
  return new Promise((resolve) => {
    const child = spawn(command, ["--version"], {
      stdio: "ignore",
      windowsHide: true,
    });
    child.on("error", () => resolve(false));
    child.on("exit", (code) => resolve(code === 0));
  });
}

async function resolvePythonCommand(rootDir = repoRoot()) {
  const candidates = [];
  if (process.platform === "win32") {
    candidates.push(path.join(rootDir, ".venv", "Scripts", "python.exe"));
  } else {
    candidates.push(path.join(rootDir, ".venv", "bin", "python"));
  }
  candidates.push("python3", "python");

  for (const candidate of candidates) {
    if (isExecutablePath(candidate)) {
      return candidate;
    }
    if (!path.isAbsolute(candidate) && (await canRunCommand(candidate))) {
      return candidate;
    }
  }

  throw new Error(
    "Python runtime not found. Create .venv or install python3/python before launching the desktop wrapper.",
  );
}

function waitForExit(child, timeoutMs) {
  return new Promise((resolve) => {
    if (!child || child.exitCode !== null) {
      resolve(true);
      return;
    }

    const timer = setTimeout(() => {
      cleanup();
      resolve(false);
    }, timeoutMs);

    function cleanup() {
      clearTimeout(timer);
      child.removeListener("exit", onExit);
      child.removeListener("close", onClose);
    }

    function onExit() {
      cleanup();
      resolve(true);
    }

    function onClose() {
      cleanup();
      resolve(true);
    }

    child.once("exit", onExit);
    child.once("close", onClose);
  });
}

async function stopManagedServer(child) {
  if (!child || child.exitCode !== null) {
    return;
  }

  child.kill("SIGTERM");
  const exited = await waitForExit(child, 3_000);
  if (!exited && child.exitCode === null) {
    child.kill("SIGKILL");
    await waitForExit(child, 1_000);
  }
}

async function waitForHealthy(options) {
  const deadline = Date.now() + options.timeoutMs;
  let lastError = null;

  while (Date.now() < deadline) {
    if (options.state.spawnError) {
      throw new Error(
        `Failed to spawn managed server: ${options.state.spawnError.message}${formatRecentLogs(options.recentLogs)}`,
      );
    }

    if (options.child && options.child.exitCode !== null) {
      throw new Error(
        `Managed server exited before /health was ready (code=${options.child.exitCode}).${formatRecentLogs(options.recentLogs)}`,
      );
    }

    const health = await isServerHealthy({
      host: options.host,
      port: options.port,
    });
    if (health.ok) {
      return health.payload;
    }

    lastError = health.error;
    await wait(POLL_INTERVAL_MS);
  }

  const lastErrorSuffix = lastError ? ` Last health error: ${lastError.message}` : "";
  throw new Error(
    `Timed out waiting for /health after ${options.timeoutMs}ms.${lastErrorSuffix}${formatRecentLogs(options.recentLogs)}`,
  );
}

async function startManagedServer(options = {}) {
  const host = options.host || DEFAULT_HOST;
  const port = options.port || DEFAULT_PORT;
  const route = options.route || "/intro";
  const rootDir = options.repoRoot || repoRoot();
  const startupTimeoutMs = options.startupTimeoutMs || DEFAULT_STARTUP_TIMEOUT_MS;

  const existing = await isServerHealthy({ host, port });
  if (existing.ok) {
    return {
      attached: true,
      started: false,
      entryUrl: buildEntryUrl({ host, port, route }),
      health: existing.payload,
      recentLogs: [],
      stop: async () => {},
    };
  }

  const pythonCommand = await resolvePythonCommand(rootDir);
  const recentLogs = [];
  const state = { spawnError: null };
  const child = spawn(pythonCommand, ["app_api.py"], {
    cwd: rootDir,
    env: {
      ...process.env,
      DOC_RAG_DESKTOP_WRAPPER: "electron",
      PYTHONUNBUFFERED: "1",
    },
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true,
  });

  child.stdout.on("data", (chunk) => appendRecentLogs(recentLogs, chunk));
  child.stderr.on("data", (chunk) => appendRecentLogs(recentLogs, chunk));
  child.on("error", (error) => {
    state.spawnError = error;
    appendRecentLogs(recentLogs, `[spawn-error] ${error.message}`);
  });

  const health = await waitForHealthy({
    child,
    host,
    port,
    recentLogs,
    state,
    timeoutMs: startupTimeoutMs,
  });

  return {
    attached: false,
    started: true,
    entryUrl: buildEntryUrl({ host, port, route }),
    health,
    process: child,
    pythonCommand,
    recentLogs,
    stop: async () => stopManagedServer(child),
  };
}

module.exports = {
  DEFAULT_HOST,
  DEFAULT_PORT,
  DEFAULT_STARTUP_TIMEOUT_MS,
  buildEntryUrl,
  buildHealthUrl,
  repoRoot,
  resolvePythonCommand,
  isServerHealthy,
  startManagedServer,
  stopManagedServer,
};
