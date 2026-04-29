from __future__ import annotations

import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
COMPANION_DIR = ROOT_DIR / "browser_companion"
MANIFEST_PATH = COMPANION_DIR / "manifest.json"

EXPECTED_PERMISSIONS = {"sidePanel", "storage", "activeTab", "scripting"}
EXPECTED_HOST_PERMISSIONS = {"http://127.0.0.1/*", "http://localhost/*"}
DISALLOWED_HOST_PERMISSIONS = {"http://*/*", "https://*/*", "<all_urls>"}
REQUIRED_FILES = {
    "background.js",
    "sidepanel.html",
    "sidepanel.css",
    "sidepanel.js",
}


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("manifest_version") != 3:
        raise SystemExit("manifest_version must be 3")
    permissions = set(manifest.get("permissions", []))
    if permissions != EXPECTED_PERMISSIONS:
        raise SystemExit(f"unexpected permissions: {sorted(permissions)}")
    host_permissions = set(manifest.get("host_permissions", []))
    if host_permissions != EXPECTED_HOST_PERMISSIONS:
        raise SystemExit(f"unexpected host_permissions: {sorted(host_permissions)}")
    if host_permissions.intersection(DISALLOWED_HOST_PERMISSIONS):
        raise SystemExit("broad host permission is not allowed")
    side_panel = manifest.get("side_panel", {})
    if side_panel.get("default_path") != "sidepanel.html":
        raise SystemExit("side_panel.default_path must be sidepanel.html")
    background = manifest.get("background", {})
    if background.get("service_worker") != "background.js":
        raise SystemExit("background.service_worker must be background.js")
    missing = sorted(name for name in REQUIRED_FILES if not (COMPANION_DIR / name).exists())
    if missing:
        raise SystemExit(f"missing companion files: {', '.join(missing)}")
    print("browser companion manifest ok")


if __name__ == "__main__":
    main()
