# 망고보드 PC 준비 완료 안내

> **AI board 는 건드리지 않습니다.**  
> 실행 중인 `AI_Program_Main_Board` 와 **완전히 별도** 폴더·프로세스입니다.

---

## 준비된 것 (GitHub에 저장됨)

| 파일 | 역할 |
|------|------|
| `망고보드_한번에설치.bat` | PC 원클릭 설치 (이것만 실행) |
| `scripts/install-all.ps1` | clone · pip · 바로가기 · 확인 |
| `run.bat` / `망고보드_실행.bat` | 망고보드 실행 |
| `scripts/launch/` | 프로그램별 바로가기 |
| `programs/registry.json` | 전체 프로그램 목록 |
| `PC_클론가이드.md` | PC 가이드 |

---

## 경로 분리 (중요)

| 보드 | PC 폴더 | 동시 실행 |
|------|---------|-----------|
| **AI board** | `D:\My_Project\AI_Program_Main_Board` | 기존 그대로 유지 |
| **망고보드** | `D:\My_Project\Mango_Helper_AI_Board` | **별도 폴더** — AI board 와 무관 |

망고보드 설치 스크립트는 **`Mango_Helper_AI_Board` 폴더만** 사용합니다.  
`AI_Program_Main_Board` 파일은 **읽기·복사하지 않습니다** (GitHub 임시 폴더에서만 받음).

---

## PC에서 나중에 할 일 (AI board 끄지 않아도 됨)

### 1) 폴더 (이미 만드셨다면 생략)

```
D:\My_Project\Mango_Helper_AI_Board
```

### 2) bat 파일 하나 복사

부모 repo에서 이 파일만 복사해 위 폴더에 넣기:

```
Mango_Helper_AI_Board\망고보드_한번에설치.bat
```

또는 GitHub 부모 저장소 `main` 의  
`Mango_Helper_AI_Board` 폴더 전체를 받은 뒤 실행.

### 3) 더블클릭

```
D:\My_Project\Mango_Helper_AI_Board\망고보드_한번에설치.bat
```

### 4) 이후 실행

바탕화면 **망고보드** 또는 `run.bat`

---

## 아직 PC에서 안 해도 되는 것

- [ ] `publish-standalone.ps1` (독립 repo에 소스 push) — 원할 때
- [ ] 망고보드 첫 실행·로그인 테스트 — 준비 끝난 뒤

---

## 버전

`VERSION.txt` — 현재 **v1.4.2**
