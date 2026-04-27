import os
from app.api.settings import _write_env_atomic


def test_write_env_creates_file_when_missing(tmp_path):
    path = tmp_path / ".env"
    _write_env_atomic(str(path), {"FOO": "bar", "BAZ": "qux"})
    content = path.read_text()
    assert "FOO=bar" in content
    assert "BAZ=qux" in content


def test_write_env_preserves_comments_and_blank_lines(tmp_path):
    path = tmp_path / ".env"
    path.write_text("# top comment\nFOO=old\n\n# section\nBAR=keep\n")
    _write_env_atomic(str(path), {"FOO": "new"})
    content = path.read_text()
    assert "# top comment" in content
    assert "# section" in content
    assert "FOO=new" in content
    assert "FOO=old" not in content
    assert "BAR=keep" in content
    assert "\n\n" in content  # blank line preserved


def test_write_env_appends_new_keys(tmp_path):
    path = tmp_path / ".env"
    path.write_text("EXISTING=1\n")
    _write_env_atomic(str(path), {"EXISTING": "2", "NEW_KEY": "3"})
    content = path.read_text()
    assert "EXISTING=2" in content
    assert "NEW_KEY=3" in content


def test_write_env_atomic_no_partial_on_failure(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text("FOO=original\n")

    def boom(*a, **kw):
        raise RuntimeError("disk full")

    monkeypatch.setattr("app.api.settings.os.replace", boom)
    try:
        _write_env_atomic(str(path), {"FOO": "new"})
    except RuntimeError:
        pass
    # Original content must be preserved (atomicity)
    assert path.read_text() == "FOO=original\n"
    # No leftover .tmp files
    assert not any(p.name.startswith(".env.") and p.name.endswith(".tmp") for p in tmp_path.iterdir())
