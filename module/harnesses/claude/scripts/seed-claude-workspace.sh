#!/usr/bin/env bash

set -euo pipefail

readonly AGENT_WORKSPACE_PATH="${1:?usage: seed-claude-workspace <workspace> <claude-binary>}"
readonly CLAUDE_BINARY="${2:?usage: seed-claude-workspace <workspace> <claude-binary>}"
readonly FALLBACK_ONBOARDING_VERSION="2.1.100"

mkdir -p "${AGENT_WORKSPACE_PATH}"

if [ ! -f "${AGENT_WORKSPACE_PATH}/HEARTBEAT.md" ]; then
	printf '# Heartbeat\n\nNo active work.\n' >"${AGENT_WORKSPACE_PATH}/HEARTBEAT.md"
fi

installed_claude_version="$("${CLAUDE_BINARY}" --version 2>/dev/null | head -1 | grep -oE '[0-9.]+' | head -1 || echo "${FALLBACK_ONBOARDING_VERSION}")"

if [ ! -f "${AGENT_WORKSPACE_PATH}/.claude.json" ]; then
	printf '{"hasCompletedOnboarding":true,"numStartups":1,"installMethod":"native","lastOnboardingVersion":"%s"}\n' \
		"${installed_claude_version}" >"${AGENT_WORKSPACE_PATH}/.claude.json"
fi
