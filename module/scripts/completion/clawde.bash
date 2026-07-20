_clawde_launch_config_directory() {
	printf '%s\n' "${HOME}/clawde/launch-config"
}

_clawde_deployed_agent_names() {
	local launch_config_directory launch_config_file
	launch_config_directory="$(_clawde_launch_config_directory)"
	[ -d "$launch_config_directory" ] || return 0
	for launch_config_file in "$launch_config_directory"/*.json; do
		[ -e "$launch_config_file" ] || continue
		basename "$launch_config_file" .json
	done
}

_clawde_on_demand_agent_names() {
	local launch_config_directory launch_config_file
	launch_config_directory="$(_clawde_launch_config_directory)"
	[ -d "$launch_config_directory" ] || return 0
	for launch_config_file in "$launch_config_directory"/*.json; do
		[ -e "$launch_config_file" ] || continue
		grep -qE '"on_demand" *: *true' "$launch_config_file" || continue
		basename "$launch_config_file" .json
	done
}

_clawde_agents_with_an_active_hours_gate() {
	local launch_config_directory launch_config_file
	launch_config_directory="$(_clawde_launch_config_directory)"
	[ -d "$launch_config_directory" ] || return 0
	for launch_config_file in "$launch_config_directory"/*.json; do
		[ -e "$launch_config_file" ] || continue
		grep -qE '"active_hours_start" *: *[0-9]' "$launch_config_file" || continue
		basename "$launch_config_file" .json
	done
}

_clawde() {
	local current_word subcommand candidate_words
	current_word="${COMP_WORDS[COMP_CWORD]}"
	subcommand="${COMP_WORDS[1]:-}"

	if [ "$COMP_CWORD" -eq 1 ]; then
		mapfile -t COMPREPLY < <(compgen -W "active list start stop" -- "$current_word")
		return 0
	fi

	case "$subcommand" in
	start | stop)
		candidate_words="$(_clawde_on_demand_agent_names)"
		;;
	active)
		candidate_words="$(_clawde_agents_with_an_active_hours_gate)
--clear"
		;;
	*)
		COMPREPLY=()
		return 0
		;;
	esac

	mapfile -t COMPREPLY < <(compgen -W "$candidate_words" -- "$current_word")
}

complete -F _clawde clawde
