"""Command line: run, set-key, test, config, install-autostart, uninstall-autostart."""

from __future__ import annotations

import argparse
import getpass
import logging
import sys
from logging.handlers import RotatingFileHandler

from rewrite_en import __version__
from rewrite_en.config import config_path, load_config, log_dir, write_default_config


def _setup_logging(verbose: bool) -> None:
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        d = log_dir()
        d.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(d / "rewrite-en.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except OSError:
        pass
    if verbose and sys.stderr is not None:
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        root.addHandler(sh)
    # Never let HTTP libraries log request bodies or headers.
    for name in ("anthropic", "httpx", "httpx2", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)


def cmd_set_key(args) -> int:
    from rewrite_en.keystore import set_api_key

    key = getpass.getpass("Anthropic API key (input hidden): ")
    try:
        set_api_key(key)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1
    print("Saved to the OS keychain.")
    return 0


def cmd_test(args) -> int:
    from rewrite_en.claude_client import ClaudeRewriter, RewriteError
    from rewrite_en.keystore import MissingAPIKey, get_api_key

    cfg = load_config()
    try:
        rewriter = ClaudeRewriter(cfg, get_api_key())
        print(rewriter.rewrite(args.text))
    except MissingAPIKey as e:
        print(e, file=sys.stderr)
        return 1
    except RewriteError as e:
        print(f"Error ({e.code}): {e}", file=sys.stderr)
        return 1
    return 0


def cmd_run(args) -> int:
    from rewrite_en import app
    from rewrite_en.keystore import MissingAPIKey, get_api_key

    write_default_config()
    cfg = load_config()
    try:
        key = get_api_key()
    except MissingAPIKey as e:
        logging.getLogger(__name__).error("no API key configured")
        print(e, file=sys.stderr)
        return 1
    app.run(cfg, key)
    return 0


def cmd_config(args) -> int:
    path = write_default_config()
    print(path)
    print(load_config())
    return 0


def cmd_install_autostart(args) -> int:
    from rewrite_en import autostart

    print(autostart.install())
    return 0


def cmd_uninstall_autostart(args) -> int:
    from rewrite_en import autostart

    print(autostart.uninstall())
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="rewrite-en", description="Rewrite selected text into natural English with a hotkey.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("-v", "--verbose", action="store_true", help="also log to the terminal")
    # Also accept -v after the subcommand; SUPPRESS keeps a top-level -v from being reset.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-v", "--verbose", action="store_true", default=argparse.SUPPRESS, help="also log to the terminal")
    sub = p.add_subparsers(dest="command", required=True)

    def add(name, help_, func):
        sp = sub.add_parser(name, help=help_, parents=[common])
        sp.set_defaults(func=func)
        return sp

    add("run", "run in the background and listen for the hotkey", cmd_run)
    add("set-key", "store your Anthropic API key in the OS keychain", cmd_set_key)
    add("test", "rewrite TEXT once, without the hotkey", cmd_test).add_argument("text")
    add("config", f"create/show the config file ({config_path()})", cmd_config)
    add("install-autostart", "start at login", cmd_install_autostart)
    add("uninstall-autostart", "stop starting at login", cmd_uninstall_autostart)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _setup_logging(args.verbose)
    return args.func(args)
