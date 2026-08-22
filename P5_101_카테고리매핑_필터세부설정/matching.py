"""
필터명 → 최적 카테고리 찾기 (요건 2026-08-22 14:26 명세 그대로).

필터명 해석
  `아름트리-무신사-남성-모자-버킷/사파리 햇`
    → 앞 2조각(브랜드-사이트)은 **무시**
    → 상위=남성 · 중위=모자 · 하위=[버킷햇, 버킷, 햇, 사파리]

찾는 순서
  1) 망고 단계수 == 엑셀 단계수  → 상위 → 중위 → 하위 로 단계별 대조
  2) 단계수가 다르면
     2-1) 상위가 있는 목록에서 (없으면 중위 목록에서)
            → 중위 일치 목록으로 좁히고 (없으면 하위로)
              → 하위 일치 목록에서 고른다
     2-2) 못 찾으면 중위 이름으로 전체 재검색
     2-3) 못 찾으면 하위 이름으로 전체 재검색
     2-4) 그래도 없으면 품목별 포괄 카테고리에서 찾는다
          의류 → 패션잡화 · 의류잡화 · 패션의류잡화
          신발 → 신발잡화 · 의류잡화 · 패션의류잡화
          선글라스/안경테/모자/햇/손수건/비니 → 의류잡화 · 패션의류잡화
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Sequence

# 필터명 앞부분(브랜드-사이트)은 무시
IGNORED_LEAD_SEGMENTS = 2

# 상위 카테고리 보조 후보 (요건 예시3)
TOP_FALLBACKS = ("패션잡화", "의류잡화", "패션의류잡화")

# 중위 동의어
MID_SYNONYMS: dict[str, tuple[str, ...]] = {
    "소품": ("소품", "잡화"),
    "잡화": ("잡화", "소품"),
    "모자": ("모자",),
}

# 품목별 포괄 카테고리 (2-4)
GENERIC_BY_KIND: dict[str, tuple[str, ...]] = {
    "의류": ("패션잡화", "의류잡화", "패션의류잡화"),
    "신발": ("신발잡화", "의류잡화", "패션의류잡화"),
    "잡화": ("의류잡화", "패션의류잡화"),
}
# ★"아우터" 하위 카테고리(다른 이름) — 필터명에 이 중 하나만 있어도 의류로 인식
OUTER_SUBTYPES = (
    "후드집업", "블루종", "라이더스", "슈트", "블레이저", "카디건",
    "경량패딩", "패딩베스트", "패딩", "사파리", "헌팅재킷", "트러커재킷",
    "스타디움재킷", "코치재킷", "트레이닝재킷", "아노락", "플리스", "뽀글이",
    "환절기코트", "베스트", "무스탕", "싱글코트", "더블코트", "숏패딩",
    "롱패딩", "헤비아우터",
    # ★실사례 — "맨투맨/후드" 필터가 "패딩" 계열로 새던 사고 (형제 품목 오매핑)
    "맨투맨", "후드", "다운점퍼", "점퍼", "패딩조끼",
)
# ★"바지" 하위 카테고리(다른 이름)
PANTS_SUBTYPES = (
    "데님팬츠", "트레이닝팬츠", "조거팬츠", "코튼팬츠", "슈트팬츠",
    "슬랙스", "숏팬츠", "레깅스", "점프슈트", "오버올", "기타하의",
)
CLOTHING_WORDS = (
    "의류", "티셔츠", "셔츠", "바지", "팬츠", "아우터", "코트", "자켓", "재킷", "니트",
    *OUTER_SUBTYPES, *PANTS_SUBTYPES,
)
SHOE_WORDS = (
    "신발", "슈즈", "운동화", "스니커즈", "구두", "부츠", "샌들", "슬리퍼",
    "활동화", "스포츠화", "워커",
    # ★신발 화면 "품목별" 하위 카테고리(다른 이름)
    "패딩신발", "퍼신발", "신발용품",
)
# ★규칙3: 필터명에 이 명칭이 있으면 **그 명칭이 있는 카테고리**에서만 고른다
ITEM_RULE_WORDS: tuple[str, ...] = ("의류", "잡화", "모자", "선글라스", "액세서리", "신발")

# ★규칙4(요건재정의 9): 의류는 이 상위 카테고리를 우선한다 (앞일수록 우선)
#   성별을 모를 때 기본 순서.
CLOTHING_PREFERRED: tuple[str, ...] = (
    "패션의류잡화",
    "패션의류",
    "남성패션의류",
    "여성패션의류",
    "남성의류",
    "여성의류",
)


def clothing_preferred_for(gender: str = "") -> tuple[str, ...]:
    """★요건재정의 9: "<성별>의류 > 패션의류 > 패션의류잡화" 순으로 우선.

    성별을 모르면 기존 순서(`CLOTHING_PREFERRED`)를 그대로 쓴다.
    """
    if not gender:
        return CLOTHING_PREFERRED
    gendered = f"{gender}의류"
    gendered_fashion = f"{gender}패션의류"
    out = [gendered, gendered_fashion, "패션의류", "패션의류잡화"]
    for extra in CLOTHING_PREFERRED:
        if extra not in out:
            out.append(extra)
    return tuple(out)

# ★품목 계열 — 계열이 다르면 서로 선택하지 않는다 (의류↔신발, 선글라스↔시계 …)
CLASS_WORDS: dict[str, tuple[str, ...]] = {
    "의류": (
        "의류", "패션의류", "상의", "하의", "아우터", "티셔츠", "셔츠", "니트", "코트",
        "자켓", "재킷", "팬츠", "바지", "청바지", "원피스", "스커트", "정장", "点퍼",
        *OUTER_SUBTYPES, *PANTS_SUBTYPES,
    ),
    "신발": (
        "신발", "슈즈", "운동화", "스니커즈", "구두", "부츠", "샌들", "슬리퍼",
        "활동화", "스포츠화", "워커", "신발잡화", "신발용품",
        # "패딩/퍼 신발" 처럼 앞에 의류 단어(패딩·퍼)가 붙는 신발 항목 —
        # 전체 문구로 등록해 class_of 의 '더 긴 일치 우선' 규칙이 적용되게 한다.
        "패딩/퍼신발", "패딩·퍼신발", "패딩신발", "퍼신발",
    ),
    "모자": (
        "모자", "캡", "비니", "버킷햇", "벙거지", "햇", "방한모",
        # ★모자 화면 하위 카테고리(다른 이름)
        "야구모자", "헌팅캡", "베레모", "페도라", "사파리햇", "트루퍼", "바라클라바",
        "기타모자",
    ),
    "선글라스": ("선글라스", "안경", "아이웨어", "안경테"),
    "시계": ("시계", "워치", "손목시계"),
    "가방": ("가방", "백팩", "크로스백", "토트백", "숄더백", "지갑"),
    "액세서리": ("액세서리", "주얼리", "목걸이", "귀걸이", "반지", "팔찌", "브로치"),
    # ★"속옷/홈웨어" 하위 카테고리(다른 이름)
    "속옷": ("속옷", "홈웨어", "여성속옷상의", "여성속옷하의", "여성속옷세트"),
    # ★"뷰티" 하위 카테고리(다른 이름) — 필터명에 이 중 하나만 있어도
    #   "뷰티" 계열로 인식해 의류·신발 등 다른 계열과 섞이지 않게 한다.
    "뷰티": (
        "뷰티", "화장품", "코스메틱",
        "스킨케어", "마스크팩", "베이스메이크업", "립메이크업", "아이메이크업",
        "메이크업", "네일", "프레그런스", "향수", "선케어",
        "클렌징", "필링", "헤어케어", "바디케어",
        "쉐이빙", "제모", "뷰티디바이스", "미용소품", "헬스", "푸드",
    ),
}
GENERIC_CLASS = "잡화"
GENERIC_CLASS_WORDS = ("잡화", "소품", "패션잡화", "의류잡화", "패션의류잡화")

ACCESSORY_WORDS = ("선글라스", "안경테", "모자", "햇", "손수건", "비니", "캡", "버킷", "바라클라바")

_SPLIT = re.compile(r"[\s/·,()\[\]|]+")

# 최근접 판단 보조 — 성별 · 소재 · 용도/활용
GENDER_WORDS = {
    "남성": ("남성", "남자", "맨즈", "men"),
    # ★"임부복" 처럼 '여성' 이란 글자가 없어도 여성 전용 카테고리인 말들을
    #   포함한다 — 없으면 남성 필터가 아무 남성 카테고리도 없을 때 이런
    #   카테고리를 '성별 무관'으로 보고 최근접 후보로 골라버린다(오매칭).
    "여성": (
        "여성", "여자", "우먼", "women", "woman", "ladies",
        "임부", "임산부", "마터니티", "maternity",
    ),
    "공용": ("공용", "유니섹스", "남녀"),
    "아동": ("아동", "키즈", "주니어", "베이비"),
}
MATERIAL_WORDS = (
    "가죽", "레더", "니트", "데님", "면", "코튼", "울", "린넨", "퍼", "메쉬",
    "고어텍스", "나일론", "폴리", "스웨이드", "캔버스", "실리콘", "메탈",
)
# 품목 동의어 — 필터명 표현과 마켓 카테고리 표현의 차이를 메운다
ITEM_SYNONYMS: dict[str, tuple[str, ...]] = {
    "비니": ("비니", "니트모자", "털모자", "방한모"),
    "바라클라바": ("바라클라바", "방한모", "발라클라바", "마스크모자"),
    "버킷햇": ("버킷햇", "벙거지", "버킷", "사파리햇"),
    "캡모자": ("캡모자", "볼캡", "야구모자", "캡"),
    "선글라스": ("선글라스", "썬글라스", "아이웨어"),
    "안경테": ("안경테", "안경", "아이웨어"),
    "스니커즈": ("스니커즈", "운동화", "캔버스화"),
    "슬리퍼": ("슬리퍼", "샌들", "쪼리"),
    "가방": ("가방", "백팩", "크로스백", "토트백"),
    "지갑": ("지갑", "카드지갑", "머니클립"),
    "목도리": ("목도리", "머플러", "스카프"),
    "장갑": ("장갑", "글러브", "핸드워머"),
    "양말": ("양말", "삭스"),
    "벨트": ("벨트", "허리띠"),
    "니트": ("니트", "스웨터", "가디건"),
    "티셔츠": ("티셔츠", "반팔", "긴팔", "티"),
    "바지": ("바지", "팬츠", "슬랙스", "청바지", "데님"),
    "코트": ("코트", "아우터", "자켓", "재킷", "점퍼"),
}

PURPOSE_WORDS = (
    "등산", "캠핑", "스포츠", "러닝", "골프", "수영", "요가", "낚시", "자전거",
    "웨딩", "정장", "캐주얼", "홈웨어", "방한", "여름", "겨울", "레인", "트레킹",
)


def normalize(text: str) -> str:
    return "".join(str(text or "").split()).lower()


def split_levels(path: str) -> list[str]:
    return [p.strip() for p in str(path or "").split(">") if p.strip()]


def leaf_of(path: str) -> str:
    """경로의 마지막 단계."""
    levels = split_levels(path)
    return levels[-1] if levels else ""


def _halves(word: str) -> list[str]:
    """`바라클라바` → [`바라`, `클라바`] (4자 이상일 때만)."""
    w = word.strip()
    if len(w) < 4:
        return []
    mid = len(w) // 2
    return [w[:mid], w[mid:]]


def segment_variants(raw: str) -> list[str]:
    """조각(중위·하위 등) 전개 — 원문 · 연속결합 · 각 토큰 · 첫+끝 결합 · 반쪽.

    ★요건재정의(2026-08-22): 중위·하위 모두 "여러 단어(슬래시·공백 구분)"로
    올 수 있다 — 예) 중위 "모자/기타잡화/신발" → 모자·기타잡화·신발·
    모자/기타잡화·기타잡화/신발·모자/기타잡화/신발. 연속된 토큰의 모든
    부분열(길이가 긴 것부터)을 결합해 만든 후보에, 기존 "첫+끝 결합"
    (버킷+햇 → 버킷햇)과 긴 토큰의 반쪽 분해를 더한다.
    """
    raw = str(raw or "").strip()
    if not raw:
        return []
    tokens = [t for t in _SPLIT.split(raw) if t]
    out: list[str] = []

    def add(v: str) -> None:
        v = v.strip()
        if v and v not in out:
            out.append(v)

    add(raw)
    add(raw.replace(" ", ""))

    n = len(tokens)
    for length in range(max(n - 1, 1), 0, -1):
        for start in range(0, n - length + 1):
            add("".join(tokens[start : start + length]))

    for tok in tokens:
        add(tok)

    if n > 1:
        add(tokens[0] + tokens[-1])  # 버킷/사파리 햇 → 버킷햇

    for tok in list(tokens) or [raw]:
        for half in _halves(tok):
            add(half)
    return out


def low_variants(raw: str) -> list[str]:
    """하위 조각 전개 — `segment_variants` 의 별칭 (하위호환)."""
    return segment_variants(raw)


@dataclass
class ParsedFilter:
    raw: str
    top: str = ""
    mid: str = ""
    lows: list[str] = field(default_factory=list)
    ignored: list[str] = field(default_factory=list)

    @property
    def tops(self) -> list[str]:
        out = [self.top] if self.top else []
        out += [t for t in TOP_FALLBACKS if t not in out]
        return out

    @property
    def mids(self) -> list[str]:
        """중위 후보 — 다중조각 전개(모자/잡화 → 모자·잡화·모자/잡화) + 동의어.

        ★요건재정의(2026-08-22 B-4~9): 중위도 하위처럼 "/" 로 여러 단어를
        가질 수 있다.
        """
        out: list[str] = []
        for v in segment_variants(self.mid):
            if v not in out:
                out.append(v)
            for syn in MID_SYNONYMS.get(v, ()):
                if syn not in out:
                    out.append(syn)
        return out

    @property
    def levels(self) -> int:
        return len([v for v in (self.top, self.mid, self.lows[0] if self.lows else "") if v])


def parse_filter_name(name: str) -> ParsedFilter:
    """`아름트리-무신사-남성-모자-버킷/사파리 햇` → 상위·중위·하위.

    ★브랜드-사이트 2조각은 **충분한 조각이 있을 때만** 무시한다.
    `여성-신발-구두`·`남성-잡화-신발` 처럼 애초에 3조각뿐인 이름에 그대로
    2개를 잘라내면 성별·상위가 통째로 '브랜드-사이트'로 오인돼 사라진다.
    조각이 `IGNORED_LEAD_SEGMENTS`(2) + 1(성별) 개보다 많을 때만
    — 즉 성별 뒤에 최소 한 조각(상위)이 남을 만큼 충분할 때만 — 앞 2조각을
    무시한다.
    """
    parts = [p.strip() for p in str(name or "").split("-") if p.strip()]
    if len(parts) > IGNORED_LEAD_SEGMENTS + 1:
        ignored = parts[:IGNORED_LEAD_SEGMENTS]
        rest = parts[IGNORED_LEAD_SEGMENTS:]
    else:
        ignored, rest = [], parts
    if not rest:  # 빈 이름 등 — 통째로 사용(원래도 빈 리스트)
        rest, ignored = parts, []

    top = rest[0] if len(rest) > 0 else ""
    mid = rest[1] if len(rest) > 1 else ""
    low_raw = "-".join(rest[2:]) if len(rest) > 2 else ""
    return ParsedFilter(
        raw=str(name or ""),
        top=top,
        mid=mid,
        lows=low_variants(low_raw),
        ignored=ignored,
    )


# ── 대조 ─────────────────────────────────────────────────────────


def level_hit(level: str, name: str) -> bool:
    """한 단계 이름이 주어진 이름과 같거나 포함하는가."""
    a, b = normalize(level), normalize(name)
    if not a or not b:
        return False
    return a == b or b in a or a in b


def path_hit(path: str, name: str) -> bool:
    return any(level_hit(lv, name) for lv in split_levels(path))


def filter_paths(paths: Iterable[str], names: Sequence[str]) -> list[str]:
    """names 중 하나라도 걸리는 경로만. 이름이 없으면 **아무것도** 고르지 않는다."""
    names = [n for n in (names or []) if str(n or "").strip()]
    if not names:
        return []
    return [p for p in paths if any(path_hit(p, n) for n in names)]


def specificity(path: str, parsed: ParsedFilter) -> tuple[int, int]:
    """정렬 기준 — (일치한 조각 수, 경로 짧은 순)."""
    hits = 0
    for name in [parsed.top, parsed.mid, *parsed.lows]:
        if name and path_hit(path, name):
            hits += 1
    return (hits, -len(path))


# ── 우선순위 규칙 (요건재정의 2026-08-22 · B-9) ──────────────────
#   남성의류 > 패션의류 > 패션의류잡화 순으로 우선 선택
#   여성의류 > 패션의류 > 패션의류잡화 순으로 우선 선택
#   국내 > 해외 순으로 적용
#   성별 > 골프 / 성별 > 낚시 / 성별 > 스포츠 순으로 우선 적용
#   남성 > 중성=혼용=공용 순 우선 적용
#   여성 > 공용=혼용=중성 순 적용
NEUTRAL_GENDER_WORDS = ("중성", "혼용", "공용", "유니섹스", "남녀")
OVERSEAS_WORDS = ("해외", "역직구", "해외직구")


def priority_rank(path: str, parsed: "ParsedFilter") -> int:
    """값이 클수록 우선 — 동점일 때 최종 선택 순서를 가른다."""
    gender = gender_of(parsed.raw)
    score = 0
    if gender:
        # 성별 정확 일치가 중성/혼용/공용보다, 그리고(자동으로) 성별 무관한
        # 활동명(골프·낚시·스포츠 등)만 일치하는 경로보다 항상 우선한다.
        if has_gender(path, gender):
            score += 100
        elif any(normalize(w) in normalize(path) for w in NEUTRAL_GENDER_WORDS):
            score += 40
        gendered_clothing = f"{gender}의류"
        if path_hit(path, gendered_clothing):
            score += 8
        elif path_hit(path, "패션의류잡화"):
            score += 3
        elif path_hit(path, "패션의류"):
            score += 5
    if not any(path_hit(path, w) for w in OVERSEAS_WORDS):
        score += 10  # 국내 > 해외
    return score


def pick_best(paths: Sequence[str], parsed: ParsedFilter) -> str:
    if not paths:
        return ""
    return sorted(
        paths,
        key=lambda p: (priority_rank(p, parsed), *specificity(p, parsed)),
        reverse=True,
    )[0]


def kind_of(parsed: ParsedFilter) -> str:
    """품목 구분 — 포괄 카테고리 선택용."""
    text = normalize(parsed.raw)
    if any(w in text for w in ACCESSORY_WORDS):
        return "잡화"
    if any(w in text for w in SHOE_WORDS):
        return "신발"
    if any(w in text for w in CLOTHING_WORDS):
        return "의류"
    return "잡화"


def match_by_levels(paths: Sequence[str], parsed: ParsedFilter) -> str:
    """1) 단계수가 같을 때 — 상위·중위·하위를 단계 순서대로 대조."""
    want = [parsed.top, parsed.mid]
    same_depth = [p for p in paths if len(split_levels(p)) == parsed.levels]
    hits: list[str] = []
    for path in same_depth:
        levels = split_levels(path)
        ok = all(
            (not name) or (i < len(levels) and level_hit(levels[i], name))
            for i, name in enumerate(want)
        )
        if not ok:
            continue
        if parsed.lows:
            last = levels[-1]
            if not any(level_hit(last, low) for low in parsed.lows):
                continue
        hits.append(path)
    return pick_best(hits, parsed)


def _bigrams(text: str) -> set[str]:
    s = normalize(text)
    return {s[i : i + 2] for i in range(len(s) - 1)} if len(s) > 1 else {s} if s else set()


def _overlap(a: str, b: str) -> float:
    ga, gb = _bigrams(a), _bigrams(b)
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / max(len(ga), len(gb))


def _words_in(text: str, words: Iterable[str]) -> set[str]:
    low = normalize(text)
    return {w for w in words if normalize(w) in low}


# 영문 표기 주의 — `women` 안에 `men` 이 들어 있어 여성 카테고리가 남성으로 잡힌다.
FEMALE_EN_WORDS = ("women", "woman", "ladies")


def gender_text(text: str, gender: str) -> str:
    """성별 판정용 문자열. 남성을 볼 때는 여성 영문 표기를 먼저 지운다."""
    low = normalize(text)
    if gender == "남성":
        for word in FEMALE_EN_WORDS:
            low = low.replace(word, "")
    return low


def gender_of(text: str) -> str:
    for gender, words in GENDER_WORDS.items():
        low = gender_text(text, gender)
        if any(normalize(w) in low for w in words):
            return gender
    return ""


def expand_synonyms(names: Sequence[str]) -> list[str]:
    """품목 동의어까지 넓힌 후보 이름."""
    out: list[str] = []
    for name in names:
        n = str(name or "").strip()
        if not n or n in out:
            continue
        out.append(n)
        low = normalize(n)
        for key, words in ITEM_SYNONYMS.items():
            if normalize(key) in low or any(normalize(w) in low for w in words):
                for w in words:
                    if w not in out:
                        out.append(w)
    return out


# ★DB화 — 클래스별 "구체적 하위 품목명". 이 목록에 있는 말들은 서로 형제
# 관계이며, 검색해서 없을 때 서로를 대신 골라서는 안 된다.
#   예) 신발(찾는 것) → 구두(형제 품목) NOT-OK · 신발 → 잡화(상위/일반) OK
#       양말(찾는 것) → 티셔츠(형제 품목) NOT-OK · 양말 → 기타의류(일반) OK
SPECIFIC_ITEM_WORDS: dict[str, tuple[str, ...]] = {
    "신발": (
        "운동화", "스니커즈", "구두", "부츠", "샌들", "슬리퍼",
        "활동화", "스포츠화", "워커",
    ),
    "의류": (
        "티셔츠", "셔츠", "니트", "코트", "자켓", "재킷", "청바지",
        "원피스", "스커트", "정장", "양말",
        *OUTER_SUBTYPES, *PANTS_SUBTYPES,
    ),
    "모자": (
        "캡", "비니", "버킷햇", "벙거지", "야구모자", "헌팅캡", "베레모",
        "페도라", "사파리햇", "트루퍼", "바라클라바",
    ),
    "가방": ("백팩", "크로스백", "토트백", "숄더백", "지갑"),
    "액세서리": ("주얼리", "목걸이", "귀걸이", "반지", "팔찌", "브로치"),
    "뷰티": (
        "스킨케어", "마스크팩", "베이스메이크업", "립메이크업", "아이메이크업",
        "네일", "프레그런스", "선케어", "클렌징", "필링", "헤어케어", "바디케어",
        "쉐이빙", "제모",
    ),
    "속옷": ("홈웨어", "여성속옷상의", "여성속옷하의", "여성속옷세트"),
}

# ★DB화 — 검색해서 없을 때 "안전하게" 물러날 수 있는 일반화(상위) 폴백어.
# 형제 품목으로 새지 않고 반드시 이 안의 더 넓은 카테고리로만 물러난다.
SAFE_FALLBACK_WORDS = GENERIC_CLASS_WORDS + (
    "신발잡화", "기타신발", "기타의류", "기타모자", "기타가방", "기타", "잡화기타",
)


def _contains_word(path: str, word: str) -> bool:
    """path 문자열이 word 를 담고 있는가 (단방향 포함 — path_hit 과 달리
    짧은 쪽이 긴 쪽에 우연히 포함되는 반대방향은 보지 않는다).

    예) SPECIFIC_ITEM_WORDS 의 "여성속옷상의" 는 "상의" 를 담고 있지만,
    path_hit 처럼 양방향으로 보면 path 의 아무 레벨("상의")이 이 긴 단어에
    포함된다고 오판해 엉뚱하게 형제 품목 충돌로 잡힌다.
    """
    nw = normalize(word)
    return bool(nw) and nw in normalize(path)


def _specific_item_conflict(path: str, parsed: "ParsedFilter") -> bool:
    """path 가 **찾는 것과 다른** 형제 품목이면 True — 근접 후보에서 제외한다.

    안전한 일반화 단어(잡화·기타의류 등)가 함께 있으면 형제 품목이라도
    막지 않는다 — '기타 신발(운동화 아님)' 처럼 안내성 표기일 수 있어서다.
    찾는 품목과 **관련된**(부분 겹침) 구체적 품목명은 형제로 보지 않는다
    (예: 찾는 것 "속옷"·"상의" 와 후보의 "여성속옷상의" 는 서로 관련어).
    """
    if any(_contains_word(path, w) for w in SAFE_FALLBACK_WORDS):
        return False
    wanted = {normalize(n) for n in expand_synonyms([parsed.mid, *parsed.lows]) if n}
    if not wanted:
        return False
    # ★리프(가장 구체적인 마지막 단계)만 본다 — 상위 단계는 그룹 이름일
    # 뿐이라(예: "속옷/홈웨어 > 여성 속옷 상의" 의 "홈웨어"), 리프가 실제
    # 품목을 정확히 담고 있다.
    leaf = leaf_of(path)

    # ★먼저 리프에 찾는 것과 관련된 구체품목명이 있는지부터 확인한다.
    # "정장샌들" 처럼 리프 하나에 무관 단어("정장"=의류)와 관련 단어
    # ("샌들"=신발)가 같이 있을 수 있다 — 관련 단어가 하나라도 있으면
    # 무관 단어가 섞여 있어도 형제 충돌로 보지 않는다.
    for words in SPECIFIC_ITEM_WORDS.values():
        for w in words:
            if _contains_word(leaf, w):
                nw = normalize(w)
                if any(nw in want or want in nw for want in wanted):
                    return False  # 찾는 것과 관련된 품목이 리프에 있음 — 형제 아님

    for words in SPECIFIC_ITEM_WORDS.values():
        for w in words:
            if not _contains_word(leaf, w):
                continue
            nw = normalize(w)
            if any(nw in want or want in nw for want in wanted):
                continue  # (위에서 이미 처리 — 여기 도달하면 무관 단어)
            return True
    return False


def nearest_score(parsed: "ParsedFilter", path: str) -> float:
    """소재·용도·성별·활용·동의어를 종합한 근접도 (0~1)."""
    leaf = leaf_of(path)
    names = expand_synonyms([n for n in (parsed.mid, *parsed.lows) if n])

    # 이름 유사도 — 하위·중위(동의어 포함) 조각과 리프/경로의 글자 겹침
    name_hit = 0.0
    for name in names:
        if level_hit(leaf, name):
            name_hit = max(name_hit, 0.95)
        name_hit = max(name_hit, _overlap(name, leaf), 0.6 * _overlap(name, path))

    # 성별
    gender = gender_of(parsed.raw)
    gender_hit = 0.0
    if gender:
        pg = gender_of(path)
        if pg == gender:
            gender_hit = 1.0
        elif pg:
            gender_hit = -0.5  # 다른 성별이면 감점

    # 소재 · 용도/활용
    mats = _words_in(parsed.raw, MATERIAL_WORDS)
    purposes = _words_in(parsed.raw, PURPOSE_WORDS)
    attr_hit = 0.0
    if mats:
        attr_hit += 0.5 * len(_words_in(path, mats)) / len(mats)
    if purposes:
        attr_hit += 0.5 * len(_words_in(path, purposes)) / len(purposes)

    # 포괄 카테고리 보너스 (품목 성격에 맞는 곳)
    generic_hit = 0.0
    for generic in GENERIC_BY_KIND.get(kind_of(parsed), ()):
        if path_hit(path, generic):
            generic_hit = 0.3
            break

    score = 0.55 * name_hit + 0.2 * max(gender_hit, 0.0) + 0.15 * attr_hit + generic_hit
    if gender_hit < 0:
        score += 0.2 * gender_hit  # 성별 불일치 감점
    return max(0.0, min(1.0, score))


def nearest_category(name: str, paths: Sequence[str]) -> tuple[str, float]:
    """규칙으로 못 찾았을 때 — **반드시** 하나를 고른다 (가장 가까운 것).

    ★요건: "엑셀에서는 반드시 최종 카테고리명을 망고로 전달해 — 가장
    비슷한 거라도 전달해". 동떨어진 형제 품목(예: 신발을 찾는데 구두로
    새는 것)은 되도록 피하지만, 그것 말고는 후보가 없을 때도 포기하지
    않고 원래 후보 전체에서 가장 가까운 것을 고른다(성별은 예외 — 성별은
    find_category 상단에서 이미 절대적으로 걸러진 뒤라 여기 들어오는
    candidates 는 항상 성별 안전하다).
    """
    parsed = parse_filter_name(name)
    candidates = [p for p in paths if str(p or "").strip()]
    safe = [p for p in candidates if not _specific_item_conflict(p, parsed)]
    pool = safe if safe else candidates

    best, best_score = "", -1.0
    for path in pool:
        score = nearest_score(parsed, path)
        if score > best_score or (score == best_score and best and len(path) < len(best)):
            best, best_score = path, score
    return best, max(best_score, 0.0)


def is_from(paths: Sequence[str], category: str) -> bool:
    """고른 카테고리가 엑셀 목록 안의 값인지."""
    if not category:
        return False
    want = normalize(category)
    return any(normalize(p) == want for p in paths)


def ensure_from(paths: Sequence[str], category: str, name: str = "") -> str:
    """엑셀 범위 밖이면 목록 안에서 가장 가까운 것으로 되돌린다."""
    if is_from(paths, category):
        return category
    fallback, _score = nearest_category(name or category, paths)
    return fallback


def has_gender(path: str, gender: str) -> bool:
    """경로가 그 성별 표기를 담고 있는가 (동의어·영문 표기 포함)."""
    words = GENDER_WORDS.get(gender, (gender,))
    low = gender_text(path, gender)
    return any(normalize(w) in low for w in words if str(w or "").strip())


OPPOSITE = {"남성": ("여성",), "여성": ("남성",)}


def opposite_of(gender: str) -> tuple[str, ...]:
    return OPPOSITE.get(gender, ())


def strip_opposite_gender(paths: Sequence[str], gender: str) -> list[str]:
    """★절대규칙: 반대 성별 용어가 들어간 카테고리는 후보에서 제거한다.

    (여성 필터면 남성패션·남성신발… 전부 제외, 남성 필터면 여성… 전부 제외)
    """
    others = opposite_of(gender)
    if not others:
        return list(paths)
    return [p for p in paths if not any(has_gender(p, o) for o in others)]


def violates_gender(path: str, filter_name: str) -> bool:
    """고른 카테고리가 반대 성별 용어를 담고 있는가."""
    gender = gender_of(filter_name)
    return any(has_gender(path, o) for o in opposite_of(gender))


def class_of(text: str) -> str:
    """필터명이 속한 품목 계열 (없으면 '').

    같은 시작 위치에서 여러 계열 단어가 겹치면(예: "패딩/퍼 신발" 은 의류
    단어 "패딩"과 신발 단어 "신발"을 둘 다 담고 있다) **더 길게(구체적으로)
    일치하는 쪽**을 우선한다 — 짧은 단어가 먼저 매칭됐다고 그게 항상 맞는
    계열은 아니다.
    """
    low = normalize(text)
    best, best_key = "", (10**6, 0)
    for cls, words in CLASS_WORDS.items():
        for w in words:
            nw = normalize(w)
            if not nw:
                continue
            pos = low.find(nw)
            if pos < 0:
                continue
            key = (pos, -len(nw))
            if key < best_key:
                best, best_key = cls, key
    return best


def _is_generic_bucket_name(segment: str) -> bool:
    """이 한 단계 이름 자체가 "패션의류잡화"·"의류잡화" 같은 포괄 버킷인가."""
    s = normalize(segment)
    return bool(s) and any(normalize(w) in s for w in GENERIC_CLASS_WORDS)


def path_class(path: str) -> str:
    """카테고리 경로가 드러내는 품목 계열 (없으면 '').

    ★최상위 단계가 "패션의류잡화"·"의류잡화" 같은 **포괄(잡화) 버킷 이름**
    이면 그 판정에서 뺀다 — 그 문구 안에 우연히 "의류" 글자가 들어 있어
    (class_of 는 위치 기반으로 가장 먼저 걸리는 단어를 고른다), 실제로는
    모자·신발·선글라스인 경로가 전부 "의류" 계열로 잘못 분류되는 사고가
    났다. 포괄 버킷이 아닌 상위 단계(예: "신발")는 그대로 포함해 계열
    판정에 쓴다 — 리프 안에서 다른 계열 단어와 뒤섞인 경우(예: "정장샌들")
    에도 상위 단계의 명확한 계열 표기가 우선하도록 한다.
    """
    levels = split_levels(path)
    if not levels:
        return class_of(path)
    if len(levels) > 1 and _is_generic_bucket_name(levels[0]):
        levels = levels[1:]
    return class_of(" ".join(levels))


def is_generic_path(path: str) -> bool:
    return any(path_hit(path, w) for w in GENERIC_CLASS_WORDS)


def strip_other_classes(paths: Sequence[str], cls: str) -> list[str]:
    """★규칙: 다른 계열(의류↔신발, 선글라스↔시계 …) 카테고리는 제외.

    계열이 드러나지 않는 경로와 잡화 계열 경로는 남긴다 (규칙3 폴백용).
    """
    if not cls:
        return list(paths)
    out: list[str] = []
    for p in paths:
        pc = path_class(p)
        if not pc or pc == cls or is_generic_path(p):
            out.append(p)
    return out


def gender_paths(paths: Sequence[str], gender: str) -> list[str]:
    """★규칙2: 성별이 구분된 필터면 그 성별 카테고리 안에서만 고른다.

    같은 성별 경로가 있으면 그것만, 없으면 **다른 성별이 아닌** 경로만 남긴다.
    """
    if not gender:
        return list(paths)
    same = [p for p in paths if has_gender(p, gender)]
    if same:
        return same
    others = [g for g in GENDER_WORDS if g != gender]
    return [p for p in paths if not any(has_gender(p, g) for g in others)]


def item_words_of(parsed: "ParsedFilter") -> list[str]:
    """필터명에 들어 있는 규칙 품목명 (의류·잡화·모자·선글라스·액세서리·신발)."""
    text = normalize(parsed.raw)
    return [w for w in ITEM_RULE_WORDS if normalize(w) in text]


def item_level(path: str, word: str) -> int:
    """그 품목명이 몇 단계에서 나오는지 (0=상위). 없으면 큰 수."""
    for i, level in enumerate(split_levels(path)):
        if level_hit(level, word):
            return i
    return 99


def item_depth_ratio(path: str, word: str) -> float:
    """품목명이 나오는 단계의 '깊이 비율' — 1.0=하위(리프) · 0.0=상위.

    경로 길이가 서로 다른 후보들을 상대 비교하려고 절대 인덱스가 아니라
    비율로 잰다. 못 찾으면 -1.0.
    """
    levels = split_levels(path)
    if not levels:
        return -1.0
    idx = -1
    for i, level in enumerate(levels):
        if level_hit(level, word):
            idx = i
            break
    if idx < 0:
        return -1.0
    if len(levels) == 1:
        return 1.0
    return idx / (len(levels) - 1)


def item_paths(paths: Sequence[str], words: Sequence[str]) -> list[str]:
    """★규칙3(요건재정의 8-3): 품목명이 있는 경로만, **하위 → 중위 → 상위**
    순으로 우선한다 (품목명이 나오는 단계가 깊을수록/구체적일수록 우선).
    """
    if not words:
        return list(paths)
    scored: list[tuple[float, str]] = []
    for p in paths:
        ratio = max((item_depth_ratio(p, w) for w in words), default=-1.0)
        if ratio >= 0:
            scored.append((ratio, p))
    if not scored:
        return []
    scored.sort(key=lambda item: (-item[0], len(item[1])))
    return [p for _ratio, p in scored]


def clothing_priority(paths: Sequence[str], gender: str = "") -> list[str]:
    """★규칙4(요건재정의 9): 의류는 <성별>의류 → 패션의류 → 패션의류잡화 순 우선."""
    for preferred in clothing_preferred_for(gender):
        hits = [p for p in paths if path_hit(p, preferred)]
        if hits:
            return hits
    return list(paths)


def constrain(paths: Sequence[str], parsed: "ParsedFilter") -> tuple[list[str], list[str]]:
    """규칙 1·2·3·4 로 후보를 좁힌다. 반환: (후보, 적용된 규칙 설명).

    ★요건재정의(2026-08-22 B-10) 순서: 의류↔신발·선글라스↔시계 같은 계열
    배타(엄격규칙)를 성별 좁히기보다 **먼저** 적용한다. 성별 좁히기가 먼저
    적용되면(같은 성별 표기가 있는 후보만 남기는 로직) 성별 표기가 없는
    다른 계열의 정상 대안이, 성별 표기가 있는 잘못된 계열 후보에 밀려
    사라질 수 있다 (예: "남성시계" 가 성별 필터를 통과해 "선글라스" 계열
    배타 검사를 받을 기회조차 없이 살아남는 사고).
    """
    pool = [p for p in paths if str(p or "").strip()]
    notes: list[str] = []

    cls = class_of(parsed.raw)
    if cls:
        narrowed = strip_other_classes(pool, cls)
        same = [p for p in narrowed if path_class(p) == cls]
        if same:
            pool, note = same, f"계열={cls}"
        elif narrowed:
            pool, note = narrowed, f"계열={cls}→잡화폴백"
        else:
            note = ""
        if note:
            notes.append(note)

    gender = gender_of(parsed.raw)
    if gender:
        narrowed = gender_paths(pool, gender)
        if narrowed:
            pool = narrowed
            notes.append(f"성별={gender}")

    words = item_words_of(parsed)
    if words:
        narrowed = item_paths(pool, words)
        if narrowed:
            pool = narrowed
            notes.append("품목=" + "·".join(words))

    if "의류" in words:
        narrowed = clothing_priority(pool, gender)
        if narrowed and len(narrowed) < len(pool):
            pool = narrowed
            notes.append("의류 우선순위" + (f"({gender})" if gender else ""))

    return pool, notes


MAX_DB_ROUNDS = 3  # ★요건재정의 D-3-6): 2)~5) 과정을 3회 반복 수행한다


def find_category(
    name: str,
    paths: Sequence[str],
    *,
    exclude: Sequence[str] = (),
    force: bool = True,
    db=None,
) -> tuple[str, str]:
    """최적("최종") 카테고리와 그 근거 단계 — 요건재정의(2026-08-22) D 항 그대로.

    탐색 순서 (대전제):
      1) 완전일치 — 망고 필터명(상위·중위·하위)과 엑셀(상위·중위·하위)이 동일
      2) 하위 카테고리로 엑셀에서 검색 — 1건이면 확정, 0건이면 4)로, 2건 이상이면 3)으로
      3) 우선순위 조정 — 상위/중위 일치 → OK, 국내/해외 → 국내 OK,
         그래도 안 되면 정보화DB 로 좁혀보고 4)로
      4) 포괄성(확장범주) 범위로 찾는다 — 의류/신발/잡화 등 품목별 포괄 카테고리
      5) 정보화DB(`db`)에서 연관검색어를 찾아 검색어를 확장한다
      (2)~5) 를 최대 `MAX_DB_ROUNDS`(3)회 반복)
      6) 그래도 없으면 — "망고 필터명"과 가장 가까운 카테고리 하나를 반드시 지정
         (소재·재료·용도·성별·활용을 종합 — `force=True`, 기본값)

    절대규칙(예외 없음, 어떤 단계에서도 뚫지 않음):
      · 반대 성별 카테고리는 어떤 경우에도 고르지 않는다
      · "브랜드" 가 붙은 카테고리는 어떤 경우에도 확정하지 않는다
      · 최적 카테고리는 반드시 엑셀 목록 범위 안의 값이어야 한다(호출측 `ensure_from`)
      · 의류↔신발, 선글라스↔시계(잡화 결합 표기는 예외) 처럼 다른 계열은 섞지 않는다

    `exclude` 는 이미 시도한 카테고리. `db` 는 `category_db.CategoryDB` —
    5) 단계에서 연관검색어를 찾는 데 쓴다(없으면 5) 단계는 건너뛴다).
    """
    parsed = parse_filter_name(name)
    skip = {normalize(e) for e in (exclude or []) if str(e or "").strip()}
    all_paths = [
        p for p in paths if str(p or "").strip() and normalize(p) not in skip
    ]
    if not all_paths:
        return "", "자료 없음"

    # ★절대규칙: 반대 성별 카테고리는 어떤 경우에도 고르지 않는다
    gender = gender_of(parsed.raw)
    if gender:
        allowed = strip_opposite_gender(all_paths, gender)
        if not allowed:
            return "", f"성별({gender}) 조건에 맞는 카테고리 없음"
        all_paths = allowed

    # ★절대규칙(예외 없음): "브랜드" 가 붙은 카테고리는 어떤 경우에도
    #   확정하지 않는다. 사용자가 엑셀에서 "브랜드" 를 직접 지운 이유가
    #   바로 이것 — 실제 마켓 엑셀엔 정식 카테고리와 별도로 "브랜드
    #   여성의류 > …" 처럼 브랜드관 전용 트리가 통째로 또 있는데, 엑셀에
    #   있다고 해서 그게 정답인 게 아니다. "가장 비슷한 거라도 전달해"
    #   원칙은 성별·브랜드 절대규칙에는 적용되지 않는다 — 그 둘을 뚫고
    #   "가장 비슷한 것"을 억지로 만들지 않는다.
    non_brand = [p for p in all_paths if not _contains_word(p, "브랜드")]
    if not non_brand:
        return "", "브랜드 카테고리만 있음 — 매핑하지 않음"
    all_paths = non_brand

    # ★소프트규칙: 동떨어진 형제 품목은 되도록 고르지 않는다.
    #   예) "맨투맨/후드" 를 찾는데 "패딩"(같은 의류 계열의 다른 구체적
    #   품목)을 대신 고르면 안 된다. 이후 모든 단계가 보는 후보 풀
    #   자체에서 뺀다. 다만 안전한 후보가 하나도 없으면(위와 동일한
    #   이유로) 포기하지 않고 원래 후보로 계속 진행해 "가장 비슷한 것"을
    #   반드시 고른다.
    if parsed.mid or parsed.lows:
        safe_paths = [p for p in all_paths if not _specific_item_conflict(p, parsed)]
        if safe_paths:
            all_paths = safe_paths

    # ★규칙 2·3·4 — 성별·품목명·의류 우선순위(성별 우선)로 후보를 먼저 좁힌다
    paths, notes = constrain(all_paths, parsed)
    tag = (" [" + " · ".join(notes) + "]") if notes else ""
    if not paths:
        paths, tag = all_paths, ""

    # 1) 완전일치 — 망고 단계수 == 엑셀 단계수 & 상위·중위·하위 전부 일치
    found = match_by_levels(paths, parsed)
    if found:
        return found, "1) 완전일치" + tag

    low_terms = list(parsed.lows)
    mid_terms = list(parsed.mids)
    tried_db_terms: set[str] = set()

    for round_no in range(1, MAX_DB_ROUNDS + 1):
        # 2) 하위 카테고리로 엑셀에서 검색
        low_hits = filter_paths(paths, expand_synonyms(low_terms))
        low_hits = low_hits or filter_paths(paths, low_terms)

        if len(low_hits) == 1:
            return low_hits[0], f"2) 하위검색 1건({round_no}회차)" + tag

        if len(low_hits) > 1:
            # 3) 우선순위 조정 — 상위/중위 일치 → OK
            narrowed = filter_paths(low_hits, parsed.tops)
            if not narrowed:
                narrowed = filter_paths(low_hits, mid_terms)
            if narrowed:
                return (
                    pick_best(narrowed, parsed),
                    f"3) 우선순위(상위·중위 일치, {round_no}회차)" + tag,
                )
            # 국내/해외 → 국내 OK
            domestic = [p for p in low_hits if not any(path_hit(p, w) for w in OVERSEAS_WORDS)]
            if domestic and len(domestic) < len(low_hits):
                return (
                    pick_best(domestic, parsed),
                    f"3) 우선순위(국내, {round_no}회차)" + tag,
                )
            # 정보화DB 로도 못 좁히면 그 안에서 가장 그럴듯한 것 하나
            return (
                pick_best(low_hits, parsed),
                f"3) 우선순위(정보화DB 조회, {round_no}회차)" + tag,
            )

        # 하위 검색 0건 → 요건 D-11: 하위(1차) 없으면 중위(2차)로 전체 재검색
        mid_hits = filter_paths(paths, mid_terms)
        if mid_hits:
            return pick_best(mid_hits, parsed), f"3) 중위 2차검색({round_no}회차)" + tag

        # 4) 포괄성(확장범주) 범위로 찾는다
        kind = kind_of(parsed)
        generic = filter_paths(paths, GENERIC_BY_KIND.get(kind, ()))
        if generic:
            narrowed = filter_paths(generic, low_terms) or filter_paths(generic, mid_terms)
            target = narrowed or generic
            return pick_best(target, parsed), f"4) 확장범주({kind}, {round_no}회차)" + tag

        # 5) 정보화DB에서 연관검색어를 찾아 검색어를 확장하고 다음 회차로
        if db is None:
            break
        new_terms: list[str] = []
        for term in [*low_terms, *mid_terms]:
            key = normalize(term)
            if not term or key in tried_db_terms:
                continue
            tried_db_terms.add(key)
            for related in db.related_terms(term):
                if related not in low_terms and related not in new_terms:
                    new_terms.append(related)
        if not new_terms:
            break
        low_terms = [*low_terms, *new_terms]

    # 6) 그래도 없으면 — 망고 필터명과 가장 가까운 카테고리 하나를 반드시 지정
    if force:
        nearest, score = nearest_category(name, paths)
        if nearest:
            return nearest, f"6) 근접매핑 강제지정 ({score:.2f})" + tag
    return "", "미검출"
