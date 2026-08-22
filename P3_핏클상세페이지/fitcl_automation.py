"""FitCL(fitcl.ai) 브라우저 자동화 — 모델컷·디테일컷 추출."""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from playwright.sync_api import Page, TimeoutError as PWTimeout

ProgressFn = Callable[[str], None]

DEFAULT_FITCL_URL = "https://fitcl.ai/"
FITCL_APP_HINTS = ("app.fitcl", "studio.fitcl", "fitcl.ai/app", "fitcl.ai/studio")

# UI 셀렉터 — fitcl.ai 앱 화면 변경 시 이 파일만 수정
SELECTORS = {
    "file_input": "input[type='file']",
    "model_card": "[data-model-name], [data-testid*='model'], .model-card, [class*='model']",
    "pose_card": "[data-pose-name], [data-testid*='pose'], .pose-card, [class*='pose']",
    "generate_btn": (
        "button:has-text('생성'), button:has-text('AI 생성'), "
        "button:has-text('만들기'), button:has-text('Generate')"
    ),
    "download_btn": (
        "button:has-text('다운로드'), a:has-text('다운로드'), "
        "button:has-text('Download'), [download]"
    ),
    "detail_section": (
        "[data-section='detail'], :has-text('디테일'), :has-text('상세컷'), "
        ":has-text('항공샷')"
    ),
}


def _log(progress: ProgressFn | None, msg: str, *, major: bool = False) -> None:
    line = f"##MAIN##{msg}" if major else msg
    print(line, flush=True)
    if progress:
        progress(line)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def is_fitcl_page(page: Page) -> bool:
    try:
        url = (page.url or "").lower()
    except Exception:
        return False
    if "fitcl" in url:
        return True
    try:
        title = (page.title() or "").lower()
        return "fitcl" in title or "핏클" in title
    except Exception:
        return False


