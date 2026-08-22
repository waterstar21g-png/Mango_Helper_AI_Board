"""FitCL 모델·포즈 카탈로그 (fitcl.ai 공개 스펙 기준, UI 연동용)."""

from __future__ import annotations

# fitcl.ai — 80+ 모델, 57 포즈 (2026-06 업데이트 기준)
DEFAULT_MODELS: list[str] = [
    "모델_01_20대_여성_슬림",
    "모델_02_20대_여성_레귤러",
    "모델_03_20대_남성_슬림",
    "모델_04_20대_남성_레귤러",
    "모델_05_30대_여성_슬림",
    "모델_06_30대_여성_레귤러",
    "모델_07_30대_남성_슬림",
    "모델_08_30대_남성_레귤러",
    "모델_09_키즈_여아",
    "모델_10_키즈_남아",
    "모델_11_시니어_여성",
    "모델_12_시니어_남성",
]

DEFAULT_POSES: list[str] = [
    "포즈_01_정면_전신",
    "포즈_02_정면_상반신",
    "포즈_03_측면_전신",
    "포즈_04_측면_상반신",
    "포즈_05_후면_전신",
    "포즈_06_걷기_전신",
    "포즈_07_앉기_전신",
    "포즈_08_손주머니_상반신",
    "포즈_09_팔짱_상반신",
    "포즈_10_스냅_전신",
    "포즈_11_무릎_전신",
    "포즈_12_벽기대기_전신",
    "포즈_13_손들기_상반신",
    "포즈_14_뒤돌아_전신",
    "포즈_15_크로스_전신",
    "포즈_16_하프턴_전신",
    "포즈_17_스쿼트_전신",
    "포즈_18_점프_전신",
    "포즈_19_의자앉기_전신",
    "포즈_20_거울셀카_상반신",
]

REQUIRED_POSE_COUNT = 10
DETAIL_CUT_COUNT = 5


def validate_pose_selection(poses: list[str]) -> tuple[bool, str]:
    if len(poses) != REQUIRED_POSE_COUNT:
        return (
            False,
            f"모델포즈는 정확히 {REQUIRED_POSE_COUNT}개를 선택해야 합니다 (현재 {len(poses)}개).",
        )
    if len(set(poses)) != REQUIRED_POSE_COUNT:
        return False, "중복된 포즈가 있습니다."
    for p in poses:
        if p not in DEFAULT_POSES:
            return False, f"알 수 없는 포즈: {p}"
    return True, ""
