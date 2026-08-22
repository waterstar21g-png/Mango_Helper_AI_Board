"""망고보드 독립성 테스트 — AI보드와 별개의 보드로 동작하는지 고정."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BOARD_DIR = Path(__file__).resolve().parents[1]
ROOT = BOARD_DIR.parent
sys.path.insert(0, str(BOARD_DIR))

import self_update  # noqa: E402
import terms  # noqa: E402

DEV_BRANCH = "cursor/mango-helper-ai-board-0c73"
AI_BOARD = "AI_Program_Main_Board"


def test_board_root_is_self_contained():
    for name in ("VERSION.txt", "run.bat", "board/app.py", "programs/registry.json"):
        assert (ROOT / name).exists(), f"망고보드 루트에 {name} 없음"


def test_self_update_targets_own_repo_main():
    assert self_update.REPO == "waterstar21g-png/Mango_Helper_AI_Board"
    assert self_update.DEFAULT_BRANCH == "main"
    assert self_update.root_dir() == ROOT


def test_version_is_read_from_own_file():
    assert self_update.local_version(ROOT) == self_update.parse_version(
        (ROOT / "VERSION.txt").read_text(encoding="utf-8")
    )


def test_terms_distinguish_ai_board():
    assert terms.APP_NAME == "Mango_Helper_AI_Board"
    assert terms.APP_SHORT_KO == "망고보드"
    assert terms.OTHER_BOARD_NAME == AI_BOARD


def test_registry_points_at_parent_main():
    reg = json.loads((ROOT / "programs" / "registry.json").read_text(encoding="utf-8"))
    assert reg["repository"] == "Mango_Helper_AI_Board"
    assert reg["parent_branch"] == "main"
    assert reg["parent_folder"] == "Mango_Helper_AI_Board"


def _live_files() -> list[Path]:
    skip_dirs = {".git", "__pycache__", "output", "run-logs", ".chrome-profile"}
    archive = ROOT / "docs" / "일별_사용자요건"
    me = Path(__file__).resolve()
    out: list[Path] = []
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in {".py", ".ps1", ".bat", ".json", ".md"}:
            continue
        if any(part in skip_dirs for part in p.parts):
            continue
        if archive in p.parents:  # 요건 원문 보관 — 당시 기록이므로 수정하지 않음
            continue
        if p.resolve() == me:
            continue
        out.append(p)
    return out


def test_no_live_reference_to_dev_branch():
    hits = [
        str(p.relative_to(ROOT))
        for p in _live_files()
        if DEV_BRANCH in p.read_text(encoding="utf-8", errors="ignore")
    ]
    assert not hits, f"개발 브랜치 참조 남음: {hits}"


# 다른 보드 이름이 문자열로 등장해도 되는 파일 — 소스를 import 하는 게 아니라
# 이름 구분(terms) 또는 원격 저장소 URL(auto_update: 부모 repo 폴백) 용도
NAME_MENTION_ALLOWED = {
    "terms.py",
    "auto_update.py",
    "test_auto_update.py",
    "test_bootstrap_bat.py",
}


def test_python_sources_do_not_reach_into_ai_board():
    hits = [
        str(p.relative_to(ROOT))
        for p in _live_files()
        if p.suffix == ".py"
        and p.name not in NAME_MENTION_ALLOWED
        and AI_BOARD in p.read_text(encoding="utf-8", errors="ignore")
    ]
    assert not hits, f"AI보드 참조 코드: {hits}"


def test_auto_update_only_uses_ai_board_as_remote_url():
    """부모 repo 이름은 원격 URL 로만 등장해야 한다 (로컬 경로·import 금지)."""
    text = (BOARD_DIR / "auto_update.py").read_text(encoding="utf-8")
    for line in text.splitlines():
        if AI_BOARD not in line:
            continue
        assert "PARENT_REPO" in line or "raw" in line or "github" in line or "#" in line
