#!/usr/bin/env bash

set -euo pipefail

if [ ! -d "$MARKETPLACE_DIR/.git" ]; then
	exit 0
fi

cd "$MARKETPLACE_DIR"
"$GIT_BIN" pull --ff-only origin main 2>/dev/null || true
