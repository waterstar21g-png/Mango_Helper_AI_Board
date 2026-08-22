"""
P3_설정수정_카테고리매핑초기화 — 카테고리매핑 설정 일괄 초기화 (설정삭제).

`P3_필터단위_수집조건수정` 을 복제해, 목록·팝업 조작은 `P5_101_카테고리매핑_필터세부설정`
(map_categories.py) 의 검증된 로직을 그대로 재사용한다 — 같은 화면(admin_group.php
목록 · market_mapping_new 팝업 · admin_category_set.php)을 다루기 때문이다.

입력
  - 수집사이트명 (`select[name="site_id"]`)
  - 작업 목록 URL — 작업 시작 시 **[선택조건으로 검색하기]** 자동 클릭
  - 작업 행 범위 [부터]-[까지] (1부터, 양끝 포함)

동작 (행 범위 안에서 순차)
  1. **[설정수정]**(`onclick="market_mapping_new('<ftid>')"`) 클릭 → 팝업
     (`admin_category_set.php?tm=F&ps_ftid=<ftid>`)
  2. 팝업에서 **[검색필터 설정삭제]**(`onclick="config_remove('','Y')"`) 클릭
  3. 팝업 닫기
  4. 다음 행

사용법:
  python reset_category_mapping.py --row-from 1 --row-to 5
  python reset_category_mapping.py --site-id MUSINSA.com --row-from 11 --row-to 11
  python reset_category_mapping.py --list-rows --row-from 11 --row-to 11   # 확인만
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
P2_DIR = ROOT / "P2"
P5_101_DIR = ROOT / "P5_101_카테고리매핑_필터세부설정"
for _p in (P2_DIR, P5_101_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import map_categories as mc  # noqa: E402 — 목록·팝업 로직 재사용

ProgressFn = Callable[[str], None]

HERE = Path(__file__).resolve().parent
STOP_FLAG_PATH = HERE / ".reset_stop"

DEFAULT_LIST_URL = mc.DEFAULT_LIST_URL
DEFAULT_SITE = ""  # 비우면 화면에 이미 선택된 사이트 유지
DEFAULT_ROW_FROM = mc.DEFAULT_ROW_FROM
DEFAULT_ROW_TO = mc.DEFAULT_ROW_TO

# 팝업 하단 [검색필터 설정삭제]
#   <a onclick="config_remove('','Y')" target="_blank" class="defbtn_lar dtype4">
#     <span>검색필터 설정삭제</span></a>
DELETE_JS = "config_remove"
DELETE_SELECTORS = (
    f'a[onclick*="{DELETE_JS}"]',
    'xpath=//a[.//span[normalize-space()="검색필터 설정삭제"]]',
    'xpath=//*[self::a or self::button or self::input]'
    '[contains(normalize-space(.),"검색필터 설정삭제")]',
)

T_CLICK = mc.T_CLICK
GAP = mc.GAP


@dataclass
class RunResult:
    ok: bool
    rows: int = 0
    deleted: int = 0
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
    line = f"##MAIN##{message}" if major else message
    print(line, flush=True)
    if progress:
        progress(line)


def click_delete_setting(popup, *, progress: ProgressFn | None = None) -> bool:
    """팝업의 [검색필터 설정삭제] 클릭. 못 찾으면 config_remove('','Y') 직접 호출."""
    for sel in DELETE_SELECTORS:
        try:
            loc = popup.locator(sel).first
            if loc.count() == 0:
                continue
            loc.click(timeout=T_CLICK)
            _log(progress, "  [검색필터 설정삭제] 클릭")
            return True
        except Exception:
            continue
    try:
        popup.evaluate("() => { if (typeof config_remove === 'function') config_remove('', 'Y'); }")
        _log(progress, "  [검색필터 설정삭제] (config_remove 직접 호출)")
        return True
    except Exception as e:  # noqa: BLE001
        _log(progress, f"오류: 검색필터 설정삭제 클릭 실패 · {e}", major=True)
        return False


def reset_one_row(
    page,
    row: "mc.RowInfo",
    *,
    list_url: str,
    progress: ProgressFn | None = None,
) -> bool:
    """한 행 — [설정수정] → 팝업 → [검색필터 설정삭제] → 팝업 닫기."""
    _log(progress, f"필터 [{row.filter_name}] (ftid={row.ftid})", major=True)

    popup = mc.open_setting_popup(page, row, list_url=list_url, progress=progress)
    if popup is None:
        return False

    try:
        popup.on("dialog", lambda d: d.accept())
    except Exception:
        pass

    try:
        ok = click_delete_setting(popup, progress=progress)
        time.sleep(GAP)
        return ok
    finally:
        mc.close_popup(popup)
        _log(progress, "  팝업 닫기")


def run_reset(
    *,
    site_id: str = DEFAULT_SITE,
    list_url: str = "",
    row_from: int | str = DEFAULT_ROW_FROM,
    row_to: int | str = DEFAULT_ROW_TO,
    progress: ProgressFn | None = None,
) -> RunResult:
    result = RunResult(ok=False)
    clear_stop_flag()

    # 작업 URL 은 필수 — 기본값으로 엉뚱한 화면에서 초기화하면 되돌릴 수 없다
    url = (list_url or "").strip()
    if not url:
        result.errors.append(
            "작업 URL 을 입력하세요 — 브라우저에서 검색필터 목록 화면을 띄운 뒤"
            " 주소창 URL 을 그대로 붙여넣으면 됩니다."
        )
        _log(progress, result.errors[0], major=True)
        return result

    try:
        import collect as p2  # noqa: WPS433
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        result.errors.append(f"의존성 로드 실패: {e}")
        _log(progress, result.errors[0], major=True)
        return result

    start, end = mc.row_range(row_from, row_to)

    try:
        with sync_playwright() as pw:
            _browser, page = p2.connect_browser(pw)
            page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            _log(progress, "검색필터 목록 화면", major=True)

            if site_id:
                mc.select_site(page, site_id, progress=progress)
            mc.click_search_filter(page, progress=progress)

            found = [r for r in mc.list_rows(page) if r.ftid]
            if not found:
                result.errors.append("작업 대상 행이 없습니다 (검색 결과 확인).")
                _log(progress, result.errors[0], major=True)
                mc.diagnose_list(page, progress=progress)
                return result

            rows = mc.slice_rows(found, start, end)
            result.rows = len(rows)
            _log(
                progress,
                f"검색 결과 {len(found)}행 중 **{start}~{end}행** → {len(rows)}건 수행",
                major=True,
            )
            if not rows:
                result.errors.append(
                    f"작업 범위({start}~{end})에 해당하는 행이 없습니다 (검색 결과 {len(found)}행)."
                )
                _log(progress, result.errors[0], major=True)
                return result

            for i, row in enumerate(rows, start=1):
                if stop_requested():
                    _log(progress, "사용자 중단", major=True)
                    break
                _log(progress, f"[{i}/{len(rows)}] (전체 {start + i - 1}행)", major=True)
                if reset_one_row(page, row, list_url=url, progress=progress):
                    result.deleted += 1
                    _log(progress, "  삭제 완료", major=True)
                else:
                    result.failed += 1
                    result.errors.append(f"설정삭제 실패 · 필터={row.filter_name}")
                time.sleep(GAP)
    except Exception as e:  # noqa: BLE001
        result.errors.append(str(e))
        _log(progress, f"실행 오류: {e}", major=True)
        return result
    finally:
        clear_stop_flag()

    result.ok = result.deleted > 0 and result.failed == 0
    _log(
        progress,
        f"완료 — 삭제 {result.deleted} · 실패 {result.failed} / 대상 {result.rows}",
        major=True,
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="P3_설정수정_카테고리매핑초기화")
    parser.add_argument("--site-id", default=DEFAULT_SITE, help="상품수집사이트 (비우면 유지)")
    parser.add_argument("--list-url", default="", help="목록 URL (필수 — 검색필터 목록 화면 주소)")
    parser.add_argument(
        "--row-from", type=int, default=DEFAULT_ROW_FROM, help=f"작업 시작 행 (기본 {DEFAULT_ROW_FROM})"
    )
    parser.add_argument(
        "--row-to", type=int, default=DEFAULT_ROW_TO, help=f"작업 종료 행 (기본 {DEFAULT_ROW_TO})"
    )
    parser.add_argument(
        "--list-rows",
        action="store_true",
        help="삭제 없이 행 번호·ftid·필터명만 확인",
    )
    args = parser.parse_args(argv)

    if args.list_rows:
        mc.list_rows_only(
            site_id=args.site_id, list_url=args.list_url,
            row_from=args.row_from, row_to=args.row_to,
        )
        return 0

    result = run_reset(
        site_id=args.site_id,
        list_url=args.list_url,
        row_from=args.row_from,
        row_to=args.row_to,
    )
    for e in result.errors:
        print(f"[오류] {e}", flush=True)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
