const { startManagedServer } = require("../server_runtime");

async function main() {
  const managedServer = await startManagedServer();
  const mode = managedServer.started ? "spawned" : "attached";
  const vectors = managedServer.health?.vectors ?? "unknown";
  const chunkingMode = managedServer.health?.chunking_mode ?? "unknown";

  console.log(
    `[electron-smoke] ready mode=${mode} url=${managedServer.entryUrl} vectors=${vectors} chunking=${chunkingMode}`,
  );

  await managedServer.stop();
}

main().catch((error) => {
  const detail = error && error.stack ? error.stack : String(error);
  console.error(`[electron-smoke] failed\n${detail}`);
  process.exitCode = 1;
});
