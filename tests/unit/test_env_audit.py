"""Chapter 30: pure logic, no network, tested against real fixture
files rather than mocked. Proves the exact real gap this chapter found
in every one of this book's three product repos: an undocumented
variable a bare `os.environ["X"]` reference actually reads.
"""

from triage_app.env_audit import documented_vars, find_env_vars, undocumented_vars


def test_find_env_vars_catches_both_bracket_and_get_forms(tmp_path):
    source = tmp_path / "example.py"
    source.write_text(
        'import os\n'
        'DATABASE_URL = os.environ["DATABASE_URL"]\n'
        'FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "default")\n'
    )
    assert find_env_vars([tmp_path]) == {"DATABASE_URL", "FRONTEND_ORIGIN"}


def test_documented_vars_reads_names_before_the_equals_sign(tmp_path):
    env_example = tmp_path / ".env.example"
    env_example.write_text("# a comment\nDATABASE_URL=\nGEMINI_API_KEY=some-placeholder\n")
    assert documented_vars(env_example) == {"DATABASE_URL", "GEMINI_API_KEY"}


def test_documented_vars_returns_empty_set_when_the_file_does_not_exist(tmp_path):
    assert documented_vars(tmp_path / "does-not-exist.example") == set()


def test_undocumented_vars_finds_the_real_gap_this_chapter_found(tmp_path):
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    (source_dir / "config.py").write_text(
        'import os\nKEY = os.environ["GEMINI_API_KEY"]\nURL = os.environ["DATABASE_URL"]\n'
    )
    env_example = tmp_path / ".env.example"
    env_example.write_text("DATABASE_URL=\n")

    assert undocumented_vars([source_dir], env_example) == {"GEMINI_API_KEY"}
