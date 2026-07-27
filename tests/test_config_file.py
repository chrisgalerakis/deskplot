"""deskplot.toml discovery, precedence, and failure behavior."""

import pytest

import deskplot
import deskplot.config as config_mod


@pytest.fixture
def file_discovery(monkeypatch, tmp_path):
    """Re-arm file loading inside an isolated cwd with no user config dir."""
    monkeypatch.setattr(config_mod, "_file_config_loaded", False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(config_mod.CONFIG_PATH_ENV_VAR, raising=False)
    monkeypatch.setattr(
        config_mod, "_user_config_dir", lambda: tmp_path / "user-config"
    )
    return tmp_path


def _write_toml(path, text):
    path.write_text(text, encoding="utf-8")


def test_no_file_keeps_defaults(file_discovery):
    cfg = deskplot.get_config()
    assert cfg.brand == "deskplot"
    assert cfg.source == ""


def test_cwd_file_is_discovered(file_discovery):
    _write_toml(
        file_discovery / "deskplot.toml",
        'brand = "FILEBRAND"\nsource = "File Research"\nauto_source = true\n',
    )
    cfg = deskplot.get_config()
    assert cfg.brand == "FILEBRAND"
    assert cfg.source == "File Research"
    assert cfg.auto_source is True


def test_user_config_dir_is_fallback(file_discovery):
    user_dir = file_discovery / "user-config"
    user_dir.mkdir()
    _write_toml(user_dir / "deskplot.toml", 'brand = "USERDIR"\n')
    assert deskplot.get_config().brand == "USERDIR"


def test_cwd_wins_over_user_config_dir(file_discovery):
    user_dir = file_discovery / "user-config"
    user_dir.mkdir()
    _write_toml(user_dir / "deskplot.toml", 'brand = "USERDIR"\n')
    _write_toml(file_discovery / "deskplot.toml", 'brand = "CWD"\n')
    assert deskplot.get_config().brand == "CWD"


def test_env_var_wins_over_cwd(file_discovery, monkeypatch):
    _write_toml(file_discovery / "deskplot.toml", 'brand = "CWD"\n')
    env_file = file_discovery / "elsewhere.toml"
    _write_toml(env_file, 'brand = "ENV"\n')
    monkeypatch.setenv(config_mod.CONFIG_PATH_ENV_VAR, str(env_file))
    assert deskplot.get_config().brand == "ENV"


def test_env_var_to_missing_file_warns(file_discovery, monkeypatch):
    monkeypatch.setenv(
        config_mod.CONFIG_PATH_ENV_VAR, str(file_discovery / "missing.toml")
    )
    with pytest.warns(UserWarning, match="does not exist"):
        cfg = deskplot.get_config()
    assert cfg.brand == "deskplot"


def test_configure_overrides_file(file_discovery):
    _write_toml(
        file_discovery / "deskplot.toml", 'brand = "FILE"\nsource = "File Src"\n'
    )
    cfg = deskplot.configure(brand="RUNTIME")
    assert cfg.brand == "RUNTIME"  # configure() beats the file...
    assert cfg.source == "File Src"  # ...but untouched file values stick


def test_unknown_key_warns_and_is_ignored(file_discovery):
    _write_toml(
        file_discovery / "deskplot.toml", 'brand = "OK"\nnot_a_field = 1\n'
    )
    with pytest.warns(UserWarning, match="unknown option 'not_a_field'"):
        cfg = deskplot.get_config()
    assert cfg.brand == "OK"
    assert not hasattr(cfg, "not_a_field")


def test_bad_toml_warns_and_keeps_defaults(file_discovery):
    _write_toml(file_discovery / "deskplot.toml", "brand = [unclosed\n")
    with pytest.warns(UserWarning, match="could not read"):
        cfg = deskplot.get_config()
    assert cfg.brand == "deskplot"


def test_file_is_loaded_only_once(file_discovery):
    toml = file_discovery / "deskplot.toml"
    _write_toml(toml, 'brand = "FIRST"\n')
    assert deskplot.get_config().brand == "FIRST"
    _write_toml(toml, 'brand = "SECOND"\n')
    assert deskplot.get_config().brand == "FIRST"
