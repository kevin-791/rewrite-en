import pytest

from rewrite_en import hotkey_setup as hs
from rewrite_en.config import load_config


@pytest.mark.req("REQ-CLI-4")
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("<ctrl>+<shift>+e", "<ctrl>+<shift>+e"),
        ("<SHIFT>+<CTRL>+E", "<ctrl>+<shift>+e"),
        ("<cmd>+<alt>+<ctrl>+r", "<ctrl>+<alt>+<cmd>+r"),
        (" <ctrl> + <alt> + <f9> ", "<ctrl>+<alt>+<f9>"),
        ("<ctrl>+<space>", "<ctrl>+<space>"),
        ("<ctrl_l>+e", "<ctrl>+e"),
    ],
)
def test_normalise_valid(raw, expected):
    assert hs.normalise_hotkey(raw) == expected


@pytest.mark.req("REQ-CLI-4")
@pytest.mark.parametrize(
    "raw,reason",
    [
        ("e", "modifier"),
        ("<ctrl>+<shift>", "non-modifier"),
        ("<ctrl>+e+r", "exactly one"),
        ("<ctrl>+<ctrl>+e", "twice"),
        ("<ctrl>+<banana>", "unknown key"),
        ("<ctrl>++e", "empty"),
        ("", "empty"),
        ("ctrl+e", "unknown key"),
    ],
)
def test_normalise_invalid(raw, reason):
    with pytest.raises(hs.HotkeyError, match=reason):
        hs.normalise_hotkey(raw)


@pytest.mark.req("REQ-CLI-4")
def test_mac_option_warning():
    assert hs.warnings_for("<ctrl>+<alt>+e", "darwin")
    assert not hs.warnings_for("<ctrl>+<alt>+e", "win32")
    assert not hs.warnings_for("<ctrl>+<shift>+e", "darwin")


@pytest.mark.req("REQ-CLI-4")
def test_save_changes_only_hotkey_line(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text('# my comment\nhotkey = "<ctrl>+<alt>+e"   # old\nmodel = "claude-sonnet-5-5"\n')
    hs.save_hotkey("<cmd>+<shift>+r", p)
    assert p.read_text() == '# my comment\nhotkey = "<cmd>+<shift>+r"\nmodel = "claude-sonnet-5-5"\n'
    assert load_config(p).hotkey == "<cmd>+<shift>+r"


@pytest.mark.req("REQ-CLI-4")
def test_save_adds_line_when_missing(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text('model = "x"\n')
    hs.save_hotkey("<ctrl>+e", p)
    cfg = load_config(p)
    assert cfg.hotkey == "<ctrl>+e" and cfg.model == "x"


@pytest.mark.req("REQ-CLI-4")
def test_save_creates_default_file(tmp_path):
    p = tmp_path / "sub" / "config.toml"
    hs.save_hotkey("<ctrl>+e", p)
    cfg = load_config(p)
    assert cfg.hotkey == "<ctrl>+e" and cfg.max_chars == 6000


@pytest.mark.req("REQ-CLI-5")
@pytest.mark.parametrize(
    "events,expected",
    [
        ([("p", "ctrl"), ("p", "shift"), ("p", "e"), ("r", "e"), ("r", "shift"), ("r", "ctrl")], "<ctrl>+<shift>+e"),
        # release order doesn't matter; repeated key-down (auto-repeat) is ignored
        ([("p", "cmd"), ("p", "r"), ("p", "r"), ("r", "cmd"), ("r", "r")], "<cmd>+r"),
        # a lone tap before the combo is discarded once released
        ([("p", "x"), ("r", "x"), ("p", "alt"), ("p", "f9"), ("r", "f9"), ("r", "alt")], "<alt>+<f9>"),
    ],
)
def test_combo_from_events(events, expected):
    assert hs.combo_from_events(events) == expected


@pytest.mark.req("REQ-CLI-5")
def test_combo_from_events_incomplete():
    assert hs.combo_from_events([("p", "ctrl"), ("p", "e")]) is None
