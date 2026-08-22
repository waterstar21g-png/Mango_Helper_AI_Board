# 망고보드 PC 환경 가이드

**저장소:** `Mango_Helper_AI_Board` (망고보드 / mango board)  
**PC 권장 경로:** `D:\My_Project\Mango_Helper_AI_Board`

---

## 1. 코드 받기

### A. 독립 저장소 (권장 — GitHub에 repo 생성 후)

```powershell
Set-Location D:\My_Project
git clone https://github.com/waterstar21g-png/Mango_Helper_AI_Board.git
Set-Location Mango_Helper_AI_Board
```

저장소가 아직 없으면 `scripts\publish-standalone.ps1` 또는 `GITHUB_SETUP.md` 참고.

### B. 부모 저장소 `main` 에서

```powershell
Set-Location D:\My_Project
git clone -b main https://github.com/waterstar21g-png/AI_Program_Main_Board.git
Set-Location AI_Program_Main_Board\Mango_Helper_AI_Board
```

이 경우에도 망고보드는 **AI보드와 별개**로 동작합니다 — 같은 저장소에 폴더만
들어 있을 뿐, 실행·버전·업데이트는 이 폴더 안에서만 이뤄집니다.

---

## 2. 최초 1회 설정

```powershell
# PowerShell (관리자 불필요)
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\scripts\setup-pc.ps1
```

또는 수동:

```powershell
py -3 -m pip install -r requirements.txt
py -3 -m pip install -r P2\requirements.txt
```

필수: **Python 3.10+**, **Google Chrome**

---

## 3. 실행 (모든 프로그램 호출)

### 메인 보드 (탭 UI — 권장)

```powershell
.\run.bat
```

바탕화면 **망고보드** 바로가기는 `setup-pc.ps1` · `망고보드_한번에설치.bat` 실행 시
자동 생성됩니다. 아이콘만 다시 만들려면:

```powershell
.\망고보드_바탕화면아이콘.bat     # 또는 py -3 board\desktop_icon.py
```

보드 안에서는 좌측 하단 **[바탕화면 아이콘 만들기]** 버튼으로도 됩니다.
OneDrive 바탕화면·한글 「바탕 화면」 폴더까지 찾아 각각 만들고, 프로젝트 폴더에도
드래그용 사본을 둡니다.

### 개별 프로그램 바로가기

`scripts\launch\` 폴더:

| 배치 파일 | 프로그램 |
|-----------|----------|
| `00_망고보드_메인.bat` | 보드 전체 |
| `00_프로그램_목록.bat` | 목록 출력 |
| `P1_마진정책적용.bat` | P1 |
| `P2_상품수변경.bat` | P2 상품수 |
| `P2_더망고대량수집.bat` | P2 수집 |
| `P3_필터갱신.bat` | P3 필터 |
| `P3_핏클상세페이지.bat` | P3 FitCL |

### CLI 통합 실행기

```powershell
py -3 scripts\launch.py list
py -3 scripts\launch.py board
py -3 scripts\launch.py p3_fitcl --product D:\img\top.jpg --model "모델_01_..." --poses "..."
```

---

## 4. 로그인 (브라우저)

망고보드는 **Chrome CDP(포트 9222)** 에 붙습니다. P2 작업 시작 시 전용 Chrome이 자동 실행됩니다.

| 프로그램 | 로그인 |
|----------|--------|
| P1, P2, P3 필터 | **더망고** — Chrome에서 직접 로그인 |
| P3 핏클 | **FitCL** [fitcl.ai](https://fitcl.ai) — Chrome에서 로그인 후 작업 화면 |

P2 최초 1회: Chrome에 **더망고 솔루션 확장** 설치 (`P2/README.md`).

---

## 5. GitHub 업데이트

```powershell
.\scripts\pull-update.ps1
```

보드 좌측 **머지반영 업데이트**는 독립 repo `main` 기준입니다.

---

## 6. 구조 요약

```
Mango_Helper_AI_Board/          ← 망고보드 루트 (이 저장소)
├── run.bat                     ← 메인 실행
├── programs/registry.json      ← 프로그램 목록·경로
├── scripts/
│   ├── setup-pc.ps1            ← PC 최초 설정
│   ├── pull-update.ps1         ← git pull
│   ├── launch.py               ← 통합 실행기
│   └── launch/*.bat            ← 개별 바로가기
├── board/app.py                ← Tkinter UI
├── P1_필터단위_마진정책적용/
├── P2_필터단위_상품수변경/
├── P2/                         ← 더망고 대량수집
├── P3_필터_갱신/
└── P3_핏클상세페이지/
```

자세한 저장소 정의: `REPOSITORY.md`
