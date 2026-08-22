# 망고보드 저장소 정의 (Mango_Helper_AI_Board)

이 폴더가 **망고보드(mango board)** 의 공식 소스 루트입니다.

| 항목 | 값 |
|------|-----|
| 공식명 | **Mango_Helper_AI_Board** |
| 한글 약칭 | **망고보드** |
| 영문 약칭 | **mango board** |
| 독립 GitHub (목표) | `waterstar21g-png/Mango_Helper_AI_Board` |
| 부모 저장소 (개발 중) | `waterstar21g-png/AI_Program_Main_Board` |
| 부모 브랜치 | `main` |
| 부모 내 경로 | `Mango_Helper_AI_Board/` |

## PC 권장 경로

```
D:\My_Project\Mango_Helper_AI_Board
```

독립 저장소가 생성되면 위 경로에 **직접 clone** 하는 것이 가장 단순합니다.  
아직 독립 repo가 없으면 부모 저장소에서 `Mango_Helper_AI_Board` 폴더를 사용합니다.

## 프로그램 호출 (단일 진입점)

| 방법 | 명령 |
|------|------|
| 메인 보드 | `run.bat` |
| 통합 실행기 | `py -3 scripts\launch.py list` |
| 바로가기 배치 | `scripts\launch\*.bat` |

전체 목록: `programs/registry.json`

## AI board 와의 관계 — 별개의 독립 보드

- **AI board** = `AI_Program_Main_Board` (별도 보드로 그대로 유지, 삭제하지 않음)
- **망고보드** = 망고·FitCL 연동 프로그램만 모은 **독립 보드** — AI보드의 하위 기능이 아님
- 실행(`run.bat`)·버전(`VERSION.txt`)·요건문서(`docs/일별_사용자요건/`)·업데이트를
  모두 이 폴더 안에서 자체적으로 가짐
- AI board 소스를 import·수정하지 않음 (부모 저장소에 폴더로 함께 있어도 무관하게 동작)

## 버전

`VERSION.txt` — 단일 소스. 보드 타이틀·문서·SR 문서와 동기화.
