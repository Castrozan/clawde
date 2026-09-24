import json
import os
import sys
import tempfile
from pathlib import Path

from channel_turn.execution import run_one_turn

commands = json.loads(Path(sys.argv[1]).read_text())["harness_one_shot_turn_commands"]
with tempfile.TemporaryDirectory() as directory:
    for harness, command in commands.items():
        for reply in ("public answer", "", "(no reply)"):
            os.environ["FIXTURE_REPLY"] = reply
            os.environ["FIXTURE_FAILURE"] = "0"
            result = run_one_turn(
                command, directory, str(Path(directory) / harness), "hello"
            )
            assert result.succeeded, (harness, result)
            assert result.reply == ("" if reply == "(no reply)" else reply), (
                harness,
                result,
            )
        os.environ["FIXTURE_REPLY"] = "incomplete text"
        os.environ["FIXTURE_FAILURE"] = "1"
        result = run_one_turn(
            command, directory, str(Path(directory) / harness), "hello"
        )
        assert not result.succeeded, (harness, result)
        assert not result.reply, (harness, result)
        print(f"{harness}: reply, silence, placeholder and failure verified")
