import pytest

from rewrite_en import cli
from rewrite_en.claude_client import ClaudeRewriter, RewriteError


@pytest.mark.req("REQ-CLI-1")
def test_subcommands():
    parser = cli.build_parser()
    sub = next(a for a in parser._actions if a.dest == "command")
    assert set(sub.choices) == {"run", "set-key", "test", "config", "install-autostart", "uninstall-autostart"}


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
