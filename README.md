# 망고보드 (mango board) **v2.7.1**

> **공식 저장소명:** `Mango_Helper_AI_Board`  
> **PC 한 페이지 가이드:** **[PC_클론가이드.md](PC_클론가이드.md)** · 상세: **[PC_SETUP.md](PC_SETUP.md)**

## ★ AI보드와 별개의 독립 보드

망고보드는 **AI보드처럼 하나의 독립된 보드**입니다. AI보드의 프로그램 목록에 들어가는
하위 기능이 아닙니다.

| 구분 | AI board (`AI_Program_Main_Board`) | 망고보드 (`Mango_Helper_AI_Board`) |
|------|-----------------------------------|-----------------------------------|
| 실행 | 저장소 루트 `run.bat` | 이 폴더의 `run.bat` |
| 버전 | 루트 `VERSION.txt` | 이 폴더의 `VERSION.txt` |
| 요건문서 | 루트 `docs/일별_사용자요건/` | 이 폴더의 `docs/일별_사용자요건/` |
| 업데이트 | AI보드 자체 갱신 | 이 폴더 기준 갱신 (독립 repo `main`) |
| PC 폴더 | `D:\My_Project\AI_Program_Main_Board` | `D:\My_Project\Mango_Helper_AI_Board` |

망고보드는 AI보드의 소스를 **읽거나 수정하지 않습니다**. 같은 저장소에 폴더로
들어 있더라도 실행·버전·문서·업데이트가 모두 이 폴더 안에서만 이뤄집니다.

| 용어 | 의미 |
|------|------|
| **망고보드** | 이 보드의 한글 약칭 |
| **mango board** | 이 보드의 영문 약칭 |
| **AI board** | 기존 `AI_Program_Main_Board` (별도 보드로 그대로 유지) |

## 구성 — 순수 파이썬 프로그램

프로그램 본체는 **전부 파이썬**입니다. npm · Node.js · TypeScript · 빌드 도구가
전혀 없고, `package.json` 도 없습니다.

| 구분 | 내용 |
|------|------|
| 파이썬 소스 | `.py` 31개 · 약 1.6만 줄 (UI·자동화·테스트 전부) |
| UI | 표준 라이브러리 **tkinter** (별도 UI 프레임워크 없음) |
| 외부 패키지 | **playwright**(브라우저 자동화) · **openpyxl**(엑셀) · pytest(테스트) — `requirements.txt` |
| 그 외 import | 전부 파이썬 표준 라이브러리 (json · pathlib · subprocess · re …) |

파이썬이 아닌 파일은 **보조 역할**입니다.

| 파일 | 역할 | 왜 파이썬이 아닌지 |
|------|------|--------------------|
| `*.bat` · `*.ps1` | 실행·설치·아이콘 래퍼 | 더블클릭 실행·PC 설치는 Windows 셸이 담당 |
| `P2/extensions/themango-solution/` (JS·CSS) | 더망고 사이트용 **크롬 확장** | 브라우저 확장 규격이 JS — 파이썬(Playwright)이 이 확장을 띄워 사용 |

즉 **로직은 파이썬, 실행 편의는 배치, 브라우저 확장만 JS** 입니다.

## PC에서 빠르게 시작

```powershell
# 폴더 D:\My_Project\Mango_Helper_AI_Board 준비 후
.\망고보드_한번에설치.bat      ← ★ 이것만 실행 (clone·pip·바탕화면아이콘·확인)
.\run.bat                     ← 망고보드 실행
```

