"""P2(collect.py) stdout ↔ 보드 main/sub 그리드 프로토콜 (tk 불필요, 테스트 가능).

collect.py 는 화면에 보여야 하는 줄만 다음 마커로 표준출력에 보낸다:
  ##META##<field>##<value>       main 상단 고정 항목(총건수·완료·수집필드·URL)
  ##META##진행##<n>              화면 미표시 — 카테고리URL목록 진행행 적색용
  ##MAIN##<seq>##<n>##<msg>      1~13단계 (main 그리드, 발생마다 새 seq)
  ##SUB##<seq>##<msg>            그 발생(seq)에 딸린 추가정보 (sub 그리드)
  ##SUBSHOT##<seq>##<path>##<label>   그 발생(seq)에 딸린 스크린샷

이 마커가 아닌 줄은 화면에 출력하지 않는다(요건: main엔 13단계만·
sub엔 그 추가정보만, 그 외 잡다한 로그는 안 보임).
"""

from __future__ import annotations

import re
import time

# ★요건(2026-08-08): 완료건→완료, 순번 삭제. 총건수는 목차행 제외 계산.
META_FIELDS: tuple[str, ...] = (
    "총건수",
    "완료",
    "수집 필드",
    "카테고리 URL",
)

# 화면 META 줄에는 안 나오고, 진행행 적색 표시에만 쓰는 내부 필드
META_INTERNAL_FIELDS: frozenset[str] = frozenset({"진행", "순번"})

# main 상단 META 1줄 표시용 구분자
META_LINE_SEP = " | "


def format_meta_line(values: dict[str, str]) -> str:
    """엑셀 진행 정보 항목을 한 줄 문자열로 합친다 (보드 main 상단)."""
    parts: list[str] = []
    for field in META_FIELDS:
        val = str(values.get(field, "") or "").strip()
        parts.append(f"{field} {val}" if val else field)
    return META_LINE_SEP.join(parts)

META_RE = re.compile(r"^##META##([^#]+)##(.*)$")
MAIN_RE = re.compile(r"^##MAIN##(\d+)##(\d+)##(.*)$")
SUB_RE = re.compile(r"^##SUB##(\d+)##(.*)$")
SUBSHOT_RE = re.compile(r"^##SUBSHOT##(\d+)##(.*?)##(.*)$")

# 단계번호 → 색상태그
# 0=엑셀진행(오렌지 meta), 1=로그인, 2·13=초기화, 9~11=저장, 12=완료
STEP_TAG: dict[int, str] = {
    0: "meta",
    1: "login",
    2: "init",
    13: "init",
    9: "save",
    10: "save",
    11: "save",
    12: "done",
}

# P3(update_filters.py) 1~7단계 + 오류/완료/중단(90/91/92) → 색상태그
# (P2와 동일 MAIN/SUB 그리드 프로토콜을 공유하지만 단계 의미가 달라 별도 매핑)
STEP_TAG_P3: dict[int, str] = {
    1: "login",
    5: "save",
    6: "save",
    90: "err",
    91: "done",
    92: "stop",
}


def strip_timestamp(text: str) -> tuple[str, str]:
    """"[HH:MM:SS] 또는 [HH:MM:SS~HH:MM:SS] 나머지" → (시각, 나머지).

    접두 없으면 현재시각을 채운다.
    """
    m = re.match(
        r"^\[(\d{2}:\d{2}:\d{2}(?:~\d{2}:\d{2}:\d{2})?)\]\s*(.*)$",
        text or "",
    )
    if m:
        return m.group(1), m.group(2)
    return time.strftime("%H:%M:%S"), (text or "")


def sub_time_range(start: str, end: str | None) -> str:
    """sub 시각 — 현단계 MAIN 진입~다음 MAIN 진입."""
    if not start:
        return end or time.strftime("%H:%M:%S")
    if end and end != start:
        return f"{start}~{end}"
    return start


def parse_line(text: str) -> tuple | None:
    """마커 있는 줄만 해석. 없으면 None(화면에 출력 안 함).

    반환:
      ("meta", field, value)
      ("main", seq, n, msg)
      ("sub", seq, msg)
      ("subshot", seq, path, label)
    """
    raw = text or ""
    m = META_RE.match(raw)
    if m:
        return ("meta", m.group(1), m.group(2))
    m = MAIN_RE.match(raw)
    if m:
        return ("main", int(m.group(1)), int(m.group(2)), m.group(3))
    m = SUB_RE.match(raw)
    if m:
        return ("sub", int(m.group(1)), m.group(2))
    m = SUBSHOT_RE.match(raw)
    if m:
        return ("subshot", int(m.group(1)), m.group(2), m.group(3))
    return None


def step_tag(n: int) -> str:
    return STEP_TAG.get(n, "normal")


def step_tag_p3(n: int) -> str:
    return STEP_TAG_P3.get(n, "normal")


# P3 MAIN 그리드 "단계" 열 표시용 — 90/91/92 숫자 코드를 한글 라벨로 (1~7은 숫자 그대로)
STEP_LABEL_P3: dict[int, str] = {90: "오류", 91: "완료", 92: "중단"}


def step_label_p3(n: int) -> str | int:
    return STEP_LABEL_P3.get(n, n)


# 단계번호로는 성공/실패가 구분되지 않으므로(예: 5)저장 성공·5)저장 실패 모두 n=5),
# 실패 문구가 있으면 MAIN 행을 적색으로 표시한다 — 오류 단계를 한눈에 찾기 위함.
P3_FAIL_HINTS: tuple[str, ...] = (
    "실패",
    "중단",
    "오류",
    "not found",
    "미검출",
    "시간초과",
)


def main_tag_p3(n: int, msg: str) -> str:
    if any(hint in (msg or "") for hint in P3_FAIL_HINTS):
        return "err"
    return step_tag_p3(n)


# 메시지 앞에 이 표식이 붙어 오면 그 행을 적색으로 구분 표시한다.
# (그리드 셀 안에서 일부 글자만 색을 바꿀 수 없으므로 행 단위로 구분한다 —
#  예: 동일 URL 행이 2개 이상일 때 "몇 개"·URL 을 별도 적색 행으로 표출)
RED_PREFIX = "##RED##"


def split_red(msg: str) -> tuple[bool, str]:
    """("적색 표시 여부", 표식 제거한 메시지)."""
    text = msg or ""
    if text.startswith(RED_PREFIX):
        return True, text[len(RED_PREFIX):].lstrip()
    return False, text