def navigate_fitcl(page: Page, url: str, *, progress: ProgressFn | None = None) -> Page:
    target = (url or "").strip() or DEFAULT_FITCL_URL
    _log(progress, f"FitCL 접속: {target}", major=True)
    page.goto(target, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(800)
    for p in page.context.pages:
        if is_fitcl_page(p):
            try:
                p.bring_to_front()
            except Exception:
                pass
            return p
    return page


def _click_by_text(page: Page, text: str, *, timeout_ms: int = 8_000) -> bool:
    want = _norm(text)
    if not want:
        return False
    try:
        loc = page.get_by_text(want, exact=False).first
        if loc.count() > 0:
            loc.click(timeout=timeout_ms)
            return True
    except Exception:
        pass
    try:
        loc = page.locator(f"[title*='{want}'], [aria-label*='{want}'], [alt*='{want}']").first
        if loc.count() > 0:
            loc.click(timeout=timeout_ms)
            return True
    except Exception:
        pass
    return False


def upload_product_image(page: Page, image_path: Path, *, progress: ProgressFn | None = None) -> bool:
    path = Path(image_path)
    if not path.is_file():
        _log(progress, f"오류: 소싱상품 파일 없음 — {path}", major=True)
        return False
    _log(progress, f"소싱상품 업로드: {path.name}", major=True)
    try:
        inputs = page.locator(SELECTORS["file_input"])
        if inputs.count() == 0:
            _log(progress, "파일 입력칸 미검출 — 업로드 버튼 탐색", major=True)
            for label in ("업로드", "사진 업로드", "의류 사진", "이미지 업로드"):
                if _click_by_text(page, label):
                    page.wait_for_timeout(500)
                    break
        inputs = page.locator(SELECTORS["file_input"])
        if inputs.count() == 0:
            _log(progress, "오류: FitCL 업로드 입력칸을 찾지 못했습니다.", major=True)
            return False
        inputs.first.set_input_files(str(path.resolve()))
        page.wait_for_timeout(1_500)
        return True
    except Exception as e:
        _log(progress, f"업로드 실패: {e}", major=True)
        return False


def select_model(page: Page, model_name: str, *, progress: ProgressFn | None = None) -> bool:
    name = _norm(model_name)
    _log(progress, f"사진모델 선택: {name}", major=True)
    if _click_by_text(page, name):
        page.wait_for_timeout(800)
        return True
    try:
        cards = page.locator(SELECTORS["model_card"])
        for i in range(min(cards.count(), 120)):
            card = cards.nth(i)
            try:
                txt = _norm(card.inner_text(timeout=500))
                alt = _norm(card.get_attribute("alt") or "")
                data = _norm(card.get_attribute("data-model-name") or "")
                if name in txt or name in alt or name in data:
                    card.click(timeout=5_000)
                    page.wait_for_timeout(800)
                    return True
            except Exception:
                continue
    except Exception:
        pass
    _log(progress, f"오류: 모델 '{name}' 미검출 — FitCL 로그인·화면 확인", major=True)
    return False


def select_pose(page: Page, pose_name: str, *, progress: ProgressFn | None = None) -> bool:
    name = _norm(pose_name)
    _log(progress, f"  포즈 선택: {name}")
    if _click_by_text(page, name):
        page.wait_for_timeout(600)
        return True
    try:
        cards = page.locator(SELECTORS["pose_card"])
        for i in range(min(cards.count(), 80)):
            card = cards.nth(i)
            try:
                txt = _norm(card.inner_text(timeout=400))
                data = _norm(card.get_attribute("data-pose-name") or "")
                if name in txt or name in data:
                    card.click(timeout=5_000)
                    page.wait_for_timeout(600)
                    return True
            except Exception:
                continue
    except Exception:
        pass
    _log(progress, f"  포즈 '{name}' 미검출", major=True)
    return False


def click_generate(page: Page, *, progress: ProgressFn | None = None) -> bool:
    try:
        btn = page.locator(SELECTORS["generate_btn"]).first
        if btn.count() > 0:
            btn.click(timeout=8_000)
            return True
    except Exception:
        pass
    for label in ("AI 생성", "생성하기", "생성", "만들기"):
        if _click_by_text(page, label):
            return True
    _log(progress, "오류: 생성 버튼 미검출", major=True)
    return False


def wait_generation_done(page: Page, *, timeout_sec: int = 300) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            loading = page.locator(
                ":has-text('생성 중'), :has-text('처리 중'), :has-text('로딩'), "
                "[class*='loading'], [class*='spinner']"
            )
            if loading.count() == 0:
                imgs = page.locator("img[src*='blob:'], img[src*='http'], canvas")
                if imgs.count() > 0:
                    return True
        except Exception:
            pass
        time.sleep(2)
    return False


def save_result_image(
    page: Page,
    dest: Path,
    *,
    progress: ProgressFn | None = None,
) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        btn = page.locator(SELECTORS["download_btn"]).first
        if btn.count() > 0:
            with page.expect_download(timeout=60_000) as dl_info:
                btn.click(timeout=10_000)
            download = dl_info.value
            download.save_as(str(dest))
            _log(progress, f"  저장: {dest.name}")
            return dest.is_file()
    except Exception:
        pass
    try:
        img = page.locator(
            "img[src*='blob:'], img[src*='cdn'], img[src*='fitcl'], "
            "canvas, [class*='result'] img"
        ).last
        if img.count() > 0:
            img.screenshot(path=str(dest), timeout=15_000)
            _log(progress, f"  캡처 저장: {dest.name}")
            return dest.is_file()
    except Exception as e:
        _log(progress, f"  이미지 저장 실패: {e}", major=True)
    return False


def extract_detail_cuts(
    page: Page,
    output_dir: Path,
    count: int = 5,
    *,
    progress: ProgressFn | None = None,
) -> int:
    """상품 디테일컷 추출 (최대 count장)."""
    saved = 0
    detail_dir = output_dir / "detail"
    detail_dir.mkdir(parents=True, exist_ok=True)
    _log(progress, f"디테일컷 추출 시작 (목표 {count}장)", major=True)

    for label in ("디테일", "상세컷", "항공샷", "디테일컷"):
        _click_by_text(page, label)
        page.wait_for_timeout(500)

    try:
        imgs = page.locator(
            "img[src*='http'], img[src*='blob:'], [class*='detail'] img, "
            "[class*='product'] img"
        )
        n = min(imgs.count(), count * 3)
        seen: set[str] = set()
        for i in range(n):
            if saved >= count:
                break
            img = imgs.nth(i)
            try:
                src = (img.get_attribute("src") or "").strip()
                if not src or src in seen:
                    continue
                box = img.bounding_box()
                if not box or box.get("width", 0) < 80:
                    continue
                seen.add(src)
                dest = detail_dir / f"detail_{saved + 1:02d}.png"
                img.screenshot(path=str(dest), timeout=10_000)
                saved += 1
                _log(progress, f"  디테일컷 {saved}/{count}: {dest.name}")
            except Exception:
                continue
    except Exception as e:
        _log(progress, f"디테일컷 추출 오류: {e}", major=True)

    if saved < count:
        _log(
            progress,
            f"디테일컷 {saved}/{count}장만 확보 — FitCL 상세페이지·디테일 메뉴 확인",
            major=True,
        )
    return saved
