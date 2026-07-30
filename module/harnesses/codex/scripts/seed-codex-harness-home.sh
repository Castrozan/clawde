#!/usr/bin/env bash

set -euo pipefail

readonly CODEX_HARNESS_HOME_PATH="${1:?usage: seed-codex-harness-home <codex-home> <user-auth-file> <newline-separated-skill-directories>}"
readonly USER_CODEX_AUTHENTICATION_FILE="${2:?usage: seed-codex-harness-home <codex-home> <user-auth-file> <newline-separated-skill-directories>}"
readonly NEWLINE_SEPARATED_SKILL_DIRECTORIES="${3:-}"

readonly HARNESS_AUTHENTICATION_LINK="${CODEX_HARNESS_HOME_PATH}/auth.json"
readonly HARNESS_SKILLS_DIRECTORY="${CODEX_HARNESS_HOME_PATH}/skills"

_link_user_authentication_into_harness_home() {
	if [ ! -f "${USER_CODEX_AUTHENTICATION_FILE}" ]; then
		echo "[codex-harness] ${USER_CODEX_AUTHENTICATION_FILE} is absent; agents on the codex harness cannot authenticate until 'codex login' has run for this user." >&2
		return 0
	fi
	ln -sfn "${USER_CODEX_AUTHENTICATION_FILE}" "${HARNESS_AUTHENTICATION_LINK}"
}

_project_one_skill_set_into_harness_skills() {
	local skill_set_directory="$1"
	local claude_layout_skills_directory="${skill_set_directory}/.claude/skills"
	if [ ! -d "${claude_layout_skills_directory}" ]; then
		return 0
	fi
	local skill_directory
	for skill_directory in "${claude_layout_skills_directory}"/*; do
		[ -e "${skill_directory}" ] || continue
		ln -sfn "${skill_directory}" "${HARNESS_SKILLS_DIRECTORY}/$(basename "${skill_directory}")"
	done
}

_remove_previously_projected_skills() {
	[ -d "${HARNESS_SKILLS_DIRECTORY}" ] || return 0
	local existing_entry
	for existing_entry in "${HARNESS_SKILLS_DIRECTORY}"/*; do
		if [ -L "${existing_entry}" ]; then
			rm -f "${existing_entry}"
		fi
	done
}

_project_all_skill_sets_into_harness_skills() {
	mkdir -p "${HARNESS_SKILLS_DIRECTORY}"
	_remove_previously_projected_skills
	[ -n "${NEWLINE_SEPARATED_SKILL_DIRECTORIES}" ] || return 0
	local skill_set_directory
	while IFS= read -r skill_set_directory; do
		[ -n "${skill_set_directory}" ] || continue
		_project_one_skill_set_into_harness_skills "${skill_set_directory}"
	done <<<"${NEWLINE_SEPARATED_SKILL_DIRECTORIES}"
}

main() {
	mkdir -p "${CODEX_HARNESS_HOME_PATH}"
	_link_user_authentication_into_harness_home
	_project_all_skill_sets_into_harness_skills
}

main "$@"
