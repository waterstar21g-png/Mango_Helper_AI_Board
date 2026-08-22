"""P3_핏클상세페이지 단위테스트."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fitcl_catalog import REQUIRED_POSE_COUNT, validate_pose_selection  # noqa: E402
from fitcl_detail import parse_poses  # noqa: E402


def test_parse_poses_comma():
    raw = "포즈_01_정면_전신, 포즈_02_정면_상반신"
    assert parse_poses(raw) == ["포즈_01_정면_전신", "포즈_02_정면_상반신"]


def test_validate_pose_count():
    poses = [f"포즈_{i:02d}_" + "x" for i in range(1, 11)]
    # unknown pose names should fail
    ok, _ = validate_pose_selection(poses)
    assert ok is False

    from fitcl_catalog import DEFAULT_POSES

    ten = DEFAULT_POSES[:REQUIRED_POSE_COUNT]
    ok, err = validate_pose_selection(ten)
    assert ok is True
    assert err == ""

    ok, err = validate_pose_selection(ten[:5])
    assert ok is False
    assert "10" in err
