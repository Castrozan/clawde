#!/usr/bin/env bash
set -euo pipefail

readonly AGENT_WORKSPACE_PATH="${1:?usage: seed-memory-bridge <agent-workspace-absolute-path>}"
readonly CANONICAL_MEMORY_DIRECTORY="${AGENT_WORKSPACE_PATH}/memory"
readonly CANONICAL_MEMORY_INDEX_PATH="${CANONICAL_MEMORY_DIRECTORY}/MEMORY.md"

_encode_path_as_claude_project_name() {
	local absolute_path="$1"
	echo "${absolute_path//[\/.]/-}"
}

_seed_canonical_memory_directory() {
	mkdir -p "${CANONICAL_MEMORY_DIRECTORY}"
	if [ ! -f "${CANONICAL_MEMORY_INDEX_PATH}" ]; then
		cat >"${CANONICAL_MEMORY_INDEX_PATH}" <<'MEMORY_INDEX_HEADER'
# Memory index

One line per topic file. Loaded once per Claude process boot via the
harness auto-memory mechanism. Agents append through the memory-write
CLI; never edit by hand.

MEMORY_INDEX_HEADER
	fi
}

_resolve_harness_memory_directory() {
	local home_dir="${HOME}"
	local encoded_project_name
	encoded_project_name=$(_encode_path_as_claude_project_name "${AGENT_WORKSPACE_PATH}")
	echo "${home_dir}/.claude/projects/${encoded_project_name}/memory"
}

_bridge_harness_to_canonical_via_symlink() {
	local harness_memory_directory
	harness_memory_directory=$(_resolve_harness_memory_directory)
	local harness_project_directory
	harness_project_directory=$(dirname "${harness_memory_directory}")
	mkdir -p "${harness_project_directory}"

	if [ -L "${harness_memory_directory}" ]; then
		local current_link_target
		current_link_target=$(readlink "${harness_memory_directory}")
		if [ "${current_link_target}" = "${CANONICAL_MEMORY_DIRECTORY}" ]; then
			return 0
		fi
		rm "${harness_memory_directory}"
		ln -s "${CANONICAL_MEMORY_DIRECTORY}" "${harness_memory_directory}"
		return 0
	fi

	if [ ! -e "${harness_memory_directory}" ]; then
		ln -s "${CANONICAL_MEMORY_DIRECTORY}" "${harness_memory_directory}"
		return 0
	fi

	if [ -d "${harness_memory_directory}" ] && [ -z "$(command ls -A "${harness_memory_directory}")" ]; then
		rmdir "${harness_memory_directory}"
		ln -s "${CANONICAL_MEMORY_DIRECTORY}" "${harness_memory_directory}"
		return 0
	fi

	echo "[memory] harness dir ${harness_memory_directory} has content; not symlinking. manual migration required." >&2
}

main() {
	_seed_canonical_memory_directory
	_bridge_harness_to_canonical_via_symlink
}

main "$@"
