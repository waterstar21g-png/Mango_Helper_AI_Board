"""BATCH 1~13 순차 골격 단위 테스트 (브라우저 최소)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import batch_steps as B  # noqa: E402


def test_batch_module_has_ordered_steps():
    names = [
        "run_row_batch",
        "step02_init",
        "step03_input_url",
        "step04_click_search",
        "step05_popup_open",
        "step06_popup_close",
        "step07_save_range",
        "step08_filter_count",
        "step09_to_12_db_save",
    ]
    for n in names:
        assert hasattr(B, n), n
        assert callable(getattr(B, n)), n


def test_doc_mentions_failure_cause():
    doc = Path(B.__file__).read_text(encoding="utf-8")
    assert "6·11·12" in doc or "6·11·12" in doc.replace(" ", "")
    assert "순차" in doc


def test_step06_no_settle_noise():
    """요건: 6단계 후 안정화/검색결과준비/샷 로그 액션 제거(호출 금지)."""
    src = Path(B.__file__).read_text(encoding="utf-8")
    # run_row_batch 본문(함수 시작~step02_init 직전) — 주석 제외한 활성 코드만
    start = src.index("def run_row_batch")
    end = src.index("def step02_init")
    body = src[start:end]
    active = "\n".join(
        ln for ln in body.splitlines() if not ln.lstrip().startswith("#")
    )
    assert "망고 검색결과 안정화" not in active
    assert "검색결과 준비" not in active
    assert "01_results_ready" not in active
    assert "wait_mango_search_settle(" not in active
    assert "prepare_product_view_for_shot(" not in active
    assert "step06b_quick_check" in active
    assert "step07_save_range" in active


def test_extract_mango_save_log_lines():
    import collect as C

    sample = (
        " unrelated header\n"
        "......신규상품(3개)의 저장을 시작합니다.\n"
        "[1] [20260808 16:11:00] [상품업데이트] [ABCmart.a-rt.com] "
        "[1010081838] 뉴발란스 공용 W480KW5 -> 금지어(뉴발란스)가 포함되어, "
        "상품이 저장 및 업데이트가 제한됩니다.\n"
        "[2] [20260808 16:11:12] [상품업데이트] x\n"
        "......신규상품의 저장이 완료되었습니다.\n"
        "trailing\n"
    )
    lines = C.extract_mango_save_log_lines(sample)
    assert lines[0].endswith("저장을 시작합니다.")
    assert any("[상품업데이트]" in ln for ln in lines)
    assert any("완료되었습니다" in ln for ln in lines)
    assert "trailing" not in "".join(lines)


if __name__ == "__main__":
    failed = 0
    for name, fn in [
        ("ordered_steps", test_batch_module_has_ordered_steps),
        ("doc", test_doc_mentions_failure_cause),
        ("step06_no_noise", test_step06_no_settle_noise),
        ("mango_log_extract", test_extract_mango_save_log_lines),
    ]:
        try:
            fn()
            print(f"PASS {name}")
        except Exception as e:
            failed += 1
            print(f"FAIL {name}: {type(e).__name__}: {e}")
    raise SystemExit(failed)
