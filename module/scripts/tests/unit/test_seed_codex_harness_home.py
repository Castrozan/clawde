import pathlib
import subprocess

SEED_SCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parents[3]
    / "harnesses"
    / "codex"
    / "scripts"
    / "seed-codex-harness-home.sh"
)


def build_skill_set_directory(root, skill_names):
    skills_directory = root / ".claude" / "skills"
    for skill_name in skill_names:
        skill_directory = skills_directory / skill_name
        skill_directory.mkdir(parents=True)
        (skill_directory / "SKILL.md").write_text(f"---\nname: {skill_name}\n---\n")
    return root


def run_seed(harness_home, skill_set_directories):
    return subprocess.run(
        [
            "bash",
            str(SEED_SCRIPT_PATH),
            str(harness_home),
            str(harness_home / "absent-auth.json"),
            "\n".join(str(directory) for directory in skill_set_directories),
        ],
        capture_output=True,
        text=True,
        check=True,
    )


def test_projects_declared_skills_into_the_harness_skills_directory(tmp_path):
    harness_home = tmp_path / "harness-home"
    skill_set = build_skill_set_directory(tmp_path / "set", ["alpha", "beta"])

    run_seed(harness_home, [skill_set])

    assert sorted(entry.name for entry in (harness_home / "skills").iterdir()) == [
        "alpha",
        "beta",
    ]


def test_drops_a_skill_no_longer_declared_by_the_agent(tmp_path):
    harness_home = tmp_path / "harness-home"
    wide_set = build_skill_set_directory(tmp_path / "wide", ["alpha", "dropped"])
    run_seed(harness_home, [wide_set])

    narrow_set = build_skill_set_directory(tmp_path / "narrow", ["alpha"])
    run_seed(harness_home, [narrow_set])

    assert [entry.name for entry in (harness_home / "skills").iterdir()] == ["alpha"]


def test_keeps_a_skill_installed_into_the_harness_home_by_hand(tmp_path):
    harness_home = tmp_path / "harness-home"
    skill_set = build_skill_set_directory(tmp_path / "set", ["alpha"])
    run_seed(harness_home, [skill_set])
    (harness_home / "skills" / "hand-installed").mkdir()

    run_seed(harness_home, [skill_set])

    assert sorted(entry.name for entry in (harness_home / "skills").iterdir()) == [
        "alpha",
        "hand-installed",
    ]
