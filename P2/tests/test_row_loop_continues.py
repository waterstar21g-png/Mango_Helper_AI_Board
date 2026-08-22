"""회귀 테스트: 엑셀 2번째 자료에서 배치가 통째로 멈추지 않는다.

과거 회귀(v2.0.62에서 수정): main() 행 루프가 특정 문구의 RuntimeError만
잡고 나머지 예외는 그대로 올려보내서, 2번째 입력 준비 중 예외 하나로
배치 전체가 조용히 죽었다(화면에는 아무 표시도 없이 종료).

엑셀에 자료가 남아 있는 동안에는 어떤 예외가 나든 그 행만 실패 처리하고
다음 행으로 계속 진행해야 한다. 단, 사용자가 보드에서 누른 "수집 종료"
(CollectStopped)만은 즉시 멈춰야 한다.

브라우저 없이 main()의 행 루프만 검증한다(플레이라이트 진입점 대체).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import collect as C  # noqa: E402


ROWS = [
    {"row": 2, "label": "카테고리1", "url": "https://shop.example/c1"},
    {"row": 3, "label": "카테고리2", "url": "https://shop.example/c2"},
    {"row": 4, "label": "카테고리3", "url": "https://shop.example/c3"},
]


class _FakePage:
    url = "https://admin.example/bulk"
    context = None

    def set_default_timeout(self, *_a, **_k) -> None:
        pass

    def bring_to_front(self) -> None:
        pass

    def wait_for_timeout(self, *_a, **_k) -> None:
        pass


class _FakePlaywright:
    def __enter__(self):
        return self

    def __exit__(self, *_exc) -> bool:
        return False


def _run_main(
    monkeypatch,
    tmp_path,
    *,
    on_prepare=None,
    on_row=None,
    extra=None,
    argv_extra=(),
):
    """행 루프만 돌린다. (처리된 순번 목록, 종료코드) 반환."""
    processed: list[int] = []
    prepared: list[int] = []

    page = _FakePage()

    monkeypatch.setattr(C, "SHOT_ROOT", tmp_path)
    monkeypatch.setattr(C, "STOP_FLAG", tmp_path / ".collect_stop")
    monkeypatch.setattr(C, "read_excel", lambda _p: list(ROWS))
    monkeypatch.setattr(C, "sync_playwright", lambda: _FakePlaywright())
    monkeypatch.setattr(C, "connect_browser", lambda _p: (None, page))
    monkeypatch.setattr(
        C, "ensure_mango_extension_settings", lambda *_a, **_k: None
    )
    monkeypatch.setattr(C, "refresh_if_closed", lambda p: p)
    monkeypatch.setattr(C, "ensure_ready_page", lambda p: p)
    monkeypatch.setattr(C.RunCtx, "shot", lambda *_a, **_k: None)
    monkeypatch.setattr(C.RunCtx, "write_gallery", lambda _self: None)

    def _prepare(p, _ctx, *, next_ordinal, next_row):
        prepared.append(next_ordinal)
        if on_prepare is not None:
            on_prepare(next_ordinal)
        return p

    def _process(p, row, ctx):
        processed.append(ctx.input_ordinal)
        if on_row is not None:
            return on_row(ctx.input_ordinal)
        return True

    monkeypatch.setattr(C, "ensure_overlays_closed_before_next", _prepare)
    monkeypatch.setattr(C, "process_row_with_retries", _process)
    monkeypatch.setattr(
        sys,
        "argv",
        ["collect.py", str(tmp_path / "in.xlsx"), "3", "--yes", *argv_extra],
    )
    for name, value in (extra or {}).items():
        monkeypatch.setattr(C, name, value)

    code = 0
    try:
        C.main()
    except SystemExit as e:  # main()은 결과에 따라 sys.exit 한다
        code = int(e.code or 0)
    return processed, prepared, code


def test_prepare_exception_on_second_row_does_not_kill_batch(monkeypatch, tmp_path):
    """2번째 행 준비 중 예외 → 그 행만 실패, 3번째 행은 계속 처리."""

    def on_prepare(ordinal: int) -> None:
        if ordinal == 2:
            # 실제로는 Playwright TargetClosedError 등 임의 예외가 난다
            raise TimeoutError("입력#2 수집 전 팝업/모달 대기 중 타임아웃")

    processed, prepared, code = _run_main(
        monkeypatch, tmp_path, on_prepare=on_prepare
    )

    assert prepared == [2, 3], "2·3번째 행 모두 준비 단계까지는 진입해야 한다"
    assert processed == [1, 3], "2번째 실패가 3번째 처리를 막으면 안 된다"
    assert code == 2, "실패가 있으면 종료코드 2 (중단 130이 아니다)"


def test_row_exception_on_second_row_continues_to_third(monkeypatch, tmp_path):
    """2번째 행 처리 중 예외 → 3번째 행까지 진행."""

    def on_row(ordinal: int) -> bool:
        if ordinal == 2:
            raise RuntimeError("망고 검색결과 확인 실패")
        return True

    processed, _prepared, code = _run_main(monkeypatch, tmp_path, on_row=on_row)

    assert processed == [1, 2, 3]
    assert code == 2


def test_row_failure_return_false_continues(monkeypatch, tmp_path):
    """2번째 행이 예외 없이 실패(False) → 나머지 행 계속."""

    processed, _prepared, code = _run_main(
        monkeypatch, tmp_path, on_row=lambda o: o != 2
    )

    assert processed == [1, 2, 3]
    assert code == 2


def test_user_stop_still_halts_immediately(monkeypatch, tmp_path):
    """사용자 '수집 종료'만은 즉시 멈춘다 (중단코드 130)."""

    def on_row(ordinal: int) -> bool:
        if ordinal == 2:
            raise C.CollectStopped("사용자 수집 종료 요청")
        return True

    processed, _prepared, code = _run_main(monkeypatch, tmp_path, on_row=on_row)

    assert processed == [1, 2], "종료 요청 후 3번째 행으로 넘어가면 안 된다"
    assert code == 130


def test_all_rows_succeed(monkeypatch, tmp_path):
    processed, prepared, code = _run_main(monkeypatch, tmp_path)

    assert processed == [1, 2, 3]
    assert prepared == [2, 3]
    assert code == 0


def test_verify_does_not_limit_rows_to_two(monkeypatch, tmp_path):
    """--verify 는 스크린샷 범위일 뿐 — 엑셀 전체 행을 처리해야 한다.

    보드 체크박스 "1·2행 전과정 스크린샷"(기본 ON)이 --verify 를 넘기는데,
    예전에는 verify가 max_rows=2를 강제해서 엑셀에 자료가 많아도 2행만
    처리하고 "완료"로 끝났다 = 사용자가 본 "엑셀 2번째 자료에서 중단".
    """
    processed, _prepared, code = _run_main(
        monkeypatch, tmp_path, argv_extra=("--verify", "--shot-first", "2")
    )

    assert processed == [1, 2, 3], "검증 모드에서도 3번째 행까지 처리해야 한다"
    assert code == 0


def test_max_rows_still_limits_explicitly(monkeypatch, tmp_path):
    """행 수 제한은 --max-rows 로만 건다."""
    processed, _prepared, code = _run_main(
        monkeypatch, tmp_path, argv_extra=("--max-rows", "2")
    )

    assert processed == [1, 2]
    assert code == 0


def test_fatal_outside_loop_is_visible_on_board(monkeypatch, tmp_path, capsys):
    """행 루프 밖 예외도 실행로그(##SUB##)로 남긴다.

    보드는 마커 없는 줄(파이썬 트레이스백 포함)을 화면에서 버리므로,
    ctx.info 로 남기지 않으면 화면에 아무 표시 없이 종료된다.
    """

    def _boom(_p):
        raise RuntimeError("브라우저 연결 실패(디버그 포트 없음)")

    processed, _prepared, code = _run_main(
        monkeypatch, tmp_path, extra={"connect_browser": _boom}
    )

    out = capsys.readouterr().out
    assert processed == []
    assert code == 3, "루프 밖 예외는 전용 종료코드 3"
    assert C.SUB_LINE_MARK in out
    assert "[치명]" in out
    assert "브라우저 연결 실패" in out


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