**모든 프로그램 목록:** `py -3 scripts\launch.py list`  
**개별 바로가기:** `scripts\launch\` 폴더

## 자동 반영 (아이콘 실행 시)

바탕화면 **[망고보드]** 아이콘(=`run.bat`)을 누르면 보드가 뜨기 전에 최신 버전을
스스로 확인해 반영합니다.

| 상황 | 동작 |
|------|------|
| 원격 버전이 더 높음 | `git pull`(가능하면) 또는 GitHub ZIP 으로 파일 갱신 후 실행 |
| 이미 최신 | 그대로 실행 |
| 오프라인·확인 실패 | 그대로 실행 (막지 않음) |

- 대상: 독립 repo `Mango_Helper_AI_Board` 우선, 없으면 부모 repo `main` 의
  `Mango_Helper_AI_Board/` 폴더
- `.git` 이 없어도 됩니다 (ZIP 경로). 부모 저장소 하위 폴더로 쓰는 경우엔 상위
  저장소에서 `git pull` 합니다
- **건드리지 않는 것**: `run-logs` · `output` · `.chrome-profile` · `*.xlsx` ·
  `.translate_options.json` · `.site_options.json` · `*.lnk`
- 자동갱신 없이 켜려면 `run.bat --noupdate`
- 확인만: `py -3 board\auto_update.py --check`

## 바탕화면 실행 아이콘

바탕화면에 **[망고보드]** 아이콘을 만드는 방법 (셋 중 아무거나):

| 방법 | 실행 |
|------|------|
| 설치할 때 자동 | `망고보드_한번에설치.bat` · `scripts\setup-pc.ps1` |
| 아이콘만 다시 | `망고보드_바탕화면아이콘.bat` 더블클릭 |
| 파이썬 직접 | `py -3 board\desktop_icon.py` |

- **실행파일 아이콘 1개만** 만듭니다 — `망고보드.lnk` → `run.bat` (작업 폴더 = 망고보드 루트).
- 놓을 위치는 레지스트리에서 **실제 활성 바탕화면**을 읽어 정합니다
  (OneDrive·한글 「바탕 화면」 리디렉션 포함). 여러 폴더에 중복 생성하지 않습니다.
- 여러 바탕화면 후보 + 프로젝트 폴더 사본까지 전부 만들려면
  `py -3 board\desktop_icon.py --all`.
- **작업표시줄 고정까지 자동 시도**합니다 (핀 폴더 복사 + 셸 고정 verb + 시작메뉴 등록).
  Windows 가 자동고정을 막으면 메시지로 알려주고, 아이콘 우클릭 → [작업 표시줄에 고정]
  으로 바로 하실 수 있게 시작메뉴에도 등록해 둡니다. 고정 없이 만들려면 `--no-pin`.
- 생성 로직은 `board/desktop_icon.py` (표준 라이브러리만). `.lnk` 저장만 Windows
  COM(`WScript.Shell`) 에 위임하며, PowerShell 을 `-EncodedCommand` 로 호출해
  한글 경로·이름이 깨지지 않습니다.

## 포함 프로그램

| 프로그램 | 폴더 | 역할 |
|----------|------|------|
| 망고보드 메인 | `board/` | Tkinter 탭 UI |
| P1_필터단위_마진정책적용 | `P1_필터단위_마진정책적용/` | 정책명 → 체크 행 적용확인 |
| P2_필터단위_상품수변경 | `P2_필터단위_상품수변경/` | 적용상품수 일괄 갱신 |
| P2 | `P2/` | 더망고 대량수집 |
| P3_필터_갱신 | `P3_필터_갱신/` | 저장상품수 갱신 |
| P3_필터단위_수집조건수정 | `P3_필터단위_수집조건수정/` | 수집사이트·번역옵션 리스트 선택값 일괄 적용 |
| P3_핏클상세페이지 | `P3_핏클상세페이지/` | FitCL 모델컷 10 + 디테일컷 5 |
| P5_카테고리_엑셀추출 | `P5_카테고리_엑셀추출/` | 오픈마켓 전체카테고리 → 1~6단계 분류표 엑셀 |
| P5_101_카테고리매핑_필터세부설정 | `P5_101_카테고리매핑_필터세부설정/` | 체크된 필터마다 마켓 카테고리 자동 매핑 |

레지스트리: `programs/registry.json`

## 로컬 경로 (권장)

```
D:\My_Project\Mango_Helper_AI_Board
```

## GitHub

| 저장소 | 용도 |
|--------|------|
| [Mango_Helper_AI_Board](https://github.com/waterstar21g-png/Mango_Helper_AI_Board) | **망고보드 독립 repo (목표)** |
| [AI_Program_Main_Board](https://github.com/waterstar21g-png/AI_Program_Main_Board) | 부모 repo · `main` 의 `Mango_Helper_AI_Board/` 폴더 |

독립 repo 에 소스 올리기: **`망고보드_독립저장소올리기.bat`** 더블클릭
(폴더 상태 자동 판별 — 독립 클론 / 단독 폴더 / AI보드 하위) · 상세 `GITHUB_SETUP.md`

## 구조

| 경로 | 역할 |
|------|------|
| `run.bat` / `망고보드_실행.bat` | 메인 실행 |
| `망고보드_바탕화면아이콘.bat` | 바탕화면 [망고보드] 아이콘 생성 |
| `board/desktop_icon.py` | 아이콘 생성 로직 (순수 파이썬) |
| `scripts/launch.py` | 통합 CLI 실행기 |
| `scripts/launch/` | 프로그램별 배치 바로가기 |
| `programs/registry.json` | 프로그램·경로·로그인 정의 |
| `board/app.py` | 메인 UI |
| `VERSION.txt` | 버전 단일 소스 |
| `docs/일별_사용자요건/` | 요구사항 원문 보관 |
