"""
P2_필터단위_상품수변경 — 더망고 필터 목록의 적용상품수 일괄 갱신.

1) 필터 목록(검색필터 화면) 행을 읽음
2) 각 행에서 수집조건수정 → 적용상품수 입력 → 저장하기 → 확인

사용법:
  python update_product_count.py --apply-count 50
  python update_product_count.py --apply-count 50 --mango-url "https://..."
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
P3_DIR = ROOT / "P3_필터_갱신"
P2_DIR = ROOT / "P2"
for p in (P3_DIR, P2_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import update_filters as p3  # noqa: E402

ProgressFn = Callable[[str], None]

STOP_FLAG_PATH = Path(__file__).resolve().parent / ".count_stop"
RUN_LOG_DIR = Path(__file__).resolve().parent / "run-logs"


@dataclass
class RunResult:
    ok: bool
    total_rows: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


def clear_stop_flag() -> None:
    try:
        STOP_FLAG_PATH.unlink(missing_ok=True)  # type: ignore[call-arg]
    except Exception:
        pass


def stop_requested() -> bool:
    return STOP_FLAG_PATH.is_file()


def _log(progress: ProgressFn | None, message: str, *, major: bool = False) -> None:
    line = message or ""
    if major:
        line = f"##MAIN##{line}"
    print(line, flush=True)
    if progress:
        progress(line)


def _patch_p3_stop() -> Path:
    """P3 내부 stop_requested 가 이 모듈 플래그를 보도록."""
    old = p3.STOP_FLAG_PATH
    p3.STOP_FLAG_PATH = STOP_FLAG_PATH
    return old


def _restore_p3_stop(old: Path) -> None:
    p3.STOP_FLAG_PATH = old


def find_apply_count_locator(page, prefer_value: str = "3"):
    """적용상품수 입력칸 (없으면 저장상품수 폴백)."""
    prefer = (prefer_value or "3").strip()
    for label in ("적용상품수", "저장상품수"):
        try:
            loc = page.locator(
                f"xpath=//tr[.//*[contains(normalize-space(.),'{label}')]]"
                "//input[(@type='text' or @type='number' or not(@type))]"
            ).first
            if loc.count() > 0:
                return loc
        except Exception:
            continue
    return p3.find_save_count_locator(page, prefer_value=prefer)


def set_apply_count(page, target: str, *, progress: ProgressFn | None = None) -> bool:
    """적용상품수(또는 저장상품수) 입력칸에 값 설정."""
    target = str(target).strip()
    if not target.isdigit():
        _log(progress, f"오류: 적용상품수는 숫자여야 합니다: {target!r}", major=True)
        return False

    work, kind = p3.resolve_modify_target(page)
    if work is None:
        _log(progress, "오류: 수정 화면(적용상품수) 미검출", major=True)
        return False

    p3.wait_for_save_count_ready(work, timeout_ms=8_000)
    loc = find_apply_count_locator(work, prefer_value="3")
    if loc is None:
        _log(progress, f"오류: 적용상품수 입력칸 미검출 · 목표={target}", major=True)
        return False

    before_val = ""
    try:
        before_val = (loc.input_value(timeout=500) or "").strip()
    except Exception:
        before_val = ""

    filled = False
    try:
        loc.fill(target, timeout=3_000)
        filled = True
    except Exception:
        try:
            filled = bool(
                loc.evaluate(
                    """(el, want) => {
                      el.focus();
                      el.value = String(want);
                      el.dispatchEvent(new Event('input', {bubbles:true}));
                      el.dispatchEvent(new Event('change', {bubbles:true}));
                      el.blur();
                      return (el.value || '').trim() === String(want);
                    }""",
                    target,
                )
            )
        except Exception:
            filled = False

    after_val = target if filled else ""
    try:
        after_val = (loc.input_value(timeout=500) or "").strip() or after_val
    except Exception:
        pass

    _log(
        progress,
        f"적용상품수 {before_val or '?'} → {after_val or target} (목표={target})",
        major=True,
    )
    return filled


def run_update_product_count(
    apply_count: int | str,
    *,
    mango_url: str = "",
    progress: ProgressFn | None = None,
) -> RunResult:
    target = str(apply_count).strip()
    if not target.isdigit() or int(target) < 0:
        return RunResult(ok=False, errors=["적용상품수는 0 이상의 숫자여야 합니다."])

    result = RunResult(ok=False)
    clear_stop_flag()
    old_stop = _patch_p3_stop()

    try:
        import collect as p2  # noqa: WPS433
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        _restore_p3_stop(old_stop)
        result.errors.append(f"의존성 로드 실패: {e}")
        _log(progress, result.errors[0], major=True)
        return result

    url = (mango_url or "").strip() or p3.DEFAULT_MANGO_URL
    _log(progress, f"적용상품수: {target}", major=True)

    try:
        with sync_playwright() as pw:
            _browser, page = p2.connect_browser(pw)
            page = p3.navigate_mango_url(page, url, progress=progress, p2=p2)

            rows = p3.list_demango_rows(page)
            editable = [r for r in rows if r.get("hasEdit")]
            result.total_rows = len(editable)
            if not editable:
                result.errors.append("필터 목록에서 수정 가능한 행이 없습니다.")
                _log(progress, result.errors[0], major=True)
                return result

            _log(progress, f"필터 {len(editable)}행 — 순차 적용상품수 갱신", major=True)

            for i, drow in enumerate(editable, start=1):
                if stop_requested():
                    _log(progress, "사용자 중단", major=True)
                    break

                row_idx = int(drow.get("index") or 0)
                d_filter = (drow.get("filterName") or "").strip()
                d_url = (drow.get("url") or "").strip()
                d_fuid = str(drow.get("fuid") or "").strip()

                _log(
                    progress,
                    f"{i}/{len(editable)} · 필터={d_filter or '?'} · URL={d_url[:80]}",
                    major=True,
                )

                if not p3.click_edit_on_row(
                    page,
                    row_idx,
                    row_url=d_url,
                    filter_hint=d_filter,
                    fuid_hint=d_fuid,
                    progress=progress,
                ):
                    result.failed += 1
                    result.errors.append(f"수집조건수정 실패 · 필터={d_filter}")
                    continue

                if not p3.wait_modify_page(page):
                    result.failed += 1
                    result.errors.append(f"수정화면 미열림 · 필터={d_filter}")
                    p3._return_to_list(page, url)
                    continue

                if not set_apply_count(page, target, progress=progress):
                    result.failed += 1
                    p3._return_to_list(page, url)
                    continue

                if not p3.click_save_button(page):
                    result.failed += 1
                    result.errors.append(f"저장하기 실패 · 필터={d_filter}")
                    p3._return_to_list(page, url)
                    continue

                if not p3.click_modified_confirm(page, progress=progress):
                    result.failed += 1
                    result.errors.append(f"확인 실패 · 필터={d_filter}")
                    p3._return_to_list(page, url)
                    continue

                result.updated += 1
                _log(progress, f"  갱신 완료 · 적용상품수={target}", major=True)
                p3._return_to_list(page, url)
                time.sleep(0.3)

    except Exception as e:  # noqa: BLE001
        result.errors.append(str(e))
        _log(progress, f"실행 오류: {e}", major=True)
    finally:
        _restore_p3_stop(old_stop)
        clear_stop_flag()

    result.ok = result.updated > 0 and result.failed == 0 and not result.errors
    _log(
        progress,
        f"완료 — 성공 {result.updated} · 실패 {result.failed} · 건너뜀 {result.skipped} "
        f"/ 대상 {result.total_rows}",
        major=True,
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="P2_필터단위_상품수변경")
    parser.add_argument("--apply-count", required=True, help="적용상품수")
    parser.add_argument("--mango-url", default="", help="필터 목록 URL (기본=P3 초기값)")
    args = parser.parse_args(argv)
    result = run_update_product_count(args.apply_count, mango_url=args.mango_url)
    if result.errors:
        for e in result.errors:
            print(f"[오류] {e}", flush=True)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
