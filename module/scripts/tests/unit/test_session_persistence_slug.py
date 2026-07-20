import pathlib
import sys

sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper")
)

import session_persistence


def project_directory_name(workspace_directory):
    return session_persistence.claude_project_directory_for_workspace(
        workspace_directory
    ).name


def test_a_dot_in_the_workspace_path_becomes_a_dash(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))

    assert (
        project_directory_name("/Users/lucas.zanoni/.dotfiles")
        == "-Users-lucas-zanoni--dotfiles"
    )


def test_an_underscore_in_the_workspace_path_becomes_a_dash(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))

    assert (
        project_directory_name("/private/var/folders/tl/nypl9j_13d16k9m3m/T")
        == "-private-var-folders-tl-nypl9j-13d16k9m3m-T"
    )


def test_slashes_and_existing_dashes_are_preserved_as_dashes(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))

    assert (
        project_directory_name("/Users/someone/repo/ai-first-initiative")
        == "-Users-someone-repo-ai-first-initiative"
    )


def test_a_conversation_under_a_dotted_workspace_path_is_found(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    workspace_directory = "/Users/lucas.zanoni/repo/betha-pm"
    project_directory = (
        tmp_path / ".claude" / "projects" / "-Users-lucas-zanoni-repo-betha-pm"
    )
    project_directory.mkdir(parents=True)
    (project_directory / "session-one.jsonl").write_text("{}\n")

    assert session_persistence.session_conversation_exists(
        "session-one", workspace_directory
    )
