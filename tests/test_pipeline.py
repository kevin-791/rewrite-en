import threading

from rewrite_en.claude_client import RewriteError
from rewrite_en.pipeline import Outcome, RewritePipeline, Timings


class FakeClipboard:
    def __init__(self, value="ORIGINAL"):
        self.value = value
        self.history = []

    def get(self):
        return self.value

    def set(self, text):
        self.value = text
        self.history.append(text)


class FakeKeys:
    """Simulates the focused app: copy puts `selection` on the clipboard."""

    def __init__(self, clipboard, selection="xin chào", copy_works=True):
        self.cb = clipboard
        self.selection = selection
        self.copy_works = copy_works
        self.copies = 0
        self.pastes = []

    def wait_modifiers_released(self, timeout):
        return True

    def copy(self):
        self.copies += 1
        if self.copy_works and self.selection is not None:
            self.cb.value = self.selection

    def paste(self):
        self.pastes.append(self.cb.value)


class FakeRewriter:
    def __init__(self, result="hello", error=None):
        self.result = result
        self.error = error
        self.calls = []

    def rewrite(self, text):
        self.calls.append(text)
        if self.error:
            raise self.error
        return self.result


class FakeFeedback:
    def __init__(self):
        self.events = []

    def started(self):
        self.events.append("started")

    def success(self):
        self.events.append("success")

    def error(self):
        self.events.append("error")


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


def make(selection="xin chào", copy_works=True, rewriter=None, original="ORIGINAL"):
    cb = FakeClipboard(original)
    keys = FakeKeys(cb, selection, copy_works)
    rw = rewriter or FakeRewriter()
    fb = FakeFeedback()
    clock = FakeClock()
    p = RewritePipeline(cb, keys, rw, fb, Timings(), sleep=clock.sleep, clock=clock)
    return p, cb, keys, rw, fb


def test_success_pastes_once_then_restores_clipboard():
    p, cb, keys, rw, fb = make()
    assert p.rewrite_selection() is Outcome.OK
    assert rw.calls == ["xin chào"]
    assert keys.pastes == ["hello"]
    assert cb.value == "ORIGINAL"
    # result was on the clipboard before the paste, original restored after
    assert cb.history[-2:] == ["hello", "ORIGINAL"]
    assert fb.events == ["started", "success"]


def test_no_selection_does_not_call_api_or_paste():
    p, cb, keys, rw, fb = make(copy_works=False)
    assert p.rewrite_selection() is Outcome.NO_SELECTION
    assert rw.calls == []
    assert keys.pastes == []
    assert cb.value == "ORIGINAL"
    assert fb.events == ["started", "error"]


def test_whitespace_selection_counts_as_no_selection():
    p, cb, keys, rw, fb = make(selection="   \n ")
    assert p.rewrite_selection() is Outcome.NO_SELECTION
    assert rw.calls == []
    assert cb.value == "ORIGINAL"


def test_api_error_restores_clipboard_and_does_not_paste():
    p, cb, keys, rw, fb = make(rewriter=FakeRewriter(error=RewriteError("network", "down")))
    assert p.rewrite_selection() is Outcome.ERROR
    assert keys.pastes == []
    assert cb.value == "ORIGINAL"
    assert fb.events == ["started", "error"]


def test_unexpected_exception_still_restores_clipboard():
    p, cb, keys, rw, fb = make(rewriter=FakeRewriter(error=KeyError("boom")))
    assert p.rewrite_selection() is Outcome.ERROR
    assert keys.pastes == []
    assert cb.value == "ORIGINAL"


def test_empty_original_clipboard_is_restored_as_empty():
    p, cb, keys, rw, fb = make(original="")
    assert p.rewrite_selection() is Outcome.OK
    assert cb.value == ""


def test_selection_identical_to_clipboard_is_still_detected():
    # The marker trick must detect a copy even if the selection equals the old clipboard.
    p, cb, keys, rw, fb = make(selection="ORIGINAL")
    assert p.rewrite_selection() is Outcome.OK
    assert rw.calls == ["ORIGINAL"]


def test_overlapping_hotkey_is_ignored():
    started, release = threading.Event(), threading.Event()

    class SlowRewriter(FakeRewriter):
        def rewrite(self, text):
            started.set()
            release.wait(5)
            return super().rewrite(text)

    p, cb, keys, rw, fb = make(rewriter=SlowRewriter())
    results = []
    t = threading.Thread(target=lambda: results.append(p.rewrite_selection()))
    t.start()
    assert started.wait(5)
    assert p.busy
    assert p.rewrite_selection() is Outcome.BUSY
    release.set()
    t.join(5)
    assert results == [Outcome.OK]
    assert keys.copies == 1
    assert not p.busy
