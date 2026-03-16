const fs = require("node:fs");
const http = require("node:http");
const https = require("node:https");
const path = require("node:path");
const { spawn } = require("node:child_process");

const {
  DEFAULT_HOST,
  DEFAULT_PORT,
  buildHealthUrl,
  isServerHealthy,
  repoRoot,
  resolvePythonCommand,
} = require("./server_runtime");

const REQUEST_TIMEOUT_MS = 2_000;
const OUTPUT_TAIL_LINES = 20;

function parseEnvFile(rootDir) {
  const envPath = path.join(rootDir, ".env");
  if (!fs.existsSync(envPath)) {
    return {};
  }

  const raw = fs.readFileSync(envPath, "utf-8");
  const values = {};
  for (const line of raw.split(/\r?\n/g)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }

    const equalsIndex = trimmed.indexOf("=");
    if (equalsIndex <= 0) {
      continue;
    }

    const key = trimmed.slice(0, equalsIndex).trim();
    let value = trimmed.slice(equalsIndex + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    values[key] = value;
  }

  return values;
}

function defaultLlmModel(provider) {
  if (provider === "openai") {
    return "gpt-4o-mini";
  }
  if (provider === "lmstudio") {
    return "local-model";
  }
  return "qwen3:4b";
}

function resolveConfiguredLlm(rootDir) {
  const envFile = parseEnvFile(rootDir);
  const provider = (process.env.LLM_PROVIDER || envFile.LLM_PROVIDER || "ollama").trim().toLowerCase();
  const model = (
    process.env.LLM_MODEL ||
    envFile.LLM_MODEL ||
    defaultLlmModel(provider)
  ).trim();

  if (provider === "openai") {
    return {
      provider,
      model,
      baseUrl: process.env.OPENAI_API_BASE || envFile.OPENAI_API_BASE || "",
      source: Object.keys(envFile).length ? ".env" : "defaults",
    };
  }

  if (provider === "lmstudio") {
    return {
      provider,
      model,
      baseUrl:
        process.env.LMSTUDIO_BASE_URL ||
        envFile.LMSTUDIO_BASE_URL ||
        "http://localhost:1234/v1",
      source: Object.keys(envFile).length ? ".env" : "defaults",
    };
  }

  return {
    provider: "ollama",
    model,
    baseUrl: process.env.OLLAMA_BASE_URL || envFile.OLLAMA_BASE_URL || "http://localhost:11434",
    source: Object.keys(envFile).length ? ".env" : "defaults",
  };
}

function trimOutput(text) {
  const lines = String(text || "")
    .split(/\r?\n/g)
    .map((line) => line.trimEnd())
    .filter(Boolean);
  if (!lines.length) {
    return "";
  }
  return lines.slice(-OUTPUT_TAIL_LINES).join("\n");
}

function runCommand(command, args, options = {}) {
  return new Promise((resolve) => {
    const child = spawn(command, args, {
      cwd: options.cwd,
      env: options.env,
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true,
    });

    const stdoutChunks = [];
    const stderrChunks = [];

    child.stdout.on("data", (chunk) => stdoutChunks.push(chunk));
    child.stderr.on("data", (chunk) => stderrChunks.push(chunk));
    child.on("error", (error) => {
      resolve({
        ok: false,
        code: null,
        stdout: "",
        stderr: error.message,
      });
    });
    child.on("close", (code) => {
      resolve({
        ok: code === 0,
        code,
        stdout: Buffer.concat(stdoutChunks).toString("utf-8"),
        stderr: Buffer.concat(stderrChunks).toString("utf-8"),
      });
    });
  });
}

