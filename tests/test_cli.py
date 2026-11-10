import pytest

from rewrite_en import cli
from rewrite_en.claude_client import ClaudeRewriter, RewriteError


@pytest.mark.req("REQ-CLI-1")
def test_subcommands():
    parser = cli.build_parser()
    sub = next(a for a in parser._actions if a.dest == "command")
    assert set(sub.choices) == {"run", "set-key", "set-hotkey", "test", "config", "install-autostart", "uninstall-autostart"}


@pytest.fixture
def no_logging(monkeypatch):
    monkeypatch.setattr(cli, "_setup_logging", lambda verbose: None)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setattr("rewrite_en.keystore.get_api_key", lambda: "sk-test")


@pytest.mark.req("REQ-CLI-2")
def test_test_command_prints_rewrite(no_logging, monkeypatch, capsys):
    monkeypatch.setattr(ClaudeRewriter, "rewrite", lambda self, text: f"EN({text})")
    assert cli.main(["test", "xin chào"]) == 0
    assert capsys.readouterr().out.strip() == "EN(xin chào)"


@pytest.mark.req("REQ-CLI-2")
def test_test_command_reports_error_code(no_logging, monkeypatch, capsys):
    def fail(self, text):
        raise RewriteError("auth", "API key was rejected (401)")

    monkeypatch.setattr(ClaudeRewriter, "rewrite", fail)
    assert cli.main(["test", "xin chào"]) == 1
    assert "auth" in capsys.readouterr().err


@pytest.mark.req("REQ-CLI-3")
@pytest.mark.parametrize(
    "argv,verbose",
    [
        (["run"], False),
        (["-v", "run"], True),
        (["run", "-v"], True),
        (["--verbose", "test", "x"], True),
        (["test", "x", "--verbose"], True),
    ],
)
def test_verbose_before_or_after_subcommand(argv, verbose):
    assert cli.build_parser().parse_args(argv).verbose is verbose


@pytest.mark.req("REQ-CLI-4")
def test_set_hotkey_saves_and_rejects(no_logging, monkeypatch, tmp_path, capsys):
    p = tmp_path / "config.toml"
    monkeypatch.setattr("rewrite_en.hotkey_setup.config_path", lambda: p)
    monkeypatch.setattr("rewrite_en.autostart.restart_if_installed", lambda: None)
    assert cli.main(["set-hotkey", "<SHIFT>+<ctrl>+r"]) == 0
    assert '"<ctrl>+<shift>+r"' in p.read_text()
    out = capsys.readouterr().out
    assert "<ctrl>+<shift>+r" in out and "Restart rewrite-en" in out
    before = p.read_text()
    assert cli.main(["set-hotkey", "r"]) == 1
    assert p.read_text() == before
    assert "modifier" in capsys.readouterr().err


@pytest.mark.req("REQ-CLI-6")
def test_set_hotkey_restarts_launch_agent(no_logging, monkeypatch, tmp_path, capsys):
    p = tmp_path / "config.toml"
    monkeypatch.setattr("rewrite_en.hotkey_setup.config_path", lambda: p)
    monkeypatch.setattr("rewrite_en.autostart.restart_if_installed", lambda: "Restarted the background rewrite-en.")
    assert cli.main(["set-hotkey", "<cmd>+e"]) == 0
    out = capsys.readouterr().out
    assert "Restarted the background rewrite-en." in out and "Restart rewrite-en" not in out


@pytest.mark.req("REQ-CLI-6")
def test_restart_if_installed(monkeypatch, tmp_path):
    from rewrite_en import autostart

    calls = []
    monkeypatch.setattr(autostart, "_launchctl", lambda *a: calls.append(a) or type("R", (), {"returncode": 0, "stderr": ""})())
    monkeypatch.setattr(autostart, "_mac_plist", lambda: tmp_path / "com.rewrite-en.plist")
    monkeypatch.setattr(autostart.os, "getuid", lambda: 501, raising=False)

    monkeypatch.setattr(autostart.sys, "platform", "win32")
    assert autostart.restart_if_installed() is None
    monkeypatch.setattr(autostart.sys, "platform", "darwin")
    assert autostart.restart_if_installed() is None  # plist not installed
    (tmp_path / "com.rewrite-en.plist").write_text("x")
    assert autostart.restart_if_installed()
    assert calls == [("kickstart", "-k", "gui/501/com.rewrite-en")]
