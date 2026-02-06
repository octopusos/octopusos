#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_DIR="${ROOT}/apps/desktop-client"
CHANNEL="${OCTOPUSOS_CHANNEL:-stable}"
VERSION_FILE="${ROOT}/VERSION"
VERSION="0.0.0"
if [[ -f "${VERSION_FILE}" ]]; then
  VERSION="$(tr -d '\n' < "${VERSION_FILE}")"
fi

echo "octopusos_version=${VERSION}"
echo "channel=${CHANNEL}"

"${APP_DIR}/runtime/build-runtime.sh"

cd "${APP_DIR}"
if command -v pnpm >/dev/null 2>&1; then
  pnpm exec tauri build
elif command -v npx >/dev/null 2>&1; then
  npx tauri build
else
  echo "[desktop] neither pnpm nor npx found for tauri build" >&2
  exit 1
fi

OUT_DIR="${ROOT}/publish/artifacts/${VERSION}/macos"
mkdir -p "${OUT_DIR}"

DMG_SRC="$(find "${APP_DIR}/src-tauri/target/release/bundle/dmg" -name '*.dmg' -print -quit || true)"
if [[ -z "${DMG_SRC}" ]]; then
  echo "[desktop] dmg artifact not found" >&2
  exit 1
fi

TARGET_NAME="octopusos-desktop-${VERSION}-macos-arm64-${CHANNEL}.dmg"
cp "${DMG_SRC}" "${OUT_DIR}/${TARGET_NAME}"

echo "desktop_artifact=${OUT_DIR}/${TARGET_NAME}"
echo "[desktop] codesign/notarize hooks TODO"