function requestJson(url, timeoutMs = REQUEST_TIMEOUT_MS) {
  return new Promise((resolve, reject) => {
    const targetUrl = new URL(url);
    const client = targetUrl.protocol === "https:" ? https : http;
    const req = client.get(targetUrl, (response) => {
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

function buildCheck(label, status, message, options = {}) {
  return {
    label,
    message,
    status,
    blocking: Boolean(options.blocking),
    detail: options.detail || "",
  };
}

async function inspectDesktopEnvironment(options = {}) {
  const host = options.host || DEFAULT_HOST;
  const port = options.port || DEFAULT_PORT;
  const rootDir = options.repoRoot || repoRoot();
  const checks = [];
  const appEntryPath = path.join(rootDir, "app_api.py");

  if (fs.existsSync(appEntryPath)) {
    checks.push(buildCheck("Repo entry", "ok", `Found ${appEntryPath}`, { blocking: true }));
  } else {
    checks.push(
      buildCheck("Repo entry", "fail", `Missing ${appEntryPath}`, {
        blocking: true,
      }),
    );
  }

  let pythonCommand = null;
  try {
    pythonCommand = await resolvePythonCommand(rootDir);
    checks.push(buildCheck("Python runtime", "ok", `Using ${pythonCommand}`, { blocking: true }));
  } catch (error) {
    checks.push(
      buildCheck("Python runtime", "fail", error.message, {
        blocking: true,
      }),
    );
  }

  if (pythonCommand) {
    const importResult = await runCommand(
      pythonCommand,
      ["-c", "import app_api"],
      {
        cwd: rootDir,
        env: { ...process.env, PYTHONUNBUFFERED: "1" },
      },
    );
    checks.push(
      buildCheck(
        "Backend import",
        importResult.ok ? "ok" : "fail",
        importResult.ok
          ? "app_api import succeeded."
          : `app_api import failed (code=${importResult.code ?? "error"}).`,
        {
          blocking: true,
          detail: trimOutput(importResult.stderr || importResult.stdout),
        },
      ),
    );
  }

  const health = await isServerHealthy({ host, port });
  if (health.ok) {
    checks.push(
      buildCheck(
        "Existing server",
        "ok",
        `Server already responding at ${buildHealthUrl({ host, port })}.`,
      ),
    );
  } else {
    checks.push(
      buildCheck(
        "Existing server",
        "warn",
        `No server responding at ${buildHealthUrl({ host, port })} yet.`,
        {
          detail: health.error ? health.error.message : "",
        },
      ),
    );
  }

  const llm = resolveConfiguredLlm(rootDir);
  if (llm.provider === "ollama") {
    const tagsUrl = new URL("/api/tags", llm.baseUrl).toString();
    try {
      const tagsPayload = await requestJson(tagsUrl);
      const tagNames = Array.isArray(tagsPayload.models)
        ? tagsPayload.models.map((item) => String(item.name || "")).filter(Boolean)
        : [];
      const modelFound = tagNames.includes(llm.model);
      checks.push(
        buildCheck(
          "Ollama runtime",
          modelFound ? "ok" : "warn",
          modelFound
            ? `Ollama reachable and model ${llm.model} is available.`
            : `Ollama reachable at ${llm.baseUrl}, but model ${llm.model} was not found in local tags.`,
          {
            detail: tagNames.length ? tagNames.join(", ") : "No local tags reported.",
          },
        ),
      );
    } catch (error) {
      checks.push(
        buildCheck(
          "Ollama runtime",
          "warn",
          `Ollama is not reachable at ${llm.baseUrl}. Desktop app can still open, but default query path may fail.`,
          {
            detail: error.message,
          },
        ),
      );
    }
  } else {
    checks.push(
      buildCheck(
        "Default LLM provider",
        "ok",
        `Configured default provider: ${llm.provider}.`,
      ),
    );
  }

  const blockingFailures = checks.filter((item) => item.blocking && item.status === "fail").length;
  const warningCount = checks.filter((item) => item.status === "warn").length;

  return {
    ok: blockingFailures === 0,
    rootDir,
    pythonCommand,
    llm,
    checks,
    blockingFailures,
    warningCount,
    existingServer: health.ok ? health.payload : null,
  };
}

function formatPreflightReport(report) {
  const lines = [
    `root=${report.rootDir}`,
    `default_llm=${report.llm.provider} / ${report.llm.model}`,
  ];

  for (const check of report.checks) {
    lines.push(`[${check.status}] ${check.label}: ${check.message}`);
    if (check.detail) {
      lines.push(`  ${check.detail}`);
    }
  }

  lines.push(`blocking_failures=${report.blockingFailures} warnings=${report.warningCount}`);
  return lines.join("\n");
}

module.exports = {
  formatPreflightReport,
  inspectDesktopEnvironment,
};
