import pathlib
import sys

SCRIPTS_DIRECTORY = pathlib.Path(__file__).resolve().parent.parent
SHARED_HARNESS_DIRECTORY = SCRIPTS_DIRECTORY / "harness"

if str(SHARED_HARNESS_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SHARED_HARNESS_DIRECTORY))
