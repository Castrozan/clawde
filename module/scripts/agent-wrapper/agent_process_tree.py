import os
import signal
import subprocess


def collect_descendant_process_ids(parent_process_id: int) -> list[int]:
    result = subprocess.run(
        ["pgrep", "-P", str(parent_process_id)],
        capture_output=True,
        text=True,
    )
    descendant_process_ids: list[int] = []
    for line in result.stdout.split():
        child_process_id = int(line)
        descendant_process_ids.extend(collect_descendant_process_ids(child_process_id))
        descendant_process_ids.append(child_process_id)
    return descendant_process_ids


def terminate_process_tree(root_process_id: int) -> None:
    for process_id in collect_descendant_process_ids(root_process_id) + [
        root_process_id
    ]:
        try:
            os.kill(process_id, signal.SIGTERM)
        except ProcessLookupError:
            pass
