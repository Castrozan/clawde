import time


def emit_timestamped_log(agent_name: str, message: str) -> None:
    print(
        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Agent {agent_name} {message}",
        flush=True,
    )
