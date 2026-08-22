"""Chrome 기동 인자 · 확장 안내 회귀 테스트.

버그: --disable-extensions-except 가 "지정 경로 외 전부 비활성화" 라서,
정품 Chrome 137+ 가 --load-extension 을 무시하는 상황과 겹치면 전용 프로필에
웹스토어로 설치해 둔 더망고 확장까지 매 실행 꺼버렸다 →
"더망고 확장프로그램이 설치되어 있지 않습니다" 배너.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import collect as C  # noqa: E402


class _FakePopen:
    """subprocess.Popen 대체 — 실제 Chrome 을 띄우지 않고 인자만 잡아둔다."""

    captured: list[str] = []

    def __init__(self, args, **kwargs):
        type(self).captured = list(args)


def _launch_args(monkeypatch, tmp_path: Path) -> list[str]:
    monkeypatch.setattr(C, "PROFILE_DIR", tmp_path / ".chrome-profile")
    monkeypatch.setattr(C, "find_browser_exe", lambda: "/fake/chrome")
    monkeypatch.setattr(C.subprocess, "Popen", _FakePopen)
    # 포트가 바로 열린 것으로 처리해 대기 루프를 건너뛴다
    monkeypatch.setattr(C, "cdp_port_open", lambda *a, **k: True)
    C.launch_debug_browser()
    return _FakePopen.captured


def test_disable_extensions_except_is_never_passed(monkeypatch, tmp_path):
    """웹스토어로 설치한 더망고 확장을 매 실행 꺼버리면 안 된다."""
    args = _launch_args(monkeypatch, tmp_path)
    assert not any(a.startswith("--disable-extensions-except") for a in args)
    assert not any(a == "--disable-extensions" for a in args)


def test_remote_debugging_uses_non_default_profile(monkeypatch, tmp_path):
    """Chrome 136+ 는 기본 프로필에서 원격 디버깅을 무시한다 — 전용 프로필 필수."""
    args = _launch_args(monkeypatch, tmp_path)
    assert f"--remote-debugging-port={C.CDP_PORT}" in args
    assert any(a.startswith("--user-data-dir=") for a in args)


def test_load_extension_still_attempted_for_chromium_builds(monkeypatch, tmp_path):
    """Chromium·Chrome for Testing 에서는 아직 동작하므로 인자는 유지한다."""
    args = _launch_args(monkeypatch, tmp_path)
    assert any(a.startswith("--load-extension=") for a in args)


def test_missing_extension_guide_points_to_webstore():
    """확장이 없을 때는 웹스토어 1회 설치를 안내해야 한다."""
    msg = C.MANGO_EXT_MISSING_GUIDE.format(cause="net::ERR_BLOCKED_BY_CLIENT")
    assert C.MANGO_EXT_WEBSTORE in msg
    assert C.MANGO_EXT_ID in msg
    assert "ERR_BLOCKED_BY_CLIENT" in msg


def test_install_page_failure_does_not_mask_original_error():
    """설치 페이지를 못 열어도 원래 오류를 덮지 않는다."""

    class _BoomContext:
        def new_page(self):
            raise RuntimeError("no page")

    assert C.open_extension_install_page(_BoomContext()) is None


class _ProbePage:
    """N 번째 시도부터 확장 팝업이 열리는 가짜 page."""

    def __init__(self, succeed_on: int):
        self.succeed_on = succeed_on
        self.attempts = 0

    def goto(self, url, **kwargs):
        self.attempts += 1
        if self.attempts < self.succeed_on:
            raise RuntimeError("net::ERR_BLOCKED_BY_CLIENT")


def test_wait_for_extension_install_continues_after_user_installs(monkeypatch):
    """설치가 확인되면 재실행 없이 그대로 이어서 진행한다."""
    monkeypatch.setattr(C.time, "sleep", lambda *_: None)
    page = _ProbePage(succeed_on=3)
    assert C.wait_for_extension_install(page, timeout_sec=60) is True
    assert page.attempts == 3


def test_wait_for_extension_install_gives_up_after_timeout(monkeypatch):
    """끝내 설치하지 않으면 False — 호출부가 원래 오류를 올린다."""
    monkeypatch.setattr(C.time, "sleep", lambda *_: None)
    ticks = iter([1000.0] + [1000.0 + i * 5 for i in range(1, 400)])
    monkeypatch.setattr(C.time, "time", lambda: next(ticks))
    assert C.wait_for_extension_install(_ProbePage(succeed_on=10**9), 30) is False


def test_wait_for_extension_install_honors_stop_request(monkeypatch):
    """보드 [수집 종료] 를 누르면 대기 중에도 즉시 빠져나온다."""
    monkeypatch.setattr(C, "stop_requested", lambda: True)
    with pytest.raises(C.CollectStopped):
        C.wait_for_extension_install(_ProbePage(succeed_on=10**9), 60)


if __name__ == "__main__":
    print("PASS (pytest 로 실행하세요)")
