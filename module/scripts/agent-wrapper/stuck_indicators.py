def pane_poll_is_stuck_evidence(
    harness_runtime_profile,
    current_pane_content: str,
    previous_pane_content: str | None,
) -> bool:
    if harness_runtime_profile.pane_is_at_idle_prompt(current_pane_content):
        return False
    if harness_runtime_profile.pane_indicates_usage_limit_modal(current_pane_content):
        return True
    return (
        previous_pane_content is not None
        and current_pane_content == previous_pane_content
    )
