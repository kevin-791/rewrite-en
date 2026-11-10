import pytest

from rewrite_en.config import load_config, write_default_config


def test_defaults_per_os(tmp_path):
    missing = tmp_path / "none.toml"
    assert load_config(missing, "win32").hotkey == "<ctrl>+<alt>+e"
    assert load_config(missing, "darwin").hotkey == "<ctrl>+<shift>+e"
    cfg = load_config(missing, "win32")
    assert cfg.model == "claude-haiku-5-5"
    assert cfg.max_chars == 6000
    assert cfg.timeout_seconds == 20


def test_toml_overrides(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text('hotkey = "<cmd>+<shift>+r"\nmodel = "claude-sonnet-5-5"\nmax_chars = 100\ntimeout_seconds = 5\nunknown = 1\n')
    cfg = load_config(p, "darwin")
    assert cfg.hotkey == "<cmd>+<shift>+r"
    assert cfg.model == "claude-sonnet-5-5"
    assert cfg.max_chars == 100
    assert cfg.timeout_seconds == 5.0


@pytest.mark.parametrize("line", ["max_chars = -1", 'max_chars = "x"', 'hotkey = ""', "sounds = 1"])
def test_invalid_values_rejected(tmp_path, line):
    p = tmp_path / "config.toml"
    p.write_text(line + "\n")
    with pytest.raises(ValueError):
        load_config(p, "win32")


def test_written_default_round_trips(tmp_path):
    p = write_default_config(tmp_path / "sub" / "config.toml")
    cfg = load_config(p)
    assert cfg.max_chars == 6000
    # Does not overwrite an existing file.
    p.write_text('model = "x"\n')
    write_default_config(p)
    assert p.read_text() == 'model = "x"\n'
