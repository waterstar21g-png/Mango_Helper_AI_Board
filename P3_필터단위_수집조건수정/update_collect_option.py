"""
P3_필터단위_수집조건수정 — 더망고 필터 목록의 수집조건(번역옵션) 일괄 변경.

`P2_필터단위_상품수변경` 을 복제해, 입력값을 「적용상품수(숫자)」 대신
「번역옵션(목록에서 선택)」 으로 바꾼 프로그램이다.

1) 필터 목록(검색필터 화면) 행을 읽음
2) 각 행에서 수집조건수정 → **번역옵션 적용** → 저장하기 → 확인

번역옵션은 망고 수정화면의 실제 컨트롤(select · 라디오 · 체크박스)에서 읽어오므로,
보드 리스트박스 목록도 `--list-options` 로 망고에서 그대로 가져온다.

사용법:
  python update_collect_option.py --list-options
  python update_collect_option.py --translate-option "번역후저장"
  python update_collect_option.py --translate-option "번역후저장" --mango-url "https://..."
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from urllib.parse import urlencode, urlsplit, urlunsplit

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

STOP_FLAG_PATH = Path(__file__).resolve().parent / ".option_stop"
OPTIONS_CACHE_PATH = Path(__file__).resolve().parent / ".translate_options.json"
SITES_CACHE_PATH = Path(__file__).resolve().parent / ".site_options.json"

# 필터 목록 화면 검색줄의 수집사이트 드롭다운
#   <div class="searchRow"><select name="site_id" class="input_" style="width:160px"> …
SITE_SELECT_NAME = "site_id"

# 수집사이트 선택 후 누르는 버튼
SEARCH_BUTTON_LABEL = "선택조건으로 검색하기"

# 수집사이트 목록 — 망고 화면 순서 그대로 (첫 항목은 전체)
SITE_ALL_LABEL = "-- 수집사이트 --"
DEFAULT_SITE_OPTIONS = (
    SITE_ALL_LABEL,
    "4910.kr",
    "ABCmart.a-rt.com",
    "HIVER.co.kr",
    "MUSINSA.com",
    "Zara.com/de",
)

# 망고 수집조건수정 팝업의 「번역 후 저장」 컨트롤
#   <tr id="layer_tr_limit_count">
#     <td>번역 후 저장</td>
#     <td><select name="translate_method" onchange="trans_change(this.value);"> …
TRANSLATE_SELECT_NAME = "translate_method"

# 첫 화면 (검색필터 목록) — 보드 「망고 URL」 초기값
DEFAULT_LIST_URL = "https://tmg1898.cafe24.com/mall/admin/shop/getGoodsCategory.php"

# 목록 행의 수집조건수정 버튼 → 팝업창
#   <a onclick="modify_filter('720');" class="defbtn_sm dtype6"><span>수집조건수정</span></a>
#   팝업 URL: admin_group_modify.php?ps_mode=modify_filter&ps_fuid=720
MODIFY_PAGE = "admin_group_modify.php"
MODIFY_MODE = "modify_filter"

# 팝업 하단 저장하기
#   <a onclick="set_save();" class="defbtn_lar dtype2"><span>저장하기</span></a>
SAVE_SELECTORS = (
    'a[onclick*="set_save"]',
    'xpath=//a[.//span[normalize-space()="저장하기"]]',
    'xpath=//*[self::a or self::button or self::input][contains(normalize-space(.),"저장하기")]',
)

# 저장하기 바로 옆 닫기
#   <a onclick="window.close();" class="defbtn_lar dtype6"> … </a>
CLOSE_SELECTORS = (
    'a[onclick*="window.close"]',
    "a.defbtn_lar.dtype6",
    'xpath=//a[.//span[normalize-space()="닫기"]]',
    'xpath=//*[self::a or self::button or self::input][contains(normalize-space(.),"닫기")]',
)

# ── 속도 (컴퓨터 속도로 — 단계별 대기를 10배 축소) ────────────────
T_CLICK = 1_500  # 버튼 클릭 대기 (ms)
T_FIELD = 2_000  # 입력/드롭다운 등장 대기 (ms)
T_READ = 200  # 현재값 읽기 (ms)
T_CLOSE = 800  # 팝업 닫힘 대기 (ms)
T_NAV = 5_000  # 목록 화면 이동 대기 (ms)
T_POPUP = 1_000  # 팝업 렌더 대기 (ms)
T_SITE = 5_000  # 수집사이트 드롭다운 대기 (ms) — 요건: 5초
POPUP_TRIES = 3  # 1초 단위로 최대 3회 (요소가 뜨면 즉시 진행)
GAP_ROW = 0.02  # 행 간 간격 (초)
GAP_SEARCH = 0.15  # 검색 후 목록 정착 (초)

# 보드 리스트박스 목록 — 망고 화면의 실제 옵션 순서 그대로
DEFAULT_TRANSLATE_OPTIONS = (
    "번역안함",
    "더망고 무료 번역기 사용",
    "구글 번역기 사용",
    "DeepL 번역기 사용",
    "네이버(클라우드) 번역기 사용",
)

# 번역 관련 컨트롤을 찾을 때 쓰는 라벨 키워드 (공백 무시 비교)
LABEL_KEYWORDS = ("번역 후 저장", "번역후저장", "번역옵션", "번역")

OPTION_LINE_PREFIX = "##OPTION##"
SITE_LINE_PREFIX = "##SITE##"


@dataclass
class RunResult:
    ok: bool
    total_rows: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class TranslateControl:
    """망고 수정화면의 번역옵션 컨트롤."""

    kind: str  # "select" | "radio" | "checkbox"
    options: list[str]
    locator: object | None = None
    choices: list[tuple[str, object]] = field(default_factory=list)  # (라벨, 로케이터)
    values: list[str] = field(default_factory=list)  # select 의 option value


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
    old = p3.STOP_FLAG_PATH
    p3.STOP_FLAG_PATH = STOP_FLAG_PATH
    return old


def _restore_p3_stop(old: Path) -> None:
    p3.STOP_FLAG_PATH = old


# ── 옵션 이름 매칭 · 캐시 ─────────────────────────────────────────


def normalize(text: str) -> str:
    return "".join(str(text or "").split())


def match_option(options: list[str], wanted: str) -> str | None:
    """리스트박스에서 고른 값을 실제 컨트롤 옵션에 맞춘다.

    정확 일치 → 공백 무시 일치 → **대소문자 무시** 일치 → 부분 포함 순서.
    `MUSINSA.COM` 처럼 대소문자가 다르게 입력돼도 `MUSINSA.com` 옵션을 찾는다.
    """
    want = str(wanted or "").strip()
    if not want:
        return None
    for o in options:
        if o == want:
            return o
    nw = normalize(want)
    for o in options:
        if normalize(o) == nw:
            return o
    nwl = nw.lower()
    for o in options:
        if normalize(o).lower() == nwl:
            return o
    for o in options:
        no = normalize(o).lower()
        if nwl and (nwl in no or no in nwl):
            return o
    return None


def load_cached_options() -> list[str]:
    """보드 리스트박스용 — 마지막으로 망고에서 읽은 목록."""
    try:
        data = json.loads(OPTIONS_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return list(DEFAULT_TRANSLATE_OPTIONS)
    opts = [str(o).strip() for o in data.get("options", []) if str(o).strip()]
    return opts or list(DEFAULT_TRANSLATE_OPTIONS)


def save_cached_options(options: list[str]) -> None:
    payload = {"options": [str(o).strip() for o in options if str(o).strip()]}
    try:
        OPTIONS_CACHE_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except OSError:
        pass


def load_cached_sites() -> list[str]:
    """보드 수집사이트 리스트박스용."""
    try:
        data = json.loads(SITES_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return list(DEFAULT_SITE_OPTIONS)
    sites = [str(s).strip() for s in data.get("sites", []) if str(s).strip()]
    return sites or list(DEFAULT_SITE_OPTIONS)


def save_cached_sites(sites: list[str]) -> None:
    payload = {"sites": [str(s).strip() for s in sites if str(s).strip()]}
    try:
        SITES_CACHE_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except OSError:
        pass


def is_all_sites(site: str) -> bool:
    """수집사이트 '전체'(플레이스홀더) 선택인지."""
    text = normalize(site)
    if not text:
        return True
    return text == normalize(SITE_ALL_LABEL) or set(text) <= {"-"}


def format_option_lines(options: list[str], sites: list[str] | None = None) -> str:
    """--list-options 출력 (보드가 파싱)."""
    lines = [f"{OPTION_LINE_PREFIX}{o}" for o in options]
    lines += [f"{SITE_LINE_PREFIX}{s}" for s in (sites or [])]
    return "\n".join(lines)


def _parse_prefixed(text: str, prefix: str) -> list[str]:
    out: list[str] = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line.startswith(prefix):
            continue
        value = line[len(prefix) :].strip()
        if value and value not in out:
            out.append(value)
    return out


def parse_option_lines(text: str) -> list[str]:
    return _parse_prefixed(text, OPTION_LINE_PREFIX)


def parse_site_lines(text: str) -> list[str]:
    return _parse_prefixed(text, SITE_LINE_PREFIX)


# ── 망고 수정화면의 번역옵션 컨트롤 ──────────────────────────────

_CONTROL_JS = """
(keywords) => {
  const norm = (s) => (s || '').replace(/\\s+/g, '');
  const hit = (s) => keywords.some(k => norm(s).includes(norm(k)));
  const scopeText = (el) => {
    const tr = el.closest('tr');
    const box = tr || el.closest('td,div,label,fieldset') || el.parentElement;
    return (box && box.innerText) || '';
  };
  const labelOf = (inp) => {
    if (inp.id) {
      const lb = document.querySelector(`label[for="${inp.id}"]`);
      if (lb && lb.innerText.trim()) return lb.innerText.trim();
    }
    const wrap = inp.closest('label');
    if (wrap && wrap.innerText.trim()) return wrap.innerText.trim();
    const sib = inp.nextElementSibling;
    if (sib && sib.innerText && sib.innerText.trim()) return sib.innerText.trim();
    return (inp.value || '').trim();
  };

  for (const sel of Array.from(document.querySelectorAll('select'))) {
    if (sel.disabled) continue;
    if (!hit(scopeText(sel)) && !hit(sel.name || '') && !hit(sel.id || '')) continue;
    const options = Array.from(sel.options)
      .map(o => (o.textContent || '').trim())
      .filter(Boolean);
    if (!options.length) continue;
    return {kind: 'select', options, name: sel.name || '', id: sel.id || ''};
  }

  const radios = Array.from(document.querySelectorAll('input[type="radio"]'))
    .filter(r => !r.disabled && (hit(scopeText(r)) || hit(r.name || '')));
  if (radios.length > 1) {
    return {
      kind: 'radio',
      options: radios.map(labelOf),
      name: radios[0].name || '',
      values: radios.map(r => r.value || ''),
    };
  }

  const checks = Array.from(document.querySelectorAll('input[type="checkbox"]'))
    .filter(c => !c.disabled && (hit(scopeText(c)) || hit(c.name || '') || hit(labelOf(c))));
  if (checks.length === 1) {
    return {
      kind: 'checkbox',
      options: ['사용', '미사용'],
      name: checks[0].name || '',
      id: checks[0].id || '',
      label: labelOf(checks[0]),
    };
  }
  return null;
}
"""


_SELECT_OPTIONS_JS = """
(el) => Array.from(el.options).map(o => ({
  text: (o.textContent || '').trim(),
  value: o.value || '',
})).filter(o => o.text)
"""

_SELECTED_LABEL_JS = """
(el) => {
  const o = el.options[el.selectedIndex];
  return o ? (o.textContent || '').trim() : '';
}
"""


def find_translate_select(page):
    """`select[name="translate_method"]` — 망고 화면의 번역 후 저장 드롭다운."""
    try:
        loc = page.locator(f'select[name="{TRANSLATE_SELECT_NAME}"]').first
        if loc.count() > 0:
            return loc
    except Exception:
        pass
    return None


def contexts(page) -> list:
    """페이지 + 모든 프레임 (망고 화면이 프레임을 쓰는 경우 대응)."""
    out = [page]
    try:
        for f in page.frames:
            if f is not page and f not in out:
                out.append(f)
    except Exception:
        pass
    return out


_DIAG_JS = """
() => ({
  url: location.href,
  title: document.title,
  selects: Array.from(document.querySelectorAll('select'))
    .map(e => (e.name || e.id || '(무명)')),
  buttons: Array.from(document.querySelectorAll('a,button,input[type=button],input[type=submit]'))
    .map(e => ((e.innerText || e.value || '').trim()))
    .filter(t => t && t.length <= 30)
    .slice(0, 25),
  frames: window.frames.length,
})
"""


def all_pages(page) -> list:
    """같은 브라우저의 모든 탭 (망고는 탭을 여러 개 쓴다)."""
    try:
        pages = list(page.context.pages)
    except Exception:
        return [page]
    if page not in pages:
        pages.insert(0, page)
    return pages


def diagnose(page, *, progress: ProgressFn | None = None) -> list[dict]:
    """탭·프레임별 URL·select 이름·버튼 라벨을 로그에 찍는다 (원인 파악용)."""
    reports: list[dict] = []
    for i, pg in enumerate(all_pages(page), start=1):
        for j, ctx in enumerate(contexts(pg), start=1):
            try:
                info = ctx.evaluate(_DIAG_JS)
            except Exception as e:  # noqa: BLE001
                _log(progress, f"  [진단] 탭{i}-프레임{j}: 읽기 실패 ({e})", major=True)
                continue
            info["tab"] = i
            info["frame"] = j
            reports.append(info)
            _log(
                progress,
                f"  [진단] 탭{i}-프레임{j} url={str(info.get('url'))[:90]}"
                f" · select={info.get('selects')}"
                f" · 버튼={info.get('buttons')}",
                major=True,
            )
    return reports


def dump_selects(page, *, progress: ProgressFn | None = None) -> list[str]:
    """모든 탭·프레임의 select name/id 목록."""
    found: list[str] = []
    for info in diagnose(page, progress=progress):
        found.extend(str(n) for n in (info.get("selects") or []))
    return found


def pick_list_page(page, *, progress: ProgressFn | None = None):
    """수집사이트 드롭다운이 있는 탭을 고른다 (다른 탭을 보고 있던 문제 대응)."""
    pages = all_pages(page)
    for pg in pages:
        for ctx in contexts(pg):
            try:
                if ctx.locator(f'select[name="{SITE_SELECT_NAME}"]').first.count() > 0:
                    if pg is not page:
                        _log(progress, "  목록 화면 탭으로 전환", major=True)
                    return pg
            except Exception:
                continue
    for pg in pages:  # URL 로 판단
        try:
            if "getGoodsCategory" in (pg.url or ""):
                if pg is not page:
                    _log(progress, "  목록 URL 탭으로 전환", major=True)
                return pg
        except Exception:
            continue
    return page


def find_site_select(page):
    """`select[name="site_id"]` — 필터 목록 검색줄의 수집사이트 드롭다운.

    프레임 안에 있을 수 있고, name 이 바뀌었을 수도 있어 옵션 텍스트로도 찾는다.
    """
    for ctx in contexts(page):
        try:
            loc = ctx.locator(f'select[name="{SITE_SELECT_NAME}"]').first
            if loc.count() > 0:
                return loc
        except Exception:
            continue

    # 폴백: 「수집사이트」 옵션을 가진 select
    for ctx in contexts(page):
        try:
            loc = ctx.locator(
                'xpath=//select[.//option[contains(normalize-space(.),"수집사이트")]]'
            ).first
            if loc.count() > 0:
                return loc
        except Exception:
            continue
    return None


def wait_site_select(page, *, progress: ProgressFn | None = None):
    """수집사이트 드롭다운 대기 — 모든 탭·프레임을 5초까지 훑는다 (뜨면 즉시)."""
    deadline = time.monotonic() + T_SITE / 1000
    logged = False
    while True:
        for pg in all_pages(page):
            loc = find_site_select(pg)
            if loc is not None:
                return loc
        if time.monotonic() >= deadline:
            return None
        if not logged:
            _log(progress, f"  수집사이트 드롭다운 대기 {T_SITE}ms …")
            logged = True
        try:
            page.wait_for_timeout(250)
        except Exception:
            time.sleep(0.25)


def read_site_options(page) -> list[str]:
    """수집사이트 드롭다운의 옵션 텍스트 목록."""
    loc = wait_site_select(page)
    if loc is None:
        return []
    try:
        raw = loc.evaluate(_SELECT_OPTIONS_JS)
    except Exception:
        return []
    return [str(o.get("text") or "").strip() for o in raw if str(o.get("text") or "").strip()]


def click_search(page, *, progress: ProgressFn | None = None) -> bool:
    """수집사이트 선택 후 **[선택조건으로 검색하기]** 클릭 — 실패 시 폴백."""
    selectors = (
        # 1순위: 실제 버튼 라벨
        f'xpath=//*[self::a or self::button or self::input]'
        f'[contains(normalize-space(.),"{SEARCH_BUTTON_LABEL}")'
        f' or @value="{SEARCH_BUTTON_LABEL}"]',
        f'xpath=//span[contains(normalize-space(.),"{SEARCH_BUTTON_LABEL}")]',
        # 폴백: 검색줄 버튼 · '검색' 이 들어간 버튼
        'xpath=//div[contains(@class,"searchRow")]//span[contains(@class,"bt_type")]'
        "//*[self::button or self::a or self::input]",
        'xpath=//*[self::a or self::button or self::input]'
        '[contains(normalize-space(.),"검색") or @value="검색"]',
    )
    attempts = [(ctx, s) for s in selectors for ctx in contexts(page)]
    for i, (ctx, sel) in enumerate(attempts, start=1):
        try:
            loc = ctx.locator(sel).first
            if loc.count() == 0:
                continue
            loc.click(timeout=T_CLICK)
            _log(
                progress,
                f"  [{SEARCH_BUTTON_LABEL}] 클릭"
                if i <= 2 * len(contexts(page))
                else "  검색 버튼 클릭(폴백)",
            )
            return True
        except Exception:
            continue
    try:
        page.locator('input[name="sch_keyword"]').first.press("Enter", timeout=T_CLICK)
        _log(progress, "  검색 실행(키워드칸 Enter)")
        return True
    except Exception:
        _log(progress, "경고: 검색 버튼을 찾지 못했습니다 (현재 목록으로 진행)", major=True)
        return False


def apply_site_filter(
    page,
    site: str,
    *,
    progress: ProgressFn | None = None,
) -> bool:
    """수집사이트 리스트박스 선택값을 목록 화면 검색조건에 적용하고 검색."""
    if is_all_sites(site):
        _log(progress, "수집사이트: 전체 (검색조건 미변경)", major=True)
        return True

    page = pick_list_page(page, progress=progress)
    loc = wait_site_select(page, progress=progress)
    if loc is None:
        _log(progress, "오류: 수집사이트 드롭다운 미검출", major=True)
        dump_selects(page, progress=progress)
        return False

    options = read_site_options(page)
    target = match_option(options, site) if options else site
    if target is None:
        _log(
            progress,
            f"오류: 수집사이트 미검출 · 선택={site!r} · 망고목록={options}",
            major=True,
        )
        return False

    try:
        loc.select_option(label=target, timeout=T_CLICK)
    except Exception as e:  # noqa: BLE001
        _log(progress, f"오류: 수집사이트 선택 실패 · {target} · {e}", major=True)
        return False

    _log(progress, f"수집사이트: {target} — 검색 실행", major=True)
    click_search(page, progress=progress)
    try:
        page.wait_for_load_state("domcontentloaded", timeout=T_NAV)
    except Exception:
        pass
    time.sleep(GAP_SEARCH)
    return True


def detect_translate_control(page) -> TranslateControl | None:
    """수정화면에서 번역옵션 컨트롤을 찾는다.

    1) 망고 실제 DOM: `select[name="translate_method"]`
    2) 폴백: 「번역 후 저장」 라벨 주변의 select · 라디오 · 체크박스
    """
    loc = find_translate_select(page)
    if loc is not None:
        try:
            raw = loc.evaluate(_SELECT_OPTIONS_JS)
        except Exception:
            raw = []
        options = [str(o.get("text") or "").strip() for o in raw if str(o.get("text") or "").strip()]
        if options:
            values = [str(o.get("value") or "") for o in raw]
            return TranslateControl(
                kind="select", options=options, locator=loc, values=values
            )

    try:
        info = page.evaluate(_CONTROL_JS, list(LABEL_KEYWORDS))
    except Exception:
        info = None
    if not info:
        return None

    kind = str(info.get("kind") or "")
    options = [str(o).strip() for o in (info.get("options") or []) if str(o).strip()]
    if not kind or not options:
        return None

    name = str(info.get("name") or "")
    el_id = str(info.get("id") or "")

    if kind == "select":
        loc = None
        if name:
            loc = page.locator(f'select[name="{name}"]').first
        elif el_id:
            loc = page.locator(f"select#{el_id}").first
        else:
            loc = page.locator("select").first
        return TranslateControl(kind="select", options=options, locator=loc)

    if kind == "radio":
        values = [str(v) for v in (info.get("values") or [])]
        choices: list[tuple[str, object]] = []
        for idx, label in enumerate(options):
            if name and idx < len(values) and values[idx]:
                loc = page.locator(
                    f'input[type="radio"][name="{name}"][value="{values[idx]}"]'
                ).first
            elif name:
                loc = page.locator(f'input[type="radio"][name="{name}"]').nth(idx)
            else:
                loc = page.locator('input[type="radio"]').nth(idx)
            choices.append((label, loc))
        return TranslateControl(kind="radio", options=options, choices=choices)

    # checkbox
    if el_id:
        loc = page.locator(f"input#{el_id}").first
    elif name:
        loc = page.locator(f'input[type="checkbox"][name="{name}"]').first
    else:
        loc = page.locator('input[type="checkbox"]').first
    return TranslateControl(kind="checkbox", options=options, locator=loc)


def read_current_option(control: TranslateControl) -> str:
    """현재 선택값 — select 는 **표시 라벨**(value 아님) 로 읽는다."""
    try:
        if control.kind == "select":
            return (control.locator.evaluate(_SELECTED_LABEL_JS) or "").strip()  # type: ignore[union-attr]
        if control.kind == "radio":
            for label, loc in control.choices:
                try:
                    if loc.is_checked(timeout=T_READ):
                        return label
                except Exception:
                    continue
            return ""
        if control.kind == "checkbox":
            checked = bool(control.locator.is_checked(timeout=T_READ))  # type: ignore[union-attr]
            return control.options[0] if checked else control.options[-1]
    except Exception:
        return ""
    return ""


ON_WORDS = ("사용", "적용", "켜", "체크", "on", "yes", "true", "저장")


def wants_on(option: str) -> bool:
    """체크박스용 — 선택값이 '켜기' 계열인지."""
    text = normalize(option).lower()
    if any(w in text for w in ("미사용", "안함", "해제", "off", "no", "false")):
        return False
    return any(normalize(w).lower() in text for w in ON_WORDS)


def apply_option(
    control: TranslateControl,
    option: str,
    *,
    progress: ProgressFn | None = None,
) -> bool:
    """번역옵션을 컨트롤에 적용. 적용 후 값을 다시 읽어 확인한다."""
    target = match_option(control.options, option)
    if target is None:
        _log(
            progress,
            f"오류: 번역옵션 미검출 · 선택={option!r} · 망고옵션={control.options}",
            major=True,
        )
        return False

    before = read_current_option(control)

    try:
        if control.kind == "select":
            # 라벨로 선택 (onchange="trans_change(this.value)" 는 select_option 이 발생시킨다)
            try:
                control.locator.select_option(label=target, timeout=T_CLICK)  # type: ignore[union-attr]
            except Exception:
                value = ""
                if target in control.options:
                    idx = control.options.index(target)
                    if idx < len(control.values):
                        value = control.values[idx]
                control.locator.select_option(  # type: ignore[union-attr]
                    value or target, timeout=T_CLICK
                )
        elif control.kind == "radio":
            loc = next((l for lab, l in control.choices if lab == target), None)
            if loc is None:
                return False
            try:
                loc.check(timeout=T_CLICK)
            except Exception:
                loc.click(timeout=T_CLICK)
        else:  # checkbox
            if wants_on(target):
                control.locator.check(timeout=T_CLICK)  # type: ignore[union-attr]
            else:
                control.locator.uncheck(timeout=T_CLICK)  # type: ignore[union-attr]
    except Exception as e:  # noqa: BLE001
        _log(progress, f"오류: 번역옵션 적용 실패 · {target} · {e}", major=True)
        return False

    after = read_current_option(control)
    ok = normalize(after) == normalize(target) if after else True
    _log(
        progress,
        f"번역옵션 {before or '?'} → {after or target} (선택={target})",
        major=True,
    )
    if not ok:
        _log(progress, f"오류: 적용 확인 실패 · 기대={target} · 현재={after}", major=True)
    return ok


def set_translate_option(page, option: str, *, progress: ProgressFn | None = None) -> bool:
    """수정 팝업에서 번역옵션을 적용."""
    control = detect_translate_control(page)
    if control is None:
        work, _kind = p3.resolve_modify_target(page)
        control = detect_translate_control(work) if work is not None else None
    if control is None:
        _log(progress, "오류: 번역옵션 컨트롤 미검출", major=True)
        return False

    return apply_option(control, option, progress=progress)


# ── 수집조건수정 팝업 (열기 → 선택 → 저장하기 → 닫기) ────────────


def build_modify_url(list_url: str, fuid: str) -> str:
    """목록 URL 기준으로 수집조건수정 팝업 URL 을 만든다.

    팝업은 `/mall/admin/admin_group_modify.php` 로, 목록(`/mall/admin/shop/…`)보다
    한 단계 위다. `/admin/` 을 기준점으로 잡는다.
    """
    parts = urlsplit(str(list_url or ""))
    if not parts.netloc:
        return ""

    path = parts.path or ""
    marker = "/admin/"
    idx = path.find(marker)
    base_dir = path[: idx + len(marker) - 1] if idx >= 0 else path.rsplit("/", 1)[0]

    query = urlencode({"ps_mode": MODIFY_MODE, "ps_fuid": str(fuid)})
    return urlunsplit((parts.scheme, parts.netloc, f"{base_dir}/{MODIFY_PAGE}", query, ""))


def open_modify_popup(page, fuid: str, *, list_url: str = "", progress: ProgressFn | None = None):
    """행의 [수집조건수정] 을 눌러 팝업창을 얻는다. 실패 시 팝업 URL 직접 오픈."""
    fuid = str(fuid or "").strip()

    if fuid:
        try:
            with page.expect_popup(timeout=T_POPUP) as popup_info:
                page.locator(f"a[onclick*=\"modify_filter('{fuid}')\"]").first.click(timeout=T_CLICK)
            popup = popup_info.value
            _log(progress, f"  수집조건수정 팝업 열림 (fuid={fuid})")
            return popup
        except Exception:
            pass

    url = build_modify_url(list_url, fuid) if fuid else ""
    if not url:
        _log(progress, f"오류: 수집조건수정 팝업을 열지 못했습니다 (fuid={fuid or '?'})", major=True)
        return None

    try:
        popup = page.context.new_page()
        popup.goto(url, wait_until="domcontentloaded", timeout=T_POPUP)
        _log(progress, f"  수집조건수정 직접 열기 (fuid={fuid})")
        return popup
    except Exception as e:  # noqa: BLE001
        _log(progress, f"오류: 팝업 열기 실패 · {e}", major=True)
        return None


def wait_translate_select(popup, *, progress: ProgressFn | None = None) -> bool:
    """팝업의 번역옵션 드롭다운 등장 대기 — 0.3초 단위. 뜨는 즉시 진행."""
    sel = f'select[name="{TRANSLATE_SELECT_NAME}"]'
    for attempt in range(1, POPUP_TRIES + 1):
        try:
            popup.wait_for_selector(sel, timeout=T_POPUP)
            return True
        except Exception:
            if attempt == 1:
                _log(progress, f"  팝업 렌더 {T_POPUP}ms 초과 — 재시도")
    return False


def click_save_in_popup(popup, *, progress: ProgressFn | None = None) -> bool:
    """팝업 하단 [저장하기] (onclick=set_save()) 클릭."""
    for sel in SAVE_SELECTORS:
        try:
            loc = popup.locator(sel).first
            if loc.count() == 0:
                continue
            loc.click(timeout=T_CLICK)
            _log(progress, "  저장하기 클릭")
            return True
        except Exception:
            continue

    try:  # 최후: set_save() 직접 호출
        popup.evaluate("() => { if (typeof set_save === 'function') set_save(); }")
        _log(progress, "  저장하기 (set_save 직접 호출)")
        return True
    except Exception as e:  # noqa: BLE001
        _log(progress, f"오류: 저장하기 클릭 실패 · {e}", major=True)
        return False


def click_close_in_popup(popup, *, progress: ProgressFn | None = None) -> bool:
    """저장하기 **바로 옆 [닫기]**(onclick=window.close()) 를 눌러 즉시 종료."""
    for sel in CLOSE_SELECTORS:
        try:
            loc = popup.locator(sel).first
            if loc.count() == 0:
                continue
            loc.click(timeout=T_CLICK)
            _log(progress, "  닫기 클릭")
            return True
        except Exception:
            continue
    try:
        popup.evaluate("() => window.close()")
        _log(progress, "  닫기 (window.close 직접 호출)")
        return True
    except Exception:
        return False


def close_popup(popup, *, timeout_ms: int = T_CLOSE, progress: ProgressFn | None = None) -> bool:
    """[닫기] 로 팝업을 즉시 종료. 그래도 남아 있으면 강제로 닫는다."""
    click_close_in_popup(popup, progress=progress)

    closed = False
    try:
        popup.wait_for_event("close", timeout=timeout_ms)
        closed = True
    except Exception:
        closed = False

    if not closed:
        try:
            if not popup.is_closed():
                popup.close()
                closed = True
        except Exception:
            pass
    return closed


def apply_option_in_popup(
    page,
    fuid: str,
    option: str,
    *,
    list_url: str = "",
    progress: ProgressFn | None = None,
) -> bool:
    """수집조건수정 → 팝업 → 번역옵션 선택 → 저장하기 → 모달 닫기."""
    popup = open_modify_popup(page, fuid, list_url=list_url, progress=progress)
    if popup is None:
        return False

    try:
        popup.on("dialog", lambda d: d.accept())
    except Exception:
        pass

    try:
        if not wait_translate_select(popup, progress=progress):
            _log(progress, "  경고: 번역옵션 드롭다운 지연 — 그대로 시도", major=True)

        if not set_translate_option(popup, option, progress=progress):
            return False
        if not click_save_in_popup(popup, progress=progress):
            return False
        close_popup(popup, progress=progress)
        return True
    finally:
        try:
            if not popup.is_closed():
                popup.close()
        except Exception:
            pass


# ── 실행 ─────────────────────────────────────────────────────────


def _open_mango(pw, mango_url: str, progress: ProgressFn | None):
    """Chrome 연결 + 목록 화면. 빠른 경로(goto) 실패 시에만 P3 절차를 쓴다."""
    import collect as p2  # noqa: WPS433

    _browser, page = p2.connect_browser(pw)
    url = (mango_url or "").strip() or DEFAULT_LIST_URL

    try:  # 빠른 경로 — 목록 URL 직접 이동 후 검색줄 확인
        page.goto(url, wait_until="domcontentloaded", timeout=T_NAV * 2)
        page.wait_for_selector(f'select[name="{SITE_SELECT_NAME}"]', timeout=T_FIELD)
        _log(progress, "망고 목록 화면 (빠른 이동)", major=True)
        return page, url
    except Exception:
        pass

    page = p3.navigate_mango_url(page, url, progress=progress, p2=p2)
    return page, url


def fetch_translate_options(
    *,
    mango_url: str = "",
    progress: ProgressFn | None = None,
) -> tuple[list[str], list[str]]:
    """망고에서 (번역옵션, 수집사이트) 목록을 읽어온다 (보드 리스트박스용)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        _log(progress, f"의존성 로드 실패: {e}", major=True)
        return [], []

    options: list[str] = []
    sites: list[str] = []
    try:
        with sync_playwright() as pw:
            page, url = _open_mango(pw, mango_url, progress)

            sites = read_site_options(page)
            if sites:
                _log(progress, f"수집사이트 {len(sites)}개: {sites}", major=True)
                save_cached_sites(sites)
            else:
                _log(progress, "수집사이트 드롭다운 미검출", major=True)

            rows = [r for r in p3.list_demango_rows(page) if r.get("hasEdit")]
            if not rows:
                _log(progress, "필터 목록에서 수정 가능한 행이 없습니다.", major=True)
                return [], sites

            first = rows[0]
            popup = open_modify_popup(
                page,
                str(first.get("fuid") or "").strip(),
                list_url=url,
                progress=progress,
            )
            if popup is None:
                _log(progress, "수집조건수정 팝업을 열지 못했습니다.", major=True)
                return [], sites

            try:
                wait_translate_select(popup, progress=progress)
                control = detect_translate_control(popup)
                if control is None:
                    _log(progress, "번역옵션 컨트롤 미검출", major=True)
                else:
                    options = list(control.options)
                    _log(progress, f"번역옵션 {len(options)}개: {options}", major=True)
            finally:
                try:
                    if not popup.is_closed():
                        popup.close()
                except Exception:
                    pass
    except Exception as e:  # noqa: BLE001
        _log(progress, f"옵션 읽기 오류: {e}", major=True)
        return [], sites

    if options:
        save_cached_options(options)
    return options, sites


