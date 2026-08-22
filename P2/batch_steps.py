"""상품수집 BATCH — 1~13단계 순차 흐름 (딴 길로 빠지지 않음).

로그인(1)은 main에서 1회.
최초: 2 초기화 후 3→…→12.
이후(14항): **3 ~ 13 반복**
  = 3→4→5→6→7→8→9→10→11→12→13(초기화) → 다시 3 …

실패 최대 원인: 6·11·12 확인 없이 다음 단계 진행.

★실행로그 규칙: 화면(표준출력·보드)에는 오직 1~13단계 줄만 보인다
(ctx.step() 로만 출력됨). 그 외 세부 진단은 ctx.info()로 파일에만 남긴다.
단계 내 입력 필드값은 그 단계 아래 한 단 더 들여써서 별도 줄로 출력한다.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page

    import collect as C_mod


def run_row_batch(page: "Page", row: dict, ctx: "C_mod.RunCtx") -> None:
    """한 입력 행을 2→12 단계로만 순차 실행."""
    import collect as C

    rn = int(row["row"])
    label = str(row.get("label") or "").strip()
    raw_url = str(row.get("url") or "").strip()
    url = C.normalize_url(raw_url)
    save_count = max(3, int(ctx.save_count))

    # 저장 팝업 대기 중 초기화(2/13) 진입 금지
    if getattr(ctx, "save_awaiting_popup", False):
        raise RuntimeError(
            f"#{rn} 저장하기 후 팝업모달 대기 미완료 — "
            "초기화 진행 불가 (11·12항 먼저)"
        )

    ctx.info(
        f"==== BATCH 시작 엑셀{rn}행 | {label} | {raw_url} | 저장수={save_count} ===="
    )

    # ── 2(최초)/13(다음행) 초기화 ──
    step02_init(page, ctx, rn)

    # ── 3~6. URL검색 (실패 시 같은 구간만 최대 N회) ──
    search_ok = False
    last_state = "unknown"
    last_count = 0
    max_search = max(1, int(C.SEARCH_MAX_TRIES))
    for try_i in range(1, max_search + 1):
        ctx.check_budget(f"BATCH 3~6 시도 {try_i}/{max_search}")
        ctx.info(f"---- 검색시도 {try_i}/{max_search} ----")
        step03_input_url(page, ctx, rn, url, raw_url, try_i)
        step04_click_search(page, ctx, rn)
        step05_popup_open(page, ctx, rn, try_i)
        step06_popup_close(page, ctx, rn, try_i)
        # ★삭제(2026-08-08 사용자 지시): 아래 6→7 불필요 액션 전부 제거/주석
        #   ctx.info("  (6→7) 망고 검색결과 안정화")
        #   wait_mango_search_settle(...) / prepare_product_view_for_shot(...)
        #   ctx.info(f"  검색결과 준비 (상품이미지 약 {N}개)")
        #   ctx.shot(page, "01_results_ready", rn)  # [샷] 1. 검색 결과 준비
        # 팝업 닫힘(6항) 후 무결과 여부만 짧게 보고 즉시 7항.
        ok, last_state, last_count = step06b_quick_check(
            page, ctx, rn, label, url, try_i, max_search
        )
        if ok:
            search_ok = True
            break

    if not search_ok:
        raise RuntimeError(
            f"#{rn} 망고 검색결과 확인 실패 "
            f"(state={last_state}, hint={last_count})"
        )

    # ── 7. 저장범위 (6항 직후 즉시) ──
    step07_save_range(page, ctx, rn)

    # ★요건: 9·10·11 합산 180초 이내 — 초과 시 다음 입력으로.
    ctx.row_deadline = time.time() + float(C.SAVE_PHASE_BUDGET_SEC)
    ctx.save_phase_deadline = time.time() + float(C.SAVE_PHASE_BUDGET_SEC)

    # ── 8. 필터 입력(저장상품수는 원래 세팅값 유지·미변경) ──
    effective_count = step08_filter_count(page, ctx, rn, label, save_count)

    # ── 9~12. 저장하기 → 팝업열림 → 닫힘 → 건수 (저장상품수 원래값 기준) ──
    step09_to_12_db_save(page, ctx, rn, effective_count)

    if not (
        ctx.server_save_ok
        and getattr(ctx, "search_popup_closed", False)
        and getattr(ctx, "save_popup_closed", False)
        and getattr(ctx, "save_count_logged", False)
    ):
        raise RuntimeError(
            f"#{rn} BATCH 미완료 — 6·11·12항 확인 전 종료 불가"
        )

    ctx.info(
        f"==== BATCH 완료 엑셀{rn}행 "
        f"(14항: 다음 행은 13 초기화 후 3~13 반복) ===="
    )


# ---------------------------------------------------------------------------
# 단계 구현 (각 함수 = 한 단계, 성공 시에만 return)
# ---------------------------------------------------------------------------


def step02_init(page, ctx, rn: int) -> None:
    """★상품수집 필드 초기화는 언제나 2단계 — 두 번째 이후 행이라도
    "13"으로 표시하지 않는다(사용자 지적: 초기화 단계는 항상 2단계).

    ★불필요한 고정 대기 없음 — reset_to_bulk_menu() 내부에서 URL검색
    버튼이 실제로 보일 때까지만 기다리고, 그 후 3항으로 곧바로 진행.

    ★2026-08-08 수정: 1번째 입력은 main()의 ensure_ready_page()가 로그인
    직후 이미 실제 메뉴클릭으로 대량수집 화면에 도착시켜 두므로, 여기서는
    "이미 도착해 있음"을 확인만 하고 지나간다(빠름). 반면 2번째 이후
    입력은 이 호출이 초기화의 전부였는데, 직전 행 상태에 따라 실제
    메뉴클릭을 하기도/안 하기도 해서 1번째와 다른 동작이 되고 필드가
    제대로 초기화되지 않는 문제가 있었다(사용자 지적). 2번째 이후는
    항상 force=True로 호출해 1번째와 동일하게 실제 메뉴클릭(서버
    재요청)을 매번 수행하도록 통일한다.
    """
    import collect as C

    ctx.step(2, "상품수집 필드 초기화 : 상품데이터수집 → 대량데이터수집")
    force_real_click = getattr(ctx, "input_ordinal", 1) > 1
    C.reset_to_bulk_menu(page, force=force_real_click)
    ctx.shot(page, "00_init_bulk", rn)


def step03_input_url(
    page, ctx, rn: int, url: str, raw_url: str, try_i: int
) -> None:
    import collect as C

    ctx.step(3, "상품수집 URL정보 입력")
    ctx.info(f"최종 카테고리 URL주소: {url}")
    if url != raw_url.strip():
        ctx.info(f"  [정보] 프로토콜 보정됨: {url}")
    target = C.url_input(page)
    C.type_into(page, target, url)
    actual = ""
    try:
        actual = target.input_value()
    except Exception:
        pass
    ctx.info(f"  입력칸 최종 값: {actual!r}")
    if actual.strip() != url.strip():
        raise RuntimeError(f"URL 입력 불일치 — 기대 {url!r} / 실제 {actual!r}")
    if try_i == 1:
        ctx.shot(page, "01_url_filled", rn)


def step04_click_search(page, ctx, rn: int) -> None:
    import collect as C

    ctx.step(4, "상품수집 시작 : URL상품검색하기 클릭")
    C.click_it(C.url_search_button(page))


def step05_popup_open(page, ctx, rn: int, try_i: int) -> None:
    import collect as C

    opened = C.wait_popup_open(page, grace_sec=15.0)
    if not opened:
        ctx.info("  키보드 재시도 (Enter)")
        try:
            C.url_search_button(page).first.focus()
            page.keyboard.press("Enter")
        except Exception:
            pass
        opened = C.wait_popup_open(page, grace_sec=10.0)
    if not opened:
        ctx.shot(page, "01_popup_missing", rn)
        raise RuntimeError(f"#{rn} 4항 클릭 후 검색 팝업이 열리지 않음 (5항 실패)")

    popup = opened[0]
    try:
        popup.bring_to_front()
    except Exception:
        pass
    try:
        imgs = C.prepare_product_view_for_shot(popup, min_images=2)
    except Exception as e:
        ctx.info(f"  [경고] 팝업 상품이미지 대기 실패: {e}")
        imgs = 0
    ctx.search_popup_seen = True
    ctx.search_popup_closed = False
    ctx.step(5, "상품수집 실행 : 검색 팝업 모달 열림 (임시메모리 적재 중)")
    ctx.info(f"  상품이미지 약 {imgs}개")
    if try_i == 1:
        ctx.shot(popup, "01_popup_opened", rn)


def step06_popup_close(page, ctx, rn: int, try_i: int) -> None:
    import collect as C

    C.wait_popups_close(page)
    if C.popups(page):
        raise TimeoutError(
            f"#{rn} 검색 팝업모달이 닫히지 않음 (6항 미확인) — 7항 진행 불가"
        )
    ctx.search_popup_closed = True
    try:
        page.bring_to_front()
    except Exception:
        pass
    ctx.step(6, "상품수집 종료 : 검색 팝업 닫기-확인 (임시메모리 보관 완료)")
    if try_i == 1:
        ctx.shot(page, "01_popup_closed", rn)


def step06b_quick_check(
    page, ctx, rn: int, label: str, url: str, try_i: int, max_search: int
) -> tuple[bool, str, int]:
    """6항 직후 결과 판별만 — 긴 안정화 대기·이미지준비·결과샷 없음.

    ★요건(2026-08-08): 6→7 구간의 불필요 액션(긴 settle / 이미지준비 /
    결과샷)을 전부 제거. 팝업 닫힘 후 무결과·상품유무만 짧게 확인.
    """
    import collect as C

    # 로딩이 잠깐 남아있으면 최대 3초만 기다림(긴 안정화 루프 없음)
    end = time.time() + 3.0
    while time.time() < end and C.is_mango_loading(page):
        page.wait_for_timeout(200)

    if C.is_mango_no_results(page):
        if try_i < max_search:
            page.wait_for_timeout(400)
            return False, "no_results", 0
        raise RuntimeError(
            f"#{rn} 더망고 자체 메세지: 검색결과가 없습니다.\n"
            f"  · 최종 카테고리명={label}\n"
            f"  · 최종 카테고리 URL주소={url}"
        )

    try:
        last_count = int(C.count_mango_result_products(page) or 0)
    except Exception:  # noqa: BLE001
        last_count = 0
    if last_count >= 1:
        return True, "products", last_count

    # 상품 카운트가 아직 0이어도 무결과 문구가 없으면 진행(화면 렌더 지연 허용)
    if not C.is_mango_no_results(page):
        return True, "unknown", last_count

    if try_i < max_search:
        page.wait_for_timeout(400)
        return False, "no_results", last_count
    raise RuntimeError(
        f"#{rn} 더망고 자체 메세지: 검색결과가 없습니다.\n"
        f"  · 최종 카테고리명={label}\n"
        f"  · 최종 카테고리 URL주소={url}"
    )


# 하위 호환 별칭 (테스트·옛 호출)
step06b_settle = step06b_quick_check


def step07_save_range(page, ctx, rn: int) -> None:
    """★요건: 6항 확인 후 7·8항은 단계별 딜레이 없이 즉시 수행 —
    9항 진입까지 소요시간 최소화. 모달이 뜨는 즉시(폴링 간격 최소) 진행,
    스크린샷용 이미지 대기는 fast=True로 최소화, 꼬리의 고정 대기 제거.
    """
    import collect as C

    C.click_it(C.save_all_button(page))
    end = time.time() + C.MODAL_WAIT_SEC
    while time.time() < end:
        if C.save_modal_visible(page):
            break
        page.wait_for_timeout(100)
    else:
        ctx.shot(page, "02_save_missing", rn)
        raise RuntimeError(f"#{rn} 7항 모두저장 후 상품저장설정 모달 미열림")
    try:
        imgs = C.prepare_product_view_for_shot(page, min_images=2, fast=True)
    except Exception as e:
        ctx.info(f"  [경고] 모달 상품이미지 대기 실패: {e}")
        imgs = 0
    ctx.step(7, "수집된 상품 저장범위 지정 : 검색된 상품 모두저장")
    ctx.info(f"  상품저장설정 모달 열림 (상품이미지 약 {imgs}개)")
    ctx.shot(page, "02_save_modal", rn)


def step08_filter_count(
    page, ctx, rn: int, label: str, save_count: int
) -> int:
    """8항 발표(step)·필드값(info)은 fill_save_modal_fields 내부에서 남긴다.

    ★요건: 검색필터명에만 엑셀 데이터를 입력하고, 저장상품수는 절대
    건드리지 않는다(원래 세팅값 유지). 반환값은 그 원래 세팅값(정수) —
    이후 9~12항의 저장건수 확인은 이 값을 기대값으로 쓴다.
    """
    import collect as C

    return C.fill_save_modal_fields(page, ctx, rn, label, save_count)


def step09_to_12_db_save(page, ctx, rn: int, save_count: int) -> None:
    """9 저장하기 → 10 팝업열림 → 11 닫힘확인 → 12 건수로그 (한 줄도 건너뛰지 않음).

    9~12항 각각의 화면 출력(ctx.step)은 run_save_submit_and_verify 내부에서
    실제로 그 단계가 확인된 시점에 남긴다(미리 다 찍지 않음).
    """
    import collect as C

    C.run_save_submit_and_verify(page, ctx, rn, save_count)
    if not ctx.server_save_ok:
        raise RuntimeError(
            f"#{rn} 9항 저장하기 실패 또는 10·11·12항 미완료 — "
            "저장하기 클릭→팝업열림→닫힘→건수로그 필수"
        )
