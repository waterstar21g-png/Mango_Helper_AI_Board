"""
P3_설정수정_카테고리매핑초기화 — 카테고리매핑 설정 일괄 초기화.

★요건 1: `P3_필터단위_수집조건수정` 소스를 그대로 활용한다.
그 프로그램은 이미 잘 돌고 있고, 이 프로그램은 **버튼만 다르다**.

| 단계 | P3_필터단위_수집조건수정 | 이 프로그램 |
|------|--------------------------|-------------|
| 목록 접속·수집사이트·검색 | 동일 (`apply_site_filter`) | 동일 — 그 모듈 함수를 호출 |
| 행 버튼 | [수집조건수정] `modify_filter(fuid)` | **[설정수정]** `market_mapping_new(ftid)` |
| 팝업 작업 | 번역옵션 선택 → 저장하기 | **[검색필터 설정삭제]** `config_remove('','Y')` |
| 팝업 닫기 | 동일 (`close_popup`) | 동일 — 그 모듈 함수를 호출 |

입력
  - 사이트명 (`select[name="site_id"]`)
  - 작업 URL (필수) — 검색필터 목록 화면 주소. 시작 시 [선택조건으로 검색하기] 자동 클릭
  - 작업행 범위 [부터]-[까지] (1부터, 양끝 포함)

사용법:
  python reset_category_mapping.py --list-url "<목록 URL>" --row-from 1 --row-to 5
  python reset_category_mapping.py --list-url "<목록 URL>" --site-id MUSINSA.com
  python reset_category_mapping.py --list-url "<목록 URL>" --list-rows   # 확인만
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
P3_OPTION_DIR = ROOT / "P3_필터단위_수집조건수정"
P3_UPDATE_DIR = ROOT / "P3_필터_갱신"
for _p in (P2_DIR, P3_OPTION_DIR, P3_UPDATE_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# ★잘 돌고 있는 P3_필터단위_수집조건수정 을 그대로 쓴다
import update_collect_option as p3opt  # noqa: E402

ProgressFn = Callable[[str], None]

HERE = Path(__file__).resolve().parent
STOP_FLAG_PATH = HERE / ".reset_stop"

DEFAULT_SITE = ""  # 비우면 화면에 이미 선택된 사이트 유지
DEFAULT_ROW_FROM = 1
DEFAULT_ROW_TO = 5

# 목록 행의 [설정수정] — P3_수집조건수정 의 modify_filter 자리에 이것이 온다
#   <a onclick="market_mapping_new('670');" class="defbtn_med dtype4">
#     <span>설정수정</span></a>
SETTING_EDIT_JS = "market_mapping_new"
SETTING_EDIT_LABEL = "설정수정"

# 팝업 하단 [검색필터 설정삭제]
#   <a onclick="config_remove('','Y')" class="defbtn_lar dtype4">
#     <span>검색필터 설정삭제</span></a>
DELETE_JS = "config_remove"
DELETE_LABEL = "검색필터 설정삭제"
DELETE_SELECTORS = (
    f'a[onclick*="{DELETE_JS}"]',
    f'xpath=//a[.//span[normalize-space()="{DELETE_LABEL}"]]',
    f'xpath=//*[self::a or self::button or self::input]'
    f'[contains(normalize-space(.),"{DELETE_LABEL}")]',
)

# 설정수정 팝업 페이지 (클릭이 막혔을 때 직접 열기용)
CATEGORY_PAGE = "admin_category_set.php"

# 대기 — P3_수집조건수정 의 값을 그대로 쓴다
T_CLICK = p3opt.T_CLICK
T_FIELD = p3opt.T_FIELD
T_NAV = p3opt.T_NAV
T_CLOSE = p3opt.T_CLOSE
GAP_ROW = p3opt.GAP_ROW
GAP_SEARCH = p3opt.GAP_SEARCH

# 검색은 서버 왕복이다 — 행이 나올 때까지 넉넉히 기다린다 (나오면 즉시 진행)
ROWS_WAIT_S = 60.0
ROWS_POLL_S = 0.5


@dataclass
class RowInfo:
    index: int
    ftid: str
    filter_name: str = ""


@dataclass
class RunResult:
    ok: bool
    rows: int = 0
    reset_done: int = 0
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


# ── 행 목록 ──────────────────────────────────────────────────────

LIST_ROWS_JS = r"""
() => {
  // 행의 [설정수정] 링크에서 거꾸로 행을 찾는다 (표 구조에 기대지 않는다)
  const out = [];
  for (const a of Array.from(document.querySelectorAll('a[onclick*="market_mapping_new"]'))) {
    const m = (a.getAttribute('onclick') || '').match(/market_mapping_new\(\s*'?(\d+)'?/);
    if (!m) continue;
    const ftid = m[1];
    const tr = a.closest('tr');
    let name = '';
    if (tr) {
      const vals = Array.from(tr.querySelectorAll('input[type="text"], input:not([type])'))
        .map(i => (i.value || i.getAttribute('value') || '').trim())
        .filter(v => v && !/^https?:/i.test(v) && !/^\d+$/.test(v));
      if (vals.length) name = vals[0];
    }
    if (!name) {
      const byUid = document.querySelector('input[attr-uid="' + ftid + '"]');
      if (byUid) name = (byUid.value || byUid.getAttribute('value') || '').trim();
    }
    if (!name && tr) name = ((tr.innerText || '').trim().split('\n')[0] || '').trim();
    out.push({ftid: ftid, filterName: name});
  }
  return out;
}
"""


def list_rows(page) -> list[RowInfo]:
    """모든 탭·프레임에서 행을 모으고 ftid 중복은 제거한다."""
    rows: list[RowInfo] = []
    seen: set[str] = set()
    for ctx in p3opt.contexts(page):
        try:
            found = ctx.evaluate(LIST_ROWS_JS) or []
        except Exception:
            found = []
        for item in found:
            ftid = str((item or {}).get("ftid") or "").strip()
            if not ftid or ftid in seen:
                continue
            seen.add(ftid)
            rows.append(
                RowInfo(
                    index=len(rows),
                    ftid=ftid,
                    filter_name=str((item or {}).get("filterName") or "").strip(),
                )
            )
    return rows


def wait_for_rows(
    page,
    *,
    timeout_s: float = ROWS_WAIT_S,
    progress: ProgressFn | None = None,
) -> list[RowInfo]:
    """검색 결과 행이 나타날 때까지 기다린다 (나오면 즉시 진행)."""
    deadline = time.time() + max(0.0, float(timeout_s))
    tries = 0
    while True:
        tries += 1
        rows = list_rows(page)
        if rows:
            if tries > 1:
                _log(progress, f"  검색 결과 대기 {tries}회 → {len(rows)}행")
            return rows
        if time.time() >= deadline:
            _log(progress, f"  검색 결과 대기 {timeout_s:.0f}초 초과 — 0행", major=True)
            return []
        time.sleep(ROWS_POLL_S)


def reveal(page, *, progress: ProgressFn | None = None) -> None:
    """★크롬 창을 화면 맨 앞으로 — 작업 과정(팝업·입력·닫기)이 눈에 보이게 한다.

    `P3_필터_갱신` 과 같은 방식. 안 해주면 실제로는 잘 돌고 있어도 보드 창
    뒤에 숨어서 사용자에게 안 보인다.
    """
    try:
        page.bring_to_front()
    except Exception as e:  # noqa: BLE001
        _log(progress, f"  (화면 앞으로 가져오기 실패: {e})")


def search_and_collect(
    pw,
    url: str,
    site_id: str,
    *,
    progress: ProgressFn | None = None,
) -> tuple[object, list[RowInfo], str]:
    """요건 0번: 입력한 「작업 URL」로 화면을 띄우고 → 사이트 선택 → 검색 → 행 수집.

    사이트 선택/검색이 실패해도 행 수집은 그대로 진행한다 — 붙여넣은 URL 이
    이미 검색조건(site_id 등)을 담고 있어 화면에 결과가 떠 있는 경우가 있고,
    그때 여기서 멈추면 실제로 있는 행을 0건으로 오판하게 된다.
    반환: (page, rows, 사용한 url)
    """
    page, used = p3opt._open_mango(pw, url, progress)
    reveal(page, progress=progress)
    if not p3opt.apply_site_filter(page, site_id, progress=progress):
        _log(
            progress,
            "  사이트 선택/검색을 건너뜁니다 — 작업 URL 화면의 결과로 계속합니다",
            major=True,
        )
    page = p3opt.pick_list_page(page, progress=progress)
    rows = wait_for_rows(page, progress=progress)
    return page, rows, used


def row_range(row_from: int | str, row_to: int | str) -> tuple[int, int]:
    """작업행 범위 보정 — 1부터, 양끝 포함. 뒤집히면 바로잡는다."""

    def _n(v, default: int) -> int:
        try:
            n = int(str(v).strip())
        except (TypeError, ValueError):
            return default
        return n if n > 0 else default

    start = _n(row_from, DEFAULT_ROW_FROM)
    end = _n(row_to, DEFAULT_ROW_TO)
    if end < start:
        start, end = end, start
    return start, end


def slice_rows(rows: list[RowInfo], start: int, end: int) -> list[RowInfo]:
    return rows[max(0, start - 1) : end]


def diagnose(page, *, progress: ProgressFn | None = None) -> None:
    """행을 못 찾을 때 화면 상태를 남긴다."""
    for i, ctx in enumerate(p3opt.contexts(page), start=1):
        try:
            info = ctx.evaluate(
                r"""() => ({
                  url: location.href,
                  tr: document.querySelectorAll('tr').length,
                  edit: document.querySelectorAll('a[onclick*="market_mapping_new"]').length,
                  attrUid: document.querySelectorAll('input[attr-uid]').length,
                })"""
            )
        except Exception as e:  # noqa: BLE001
            _log(progress, f"  [진단] 프레임{i}: 읽기 실패 ({e})", major=True)
            continue
        _log(
            progress,
            f"  [진단] 프레임{i} tr={info.get('tr')}"
            f" · 설정수정={info.get('edit')} · attr-uid={info.get('attrUid')}",
            major=True,
        )
        _log(progress, f"  [진단] 프레임{i} url={info.get('url')}", major=True)


# ── 팝업 (열기 → 검색필터 설정삭제 → 닫기) ───────────────────────


def build_popup_url(list_url: str, ftid: str) -> str:
    """설정수정 팝업 URL (`admin_category_set.php?tm=F&ps_ftid=<ftid>`)."""
    from urllib.parse import urlencode, urlsplit, urlunsplit

    parts = urlsplit(str(list_url or ""))
    if not parts.netloc:
        return ""
    path = parts.path or ""
    marker = "/admin/"
    idx = path.find(marker)
    base_dir = path[: idx + len(marker) - 1] if idx >= 0 else path.rsplit("/", 1)[0]
    query = urlencode({"tm": "F", "ps_ftid": str(ftid)})
    return urlunsplit((parts.scheme, parts.netloc, f"{base_dir}/{CATEGORY_PAGE}", query, ""))


def open_setting_popup(page, ftid: str, *, list_url: str = "", progress: ProgressFn | None = None):
    """행의 [설정수정] 클릭 → 팝업. 실패 시 팝업 URL 직접 오픈.

    ★프레임을 돌 때 버튼이 **있는지 먼저 즉시 확인**(count, 대기 없음)하고,
    있는 프레임에서만 클릭+팝업대기 를 시도한다. 관계없는 프레임(광고 iframe 등)
    까지 매번 클릭을 시도하면 없는 요소를 T_CLICK·T_NAV 만큼씩 헛기다리게 된다.
    """
    ftid = str(ftid or "").strip()
    if ftid:
        sel = f"a[onclick*=\"{SETTING_EDIT_JS}('{ftid}')\"]"
        for ctx in p3opt.contexts(page):
            try:
                loc = ctx.locator(sel).first
                if loc.count() == 0:
                    continue
                with page.expect_popup(timeout=T_NAV) as info:
                    loc.click(timeout=T_CLICK)
                popup = info.value
                reveal(popup, progress=progress)
                _log(progress, f"  [{SETTING_EDIT_LABEL}] 팝업 열림 (ftid={ftid})")
                return popup
            except Exception:
                continue

    url = build_popup_url(list_url, ftid) if ftid else ""
    if not url:
        _log(progress, f"오류: 설정수정 팝업을 열지 못했습니다 (ftid={ftid or '?'})", major=True)
        return None
    try:
        popup = page.context.new_page()
        popup.goto(url, wait_until="domcontentloaded", timeout=T_NAV)
        reveal(popup, progress=progress)
        _log(progress, f"  [{SETTING_EDIT_LABEL}] 직접 열기 (ftid={ftid})")
        return popup
    except Exception as e:  # noqa: BLE001
        _log(progress, f"오류: 팝업 열기 실패 · {e}", major=True)
        return None


def click_delete_setting(popup, *, progress: ProgressFn | None = None) -> bool:
    """팝업의 [검색필터 설정삭제] 클릭. 못 찾으면 config_remove('','Y') 직접 호출."""
    for sel in DELETE_SELECTORS:
        try:
            loc = popup.locator(sel).first
            if loc.count() == 0:
                continue
            loc.click(timeout=T_CLICK)
            _log(progress, f"  [{DELETE_LABEL}] 클릭")
            return True
        except Exception:
            continue
    try:
        popup.evaluate(
            "() => { if (typeof config_remove === 'function') config_remove('', 'Y'); }"
        )
        _log(progress, f"  [{DELETE_LABEL}] (config_remove 직접 호출)")
        return True
    except Exception as e:  # noqa: BLE001
        _log(progress, f"오류: {DELETE_LABEL} 클릭 실패 · {e}", major=True)
        return False


def reset_one_row(
    page,
    row: RowInfo,
    *,
    list_url: str = "",
    progress: ProgressFn | None = None,
) -> bool:
    """한 행 — [설정수정] → 팝업 → [검색필터 설정삭제] → 팝업 닫기."""
    _log(progress, f"필터 [{row.filter_name or '?'}] (ftid={row.ftid})", major=True)

    popup = open_setting_popup(page, row.ftid, list_url=list_url, progress=progress)
    if popup is None:
        return False

    try:
        popup.on("dialog", lambda d: d.accept())
    except Exception:
        pass

    try:
        try:
            popup.wait_for_selector(DELETE_SELECTORS[0], timeout=T_FIELD)
        except Exception:
            pass
        ok = click_delete_setting(popup, progress=progress)
        time.sleep(GAP_ROW)
        return ok
    finally:
        p3opt.close_popup(popup, timeout_ms=T_CLOSE, progress=progress)
        _log(progress, "  팝업 닫기")


# ── 실행 ─────────────────────────────────────────────────────────


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
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        result.errors.append(f"의존성 로드 실패: {e}")
        _log(progress, result.errors[0], major=True)
        return result

    start, end = row_range(row_from, row_to)
    _log(progress, f"작업행 범위: {start}~{end}행", major=True)

    try:
        with sync_playwright() as pw:
            # ★P3_수집조건수정 과 동일한 접속·검색 절차
            page, found, url = search_and_collect(pw, url, site_id, progress=progress)
            if not found:
                result.errors.append("작업 대상 행이 없습니다 (검색 결과 확인).")
                _log(progress, result.errors[0], major=True)
                diagnose(page, progress=progress)
                return result

            rows = slice_rows(found, start, end)
            result.rows = len(rows)
            _log(
                progress,
                f"검색 결과 {len(found)}행 중 {start}~{end}행 → {len(rows)}건 수행",
                major=True,
            )
            if not rows:
                result.errors.append(
                    f"작업 범위({start}~{end})에 해당하는 행이 없습니다"
                    f" (검색 결과 {len(found)}행)."
                )
                _log(progress, result.errors[0], major=True)
                return result

            for i, row in enumerate(rows, start=1):
                if stop_requested():
                    _log(progress, "사용자 중단", major=True)
                    break
                _log(progress, f"[{i}/{len(rows)}] (전체 {start + i - 1}행)", major=True)
                if reset_one_row(page, row, list_url=url, progress=progress):
                    result.reset_done += 1
                    _log(progress, "  초기화 완료", major=True)
                else:
                    result.failed += 1
                    result.errors.append(f"설정삭제 실패 · 필터={row.filter_name}")
                time.sleep(GAP_ROW)
    except Exception as e:  # noqa: BLE001
        result.errors.append(str(e))
        _log(progress, f"실행 오류: {e}", major=True)
        return result
    finally:
        clear_stop_flag()

    result.ok = result.reset_done > 0 and result.failed == 0
    _log(
        progress,
        f"완료 — 초기화 {result.reset_done} · 실패 {result.failed} / 대상 {result.rows}",
        major=True,
    )
    return result


def list_rows_only(
    *,
    site_id: str = DEFAULT_SITE,
    list_url: str = "",
    row_from: int | str = "",
    row_to: int | str = "",
    progress: ProgressFn | None = None,
) -> list[RowInfo]:
    """삭제 없이 행 번호·ftid·필터명만 확인한다."""
    url = (list_url or "").strip()
    if not url:
        _log(progress, "작업 URL 을 입력하세요 (검색필터 목록 화면 주소).", major=True)
        return []

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        _log(progress, f"의존성 로드 실패: {e}", major=True)
        return []

    rows: list[RowInfo] = []
    try:
        with sync_playwright() as pw:
            page, rows, url = search_and_collect(pw, url, site_id, progress=progress)
            if not rows and page is not None:
                diagnose(page, progress=progress)
    except Exception as e:  # noqa: BLE001
        _log(progress, f"행 목록 확인 오류: {e}", major=True)
        return []

    start, end = (row_range(row_from, row_to) if str(row_from).strip() else (0, 0))
    _log(progress, f"검색 결과 {len(rows)}행", major=True)
    for i, row in enumerate(rows, start=1):
        mark = " ★" if start and start <= i <= end else ""
        _log(progress, f"  {i}행 · ftid={row.ftid} · 필터={row.filter_name or '?'}{mark}")
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="P3_설정수정_카테고리매핑초기화")
    parser.add_argument("--site-id", default=DEFAULT_SITE, help="사이트명 (비우면 유지)")
    parser.add_argument(
        "--list-url", default="", help="작업 URL (필수 — 검색필터 목록 화면 주소)"
    )
    parser.add_argument(
        "--row-from", type=int, default=DEFAULT_ROW_FROM, help=f"작업 시작 행 (기본 {DEFAULT_ROW_FROM})"
    )
    parser.add_argument(
        "--row-to", type=int, default=DEFAULT_ROW_TO, help=f"작업 종료 행 (기본 {DEFAULT_ROW_TO})"
    )
    parser.add_argument(
        "--list-rows", action="store_true", help="초기화 없이 행 번호·ftid·필터명만 확인"
    )
    args = parser.parse_args(argv)

    if args.list_rows:
        list_rows_only(
            site_id=args.site_id,
            list_url=args.list_url,
            row_from=args.row_from,
            row_to=args.row_to,
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