def run_update_collect_option(
    translate_option: str,
    *,
    collect_site: str = "",
    mango_url: str = "",
    progress: ProgressFn | None = None,
) -> RunResult:
    option = str(translate_option or "").strip()
    if not option:
        return RunResult(ok=False, errors=["번역옵션을 리스트에서 선택하세요."])
    site = str(collect_site or "").strip()

    result = RunResult(ok=False)
    clear_stop_flag()
    old_stop = _patch_p3_stop()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        _restore_p3_stop(old_stop)
        result.errors.append(f"의존성 로드 실패: {e}")
        _log(progress, result.errors[0], major=True)
        return result

    _log(progress, f"번역옵션: {option}", major=True)
    _log(progress, f"수집사이트: {site or SITE_ALL_LABEL}", major=True)

    try:
        with sync_playwright() as pw:
            page, url = _open_mango(pw, mango_url, progress)

            page = pick_list_page(page, progress=progress)
            if not apply_site_filter(page, site, progress=progress):
                result.errors.append(f"수집사이트 적용 실패 · {site}")
                return result

            rows = p3.list_demango_rows(page)
            editable = [r for r in rows if r.get("hasEdit")]
            result.total_rows = len(editable)
            if not editable:
                result.errors.append("필터 목록에서 수정 가능한 행이 없습니다.")
                _log(progress, result.errors[0], major=True)
                return result

            _log(progress, f"필터 {len(editable)}행 — 순차 수집조건수정", major=True)

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

                if not apply_option_in_popup(
                    page,
                    d_fuid or str(row_idx),
                    option,
                    list_url=url,
                    progress=progress,
                ):
                    result.failed += 1
                    result.errors.append(f"수집조건수정 실패 · 필터={d_filter}")
                    continue

                result.updated += 1
                _log(progress, f"  변경 완료 · 번역옵션={option}", major=True)
                time.sleep(GAP_ROW)

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
    parser = argparse.ArgumentParser(description="P3_필터단위_수집조건수정")
    parser.add_argument("--translate-option", default="", help="번역옵션 (리스트 선택값)")
    parser.add_argument(
        "--collect-site",
        default="",
        help=f"수집사이트 (리스트 선택값 · 비우면 {SITE_ALL_LABEL})",
    )
    parser.add_argument(
        "--list-options",
        action="store_true",
        help="망고에서 번역옵션·수집사이트 목록만 읽어 출력",
    )
    parser.add_argument(
        "--mango-url", default="", help=f"필터 목록 URL (기본={DEFAULT_LIST_URL})"
    )
    args = parser.parse_args(argv)

    if args.list_options:
        options, sites = fetch_translate_options(mango_url=args.mango_url)
        if not options and not sites:
            print("[오류] 목록을 읽지 못했습니다.", flush=True)
            return 1
        print(format_option_lines(options, sites), flush=True)
        return 0

    if not args.translate_option.strip():
        parser.error("--translate-option 또는 --list-options 가 필요합니다.")

    result = run_update_collect_option(
        args.translate_option,
        collect_site=args.collect_site,
        mango_url=args.mango_url,
    )
    if result.errors:
        for e in result.errors:
            print(f"[오류] {e}", flush=True)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
