"""
P3_핏클상세페이지 — FitCL 연동 모델컷·디테일컷 추출.

입력:
  1. 소싱상품 (의류 이미지)
  2. 사진모델
  3. 모델포즈 10개

출력:
  - 모델컷 10장 (포즈당 1장)
  - 상품 디테일컷 5장

사용법:
  python fitcl_detail.py --product path/to/product.jpg --model "모델_01_..." \\
    --poses "포즈_01_...,포즈_02_...,..." 
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
P2_DIR = ROOT / "P2"
if str(P2_DIR) not in sys.path:
    sys.path.insert(0, str(P2_DIR))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from fitcl_automation import (  # noqa: E402
    DEFAULT_FITCL_URL,
    click_generate,
    extract_detail_cuts,
    navigate_fitcl,
    save_result_image,
    select_model,
    select_pose,
    upload_product_image,
    wait_generation_done,
)
from fitcl_catalog import (  # noqa: E402
    DEFAULT_MODELS,
    DEFAULT_POSES,
    DETAIL_CUT_COUNT,
    REQUIRED_POSE_COUNT,
    validate_pose_selection,
)
from fitcl_automation import DEFAULT_FITCL_URL  # noqa: E402

STOP_FLAG_PATH = Path(__file__).resolve().parent / ".fitcl_stop"
RUN_LOG_DIR = Path(__file__).resolve().parent / "run-logs"
OUTPUT_ROOT = Path(__file__).resolve().parent / "output"

ProgressFn = Callable[[str], None]


@dataclass
class RunResult:
    ok: bool = False
    model_saved: int = 0
    detail_saved: int = 0
    output_dir: str = ""
    errors: list[str] = field(default_factory=list)


def clear_stop_flag() -> None:
    try:
        STOP_FLAG_PATH.unlink(missing_ok=True)  # type: ignore[call-arg]
    except Exception:
        pass


def stop_requested() -> bool:
    return STOP_FLAG_PATH.is_file()


def _log(progress: ProgressFn | None, msg: str, *, major: bool = False) -> None:
    line = f"##MAIN##{msg}" if major else msg
    print(line, flush=True)
    if progress:
        progress(line)


def parse_poses(raw: str) -> list[str]:
    parts = [p.strip() for p in (raw or "").replace("\n", ",").split(",") if p.strip()]
    return parts


def make_output_dir(product_path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = product_path.stem[:40] or "product"
    out = OUTPUT_ROOT / f"{name}_{stamp}"
    (out / "model").mkdir(parents=True, exist_ok=True)
    (out / "detail").mkdir(parents=True, exist_ok=True)
    return out


def run_fitcl_detail(
    product_image: str | Path,
    model_name: str,
    poses: list[str],
    *,
    fitcl_url: str = "",
    output_dir: str | Path = "",
    progress: ProgressFn | None = None,
) -> RunResult:
    result = RunResult()
    clear_stop_flag()

    product_path = Path(product_image)
    if not product_path.is_file():
        result.errors.append(f"소싱상품 파일 없음: {product_path}")
        _log(progress, result.errors[0], major=True)
        return result

    model = (model_name or "").strip()
    if not model:
        result.errors.append("사진모델을 선택하세요.")
        _log(progress, result.errors[0], major=True)
        return result
    if model not in DEFAULT_MODELS:
        result.errors.append(f"알 수 없는 모델: {model}")
        _log(progress, result.errors[0], major=True)
        return result

    ok_poses, pose_err = validate_pose_selection(poses)
    if not ok_poses:
        result.errors.append(pose_err)
        _log(progress, pose_err, major=True)
        return result

    out = Path(output_dir) if output_dir else make_output_dir(product_path)
    out.mkdir(parents=True, exist_ok=True)
    (out / "model").mkdir(exist_ok=True)
    (out / "detail").mkdir(exist_ok=True)
    result.output_dir = str(out)

    meta = {
        "product": str(product_path.resolve()),
        "model": model,
        "poses": poses,
        "fitcl_url": fitcl_url or DEFAULT_FITCL_URL,
    }
    (out / "run_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    _log(progress, f"소싱상품: {product_path.name}", major=True)
    _log(progress, f"사진모델: {model}", major=True)
    _log(progress, f"모델포즈: {len(poses)}개 순차 생성", major=True)
    _log(progress, f"출력 폴더: {out}", major=True)

    try:
        import collect as p2  # noqa: WPS433
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        result.errors.append(f"의존성 로드 실패: {e}")
        _log(progress, result.errors[0], major=True)
        return result

    url = (fitcl_url or "").strip() or DEFAULT_FITCL_URL

    try:
        with sync_playwright() as pw:
            _browser, page = p2.connect_browser(pw)
            page = navigate_fitcl(page, url, progress=progress)

            if not upload_product_image(page, product_path, progress=progress):
                result.errors.append("소싱상품 업로드 실패")
                return result

            if not select_model(page, model, progress=progress):
                result.errors.append(f"사진모델 선택 실패: {model}")
                return result

            for i, pose in enumerate(poses, start=1):
                if stop_requested():
                    _log(progress, "사용자 중단", major=True)
                    break

                _log(progress, f"[{i}/{REQUIRED_POSE_COUNT}] 포즈 생성 — {pose}", major=True)
                if not select_pose(page, pose, progress=progress):
                    result.errors.append(f"포즈 선택 실패: {pose}")
                    continue

                if not click_generate(page, progress=progress):
                    result.errors.append(f"생성 실패: {pose}")
                    continue

                if not wait_generation_done(page, timeout_sec=300):
                    result.errors.append(f"생성 대기 시간 초과: {pose}")
                    continue

                dest = out / "model" / f"model_{i:02d}_{pose}.png"
                if save_result_image(page, dest, progress=progress):
                    result.model_saved += 1
                else:
                    result.errors.append(f"모델컷 저장 실패: {pose}")

                time.sleep(1)

            if stop_requested():
                result.ok = result.model_saved > 0
                return result

            _log(progress, "디테일컷 추출 단계", major=True)
            result.detail_saved = extract_detail_cuts(
                page, out, count=DETAIL_CUT_COUNT, progress=progress
            )

    except Exception as e:  # noqa: BLE001
        result.errors.append(str(e))
        _log(progress, f"실행 오류: {e}", major=True)
    finally:
        clear_stop_flag()

    result.ok = (
        result.model_saved == REQUIRED_POSE_COUNT
        and result.detail_saved >= DETAIL_CUT_COUNT
        and not result.errors
    )
    _log(
        progress,
        f"완료 — 모델컷 {result.model_saved}/{REQUIRED_POSE_COUNT} · "
        f"디테일컷 {result.detail_saved}/{DETAIL_CUT_COUNT} · {out}",
        major=True,
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="P3_핏클상세페이지 — FitCL 모델컷·디테일컷")
    parser.add_argument("--product", required=True, help="소싱상품 이미지 경로")
    parser.add_argument("--model", required=True, help="사진모델")
    parser.add_argument(
        "--poses",
        required=True,
        help=f"모델포즈 {REQUIRED_POSE_COUNT}개 (쉼표 구분)",
    )
    parser.add_argument("--fitcl-url", default="", help="FitCL URL (기본=fitcl.ai)")
    parser.add_argument("--output-dir", default="", help="출력 폴더 (기본=자동 생성)")
    parser.add_argument("--list-models", action="store_true", help="모델 목록 출력")
    parser.add_argument("--list-poses", action="store_true", help="포즈 목록 출력")
    args = parser.parse_args(argv)

    if args.list_models:
        for m in DEFAULT_MODELS:
            print(m)
        return 0
    if args.list_poses:
        for p in DEFAULT_POSES:
            print(p)
        return 0

    poses = parse_poses(args.poses)
    result = run_fitcl_detail(
        args.product,
        args.model,
        poses,
        fitcl_url=args.fitcl_url,
        output_dir=args.output_dir,
    )
    if result.errors:
        for e in result.errors:
            print(f"[오류] {e}", flush=True)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
