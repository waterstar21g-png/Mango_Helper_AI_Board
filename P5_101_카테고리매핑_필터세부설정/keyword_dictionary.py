"""연관검색어DB — 카테고리 마스터 + 키워드 매핑 사전 (요건 2026-08-23).

목적: 특정 검색어로 카테고리가 검색되지 않을 때, 그 검색어에 대한
<연관검색어>·<유사검색어>·<동일범주 검색어>·<확대범주 검색어> 로
재검색을 수행해 최적의 카테고리와 매핑하기 위한 목적 특화 DB.

논리적 구조 (ERD)
==================

CATEGORY_MASTER (카테고리 마스터)
    Cat_ID     (PK)  카테고리 고유 식별자
    Cat_Name         카테고리명 (그 단계의 이름)
    Parent_ID  (FK)  상위 카테고리 ID (ROOT 면 없음)
    Level            분류 뎁스 (1=대분류 … N=최하위)
    Full_Path        전체 카테고리 경로 ("A > B > C")

KEYWORD_DICTIONARY (검색어 매핑 사전)
    Keyword_ID (PK)  검색어 고유 식별자
    Search_Keyword   고객/필터가 입력할 수 있는 검색어
    Target_Cat_ID (FK)  매핑될 CATEGORY_MASTER.Cat_ID
    Mapping_Type     SY(동의어) · MO(형태소분리) · RE(동일범주/형제어) · EX(확대범주/상위어)
    Priority         다중 매칭 시 우선순위 (1이 가장 높음)

관계: KEYWORD_DICTIONARY.Target_Cat_ID → CATEGORY_MASTER.Cat_ID (N:1)
      CATEGORY_MASTER.Parent_ID → CATEGORY_MASTER.Cat_ID (자기참조, 트리)

자동 매핑 4단계 (Waterfall)
    1) 완전일치   — Search_Keyword == 리프 Cat_Name
    2) 유사어매칭 — Mapping_Type = SY/MO
    3) 동일범주   — Mapping_Type = RE (같은 Parent_ID 를 공유하는 형제 리프)
    4) 확대범주   — Mapping_Type = EX (조상 노드로 범위 확대)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Sequence

try:
    import matching as _matching  # 기존 품목 동의어 사전(캡모자↔야구모자 등) 재사용
except ImportError:  # pragma: no cover - 단독 사용 시에도 동작하도록
    _matching = None

_SPLIT = re.compile(r"[\s/·,()\[\]|]+")

# 부모 경로에 이 단어가 있으면 리프 토큰과 결합해 형태소(MO) 키워드를 만든다.
ATTRIBUTE_WORDS: tuple[str, ...] = (
    "남성", "여성", "남아", "여아", "유아동", "공용",
)

MAPPING_TYPES = ("SY", "MO", "RE", "EX")
MAPPING_TYPE_LABEL = {
    "SY": "동의어",
    "MO": "형태소분리",
    "RE": "동일범주(형제어)",
    "EX": "확대범주(상위어)",
}


@dataclass
class CategoryNode:
    cat_id: str
    cat_name: str
    parent_id: str | None
    level: int
    full_path: str


@dataclass
class KeywordEntry:
    keyword_id: str
    search_keyword: str
    target_cat_id: str
    mapping_type: str  # SY / MO / RE / EX
    priority: int


@dataclass
class KeywordDB:
    """CATEGORY_MASTER + KEYWORD_DICTIONARY 를 함께 관리하는 연관검색어DB."""

    categories: dict[str, CategoryNode] = field(default_factory=dict)
    keywords: list[KeywordEntry] = field(default_factory=list)
    _path_to_id: dict[str, str] = field(default_factory=dict)
    _next_cat_seq: int = 1
    _next_kw_seq: int = 1

    # ── CATEGORY_MASTER ──────────────────────────────────────────

    def add_path(self, path: str) -> str | None:
        """"A > B > C" 경로를 등록한다. 중간 노드도 함께 등록하고 리프
        Cat_ID 를 반환한다(빈 경로면 None)."""
        levels = [p.strip() for p in str(path or "").split(">") if p.strip()]
        if not levels:
            return None
        parent_id: str | None = None
        built: list[str] = []
        leaf_id = None
        for i, name in enumerate(levels):
            built.append(name)
            full = " > ".join(built)
            key = full.lower()
            cat_id = self._path_to_id.get(key)
            if cat_id is None:
                cat_id = self._new_cat_id()
                self._path_to_id[key] = cat_id
                self.categories[cat_id] = CategoryNode(cat_id, name, parent_id, i + 1, full)
            parent_id = cat_id
            leaf_id = cat_id
        return leaf_id

    def build_from_paths(self, paths: Sequence[str]) -> "KeywordDB":
        for p in paths:
            self.add_path(p)
        return self

    def _new_cat_id(self) -> str:
        cid = f"C{self._next_cat_seq:04d}"
        self._next_cat_seq += 1
        return cid

    def is_leaf(self, cat_id: str) -> bool:
        return not any(c.parent_id == cat_id for c in self.categories.values())

    def leaves(self) -> list[CategoryNode]:
        return [c for c in self.categories.values() if self.is_leaf(c.cat_id)]

    def children_of(self, cat_id: str | None) -> list[CategoryNode]:
        return [c for c in self.categories.values() if c.parent_id == cat_id]

    def ancestors_of(self, cat_id: str) -> list[CategoryNode]:
        """가까운 조상부터 먼 조상(대분류) 순으로."""
        out: list[CategoryNode] = []
        node = self.categories.get(cat_id)
        while node and node.parent_id:
            node = self.categories.get(node.parent_id)
            if node:
                out.append(node)
        return out

    # ── KEYWORD_DICTIONARY ───────────────────────────────────────

    def _add_keyword(self, keyword: str, target_cat_id: str, mapping_type: str, priority: int) -> None:
        keyword = keyword.strip()
        if not keyword:
            return
        kid = f"K{self._next_kw_seq:04d}"
        self._next_kw_seq += 1
        self.keywords.append(KeywordEntry(kid, keyword, target_cat_id, mapping_type, priority))

    def build_dictionary(self) -> "KeywordDB":
        """리프 카테고리마다 SY·MO·RE·EX 키워드를 자동 생성한다.

        - SY(동의어)  : 리프명을 "/" 로 쪼갠 개별 토큰 + 구분자 없이 붙인 결합어
        - MO(형태소)  : 조상 경로에 있는 성별/속성 단어 + 리프 토큰의 결합어
                        (예: "무스탕" + 조상의 "남성" → "남성무스탕")
        - RE(동일범주) : 같은 Parent_ID(형제) 리프들의 토큰을 서로의 연관어로 등록
        - EX(확대범주) : 조상 노드 이름(가까운 조상=우선순위 높음)
        """
        self.keywords.clear()
        self._next_kw_seq = 1

        leaves = self.leaves()
        siblings_by_parent: dict[str | None, list[CategoryNode]] = {}
        for leaf in leaves:
            siblings_by_parent.setdefault(leaf.parent_id, []).append(leaf)

        for leaf in leaves:
            tokens = [t for t in _SPLIT.split(leaf.cat_name) if t]
            if not tokens:
                continue

            # SY — 개별 토큰 + 결합어(원문 그대로도 등록)
            for tok in tokens:
                self._add_keyword(tok, leaf.cat_id, "SY", 1)
            combined = leaf.cat_name.replace("/", "").replace(" ", "")
            if combined not in tokens:
                self._add_keyword(combined, leaf.cat_id, "SY", 1)

            # SY(사전) — 기존 품목 동의어 사전(matching.ITEM_SYNONYMS) 재사용.
            #   토큰이 사전의 대표어나 동의어 중 하나와 같으면, 그 묶음의
            #   나머지 말들도 같은 카테고리의 동의어로 등록한다.
            #   (예: "캡모자" ↔ "야구모자"·"볼캡"·"캡)
            if _matching is not None:
                for tok in tokens:
                    for key, synonyms in _matching.ITEM_SYNONYMS.items():
                        pool = {key, *synonyms}
                        if tok in pool:
                            for extra in pool:
                                if extra != tok:
                                    self._add_keyword(extra, leaf.cat_id, "SY", 1)

            # MO — 조상 경로의 속성어(성별 등) + 토큰 결합어 (양방향)
            #   - 토큰에 속성어가 없으면: 속성어를 붙인 결합어 생성
            #     (예: 조상에 "남성" + 토큰 "무스탕" → "남성무스탕")
            #   - 토큰에 이미 속성어가 붙어 있으면: 속성어를 뗀 원형도 등록
            #     (예: 토큰 "남성로퍼" → "로퍼")
            ancestor_names = [a.cat_name for a in self.ancestors_of(leaf.cat_id)]
            attrs = [a for a in ATTRIBUTE_WORDS if any(a in name for name in ancestor_names)]
            for tok in tokens:
                own_attr = next((a for a in ATTRIBUTE_WORDS if tok.startswith(a)), None)
                if own_attr:
                    stripped = tok[len(own_attr) :]
                    if stripped and stripped != tok:
                        self._add_keyword(stripped, leaf.cat_id, "MO", 2)
                    continue
                for attr in attrs:
                    self._add_keyword(f"{attr}{tok}", leaf.cat_id, "MO", 2)

            # RE — 같은 부모를 공유하는 형제 리프의 토큰들
            for sib in siblings_by_parent.get(leaf.parent_id, ()):
                if sib.cat_id == leaf.cat_id:
                    continue
                for tok in [t for t in _SPLIT.split(sib.cat_name) if t]:
                    self._add_keyword(tok, leaf.cat_id, "RE", 3)

            # EX — 조상 이름(가까운 조상일수록 우선순위 높음)
            for depth, ancestor in enumerate(self.ancestors_of(leaf.cat_id), start=1):
                self._add_keyword(ancestor.cat_name, leaf.cat_id, "EX", 3 + depth)

        return self

    # ── 조회 (자동 매핑 4단계) ────────────────────────────────────

    def lookup(
        self, keyword: str, *, mapping_types: Sequence[str] | None = None
    ) -> list[KeywordEntry]:
        """검색어와 정확히 일치하는 KEYWORD_DICTIONARY 항목을 우선순위순으로."""
        want = str(keyword or "").strip()
        if not want:
            return []
        hits = [
            k
            for k in self.keywords
            if k.search_keyword == want and (mapping_types is None or k.mapping_type in mapping_types)
        ]
        hits.sort(key=lambda k: k.priority)
        return hits

    def resolve(self, keyword: str) -> tuple[str | None, str]:
        """요건 4단계(폭포수)로 검색어를 카테고리 하나로 해석한다.

        반환: (Cat_ID 또는 None, 어느 단계에서 찾았는지 설명)
        """
        want = str(keyword or "").strip()
        if not want:
            return None, "검색어 없음"

        # 1) 완전일치 — 리프 Cat_Name 이 검색어와 동일
        for leaf in self.leaves():
            if leaf.cat_name == want:
                return leaf.cat_id, "1) 완전일치"

        # 2) 유사어 매칭 (SY·MO)
        hits = self.lookup(want, mapping_types=("SY", "MO"))
        if hits:
            return hits[0].target_cat_id, f"2) 유사어매칭({hits[0].mapping_type})"

        # 3) 동일범주(형제어)
        hits = self.lookup(want, mapping_types=("RE",))
        if hits:
            return hits[0].target_cat_id, "3) 동일범주(RE)"

        # 4) 확대범주(상위어)
        hits = self.lookup(want, mapping_types=("EX",))
        if hits:
            return hits[0].target_cat_id, "4) 확대범주(EX)"

        return None, "미검출"

    # ── 범위 한정(scoped) 폭포수 — 특정 카테고리 실패 시 형제/조상만 본다 ─
    #
    # ★요건 원문 그대로: "3) 동일/확대 범주 탐색 (만약 M112 카테고리에
    #   현재 판매 상품이 0개일 경우): 동일범주 검색 — M112 의 Parent_ID 를
    #   공유하는 형제 카테고리 노출. 확대범주 검색 — 상위 카테고리로 넓혀
    #   노출". 즉 3)·4) 단계는 "아무 검색어나 전역으로 찾는" 것이 아니라
    #   "**특정 카테고리 하나가 실패했을 때** 그 카테고리를 중심으로
    #   형제·조상만 본다"는 **범위 한정** 탐색이다.
    #
    # 기존 `resolve()` 는 KEYWORD_DICTIONARY 전체를 대상으로 전역 조회하기
    # 때문에, RE 로 등록된 검색어는 그 형제(원래 등록처)에서 이미 SY 로도
    # 걸려 있어 3) 단계가 실제로 선택되는 일이 거의 없었다(전역 조회에서는
    # RE 가 SY 뒤에 가려짐). 아래 메서드들은 "이 카테고리(cat_id) 하나가
    # 실패했다"는 조건을 명시적으로 주고, 그 형제·조상만 후보로 삼는다.

    def siblings_of(self, cat_id: str) -> list[CategoryNode]:
        """같은 Parent_ID 를 공유하는 형제 리프 (자기 자신은 제외)."""
        node = self.categories.get(cat_id)
        if node is None:
            return []
        return [c for c in self.children_of(node.parent_id) if c.cat_id != cat_id]

    def descendants_of(self, cat_id: str) -> list[CategoryNode]:
        """이 노드 아래의 모든 하위 노드(자손) — 너비우선으로."""
        out: list[CategoryNode] = []
        queue = [c.cat_id for c in self.children_of(cat_id)]
        seen: set[str] = set()
        while queue:
            cid = queue.pop(0)
            if cid in seen:
                continue
            seen.add(cid)
            node = self.categories.get(cid)
            if node is None:
                continue
            out.append(node)
            queue.extend(c.cat_id for c in self.children_of(cid))
        return out

    def _best_by_similarity(self, name: str, candidate_ids: Sequence[str]) -> str | None:
        """이름 글자(bigram) 유사도로 candidate_ids 중 가장 가까운 것 하나."""
        if not candidate_ids:
            return None
        if _matching is not None:
            best_id, best_score = None, -1.0
            for cid in candidate_ids:
                node = self.categories.get(cid)
                if node is None:
                    continue
                score = _matching._overlap(name, node.cat_name) + 0.5 * _matching._overlap(
                    name, node.full_path
                )
                if score > best_score:
                    best_id, best_score = cid, score
            if best_id is not None:
                return best_id
        return candidate_ids[0]

    def substitute_for(
        self,
        cat_id: str,
        *,
        available_cat_ids: Sequence[str] | None = None,
    ) -> tuple[str | None, str]:
        """`cat_id` 가 실패(미존재·품절 등)했을 때 대체 카테고리를 찾는다.

        ★요건(절대): "이걸 발생하지 않기 위해 DB를 만든 것" — `available_cat_ids`
        가 주어졌고 그 안에 카테고리가 **하나라도** 있으면, 아래 순서
        (3→4→5) 중 어디선가 **반드시** 하나를 반환한다. 정말 아무 것도
        없을 때(그 범위 자체가 빈 목록)에만 실패로 본다 — 그 경우는
        "미검출"이 아니라 "카테고리 자료 없음"으로 구분해 알려준다.

        순서:
          3) 동일범주 — 형제 리프
          4) 확대범주 — 가까운 조상부터. 조상 노드 자신이 없으면 그
             조상의 하위트리(사촌 리프들) 전체에서 찾는다
          5) 그래도 없으면 — 범위 전체에서 이름이 가장 비슷한 것 하나를
             반드시 지정한다(오매핑보다 낫다는 전제 아래, 미매칭은 이보다
             더 나쁘다)
        """
        node = self.categories.get(cat_id)
        if node is None:
            return None, "대상 카테고리 없음"

        allowed = None if available_cat_ids is None else list(dict.fromkeys(available_cat_ids))

        if allowed is not None and not allowed:
            return None, "카테고리 자료 없음"

        allowed_set = None if allowed is None else set(allowed)

        def ok(cid: str) -> bool:
            return allowed_set is None or cid in allowed_set

        # 3) 동일범주 — 형제 리프
        for sib in self.siblings_of(cat_id):
            if ok(sib.cat_id):
                return sib.cat_id, "3) 동일범주(형제)"

        # 4) 확대범주 — 가까운 조상부터. 조상 자신이 없으면 그 하위트리
        #    (사촌 리프들)에서 available 한 것을 찾는다.
        for depth, ancestor in enumerate(self.ancestors_of(cat_id), start=1):
            if ok(ancestor.cat_id):
                return ancestor.cat_id, f"4) 확대범주(상위 {depth}단계)"
            if allowed_set is not None:
                cousins = [
                    d.cat_id for d in self.descendants_of(ancestor.cat_id) if d.cat_id in allowed_set
                ]
                if cousins:
                    best = self._best_by_similarity(node.cat_name, cousins)
                    return best, f"4) 확대범주(상위 {depth}단계 하위트리)"

        # 5) ★반드시 하나 지정 — 위 3)·4) 로도 못 찾았는데 이 범위(마켓)에
        #    카테고리가 있다면, 그중 이름이 가장 비슷한 것을 강제 지정한다.
        #    "미검출"을 반환하는 것은 이 DB 의 존재 목적에 위배된다.
        #    범위 제한이 없을 때(allowed=None)도 CATEGORY_MASTER 전체
        #    (자기 자신 제외)를 마지막 후보로 본다 — 형제·조상이 우연히
        #    하나도 없는 고립 노드라도 빈손으로 끝내지 않는다.
        pool = list(allowed_set) if allowed_set is not None else [
            c for c in self.categories if c != cat_id
        ]
        if pool:
            best = self._best_by_similarity(node.cat_name, pool)
            if best:
                return best, "5) 최근접 강제지정(전범위)"

        return None, "카테고리 자료 없음"

    def resolve_with_fallback(
        self,
        keyword: str,
        *,
        available_cat_ids: Sequence[str] | None = None,
    ) -> tuple[str | None, str]:
        """요건 원문의 전체 흐름 — 1)완전일치 → 2)유사어 → (그 결과가
        `available_cat_ids` 범위 밖·즉 "실패"면) 3)동일범주 → 4)확대범주.

        `available_cat_ids` 를 생략하면 1)·2) 결과가 항상 "존재"하는
        것으로 보고 3)·4) 단계로 넘어가지 않는다(전역 사전만 있을 때의
        기본 동작).
        """
        want = str(keyword or "").strip()
        if not want:
            return None, "검색어 없음"

        allowed = None if available_cat_ids is None else set(available_cat_ids)

        # 1) 완전일치
        for leaf in self.leaves():
            if leaf.cat_name == want:
                if allowed is None or leaf.cat_id in allowed:
                    return leaf.cat_id, "1) 완전일치"
                return self.substitute_for(leaf.cat_id, available_cat_ids=available_cat_ids)

        # 2) 유사어 매칭 (SY·MO)
        hits = self.lookup(want, mapping_types=("SY", "MO"))
        if hits:
            target = hits[0].target_cat_id
            if allowed is None or target in allowed:
                return target, f"2) 유사어매칭({hits[0].mapping_type})"
            # ★요건 시나리오: 2)에서 찾은 카테고리가 이 범위(마켓)에는
            #   없다 — 그 카테고리를 기준으로 3)~5)(형제→조상→최근접
            #   강제지정)로 대체를 찾는다. `available_cat_ids` 가 비어
            #   있지 않은 한 여기서 **반드시** 하나가 나온다.
            sub_id, sub_step = self.substitute_for(target, available_cat_ids=available_cat_ids)
            return sub_id, f"2) 유사어매칭({hits[0].mapping_type}) 대상 없음 → {sub_step}"

        # ★요건(절대): "미검출"로 끝내지 않는다 — SY/MO 로도 못 찾았지만
        #   이 범위(마켓)에 카테고리가 하나라도 있으면, 그중 검색어와
        #   가장 비슷한 것을 강제 지정한다. 범위 제한이 없으면 리프
        #   카테고리 전체를 대상으로 한다(중간 노드보다 구체적인 값을
        #   확정하는 것이 낫다).
        pool = allowed if allowed is not None else [c.cat_id for c in self.leaves()]
        if pool:
            best = self._best_by_similarity(want, pool)
            if best:
                return best, "5) 최근접 강제지정(SY/MO 실패)"
        return None, "카테고리 자료 없음" if allowed is not None else "미검출"

    def full_path(self, cat_id: str) -> str:
        node = self.categories.get(cat_id)
        return node.full_path if node else ""

    # ── 표시용 ────────────────────────────────────────────────────

    def category_rows(self) -> list[tuple[str, str, str, int, str]]:
        return [
            (n.cat_id, n.cat_name, n.parent_id or "ROOT", n.level, n.full_path)
            for n in self.categories.values()
        ]

    def keyword_rows(self) -> list[tuple[str, str, str, str, int, str]]:
        return [
            (k.keyword_id, k.search_keyword, k.target_cat_id, k.mapping_type, k.priority, self.full_path(k.target_cat_id))
            for k in self.keywords
        ]


def build(paths: Sequence[str]) -> KeywordDB:
    """경로 목록으로 CATEGORY_MASTER + KEYWORD_DICTIONARY 를 한 번에 구축."""
    db = KeywordDB()
    db.build_from_paths(paths)
    db.build_dictionary()
    return db
