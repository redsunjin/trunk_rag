const { formatPreflightReport, inspectDesktopEnvironment } = require("../preflight");

async function main() {
  const report = await inspectDesktopEnvironment();
  console.log(formatPreflightReport(report));

  if (!report.ok) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  const detail = error && error.stack ? error.stack : String(error);
  console.error(`[electron-preflight] failed\n${detail}`);
  process.exitCode = 1;
});
