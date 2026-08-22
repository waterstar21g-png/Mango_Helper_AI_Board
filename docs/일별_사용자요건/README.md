# 일별_사용자요건 (SR — User Requirements Archive)

CHANGELOG와 **별도**로, 사용자가 요청한 내용을 **원문 그대로** 보관합니다.

## 용어 (망고보드)

| 약칭 | 공식명 | 비고 |
|------|--------|------|
| **망고보드** | Mango_Helper_AI_Board | 한글 약칭 |
| **mango board** | Mango_Helper_AI_Board | 영문 약칭 |
| **AI board** | AI_Program_Main_Board | 구분 대상 (기존 보드) |

정의 파일: `board/terms.py`

## 디렉터리

- 경로: `docs/일별_사용자요건/`

## 파일 생성 시점

- **Git COMMIT 시점마다** 새 파일 1건 생성 (커밋에 포함된 사용자 요구 반영분 기준).

## 파일 이름 규칙

```
SR_doc_YYYYMMDD_HHMMSS_요건요약20자이내.md
```

| 부분 | 설명 | 예 |
|------|------|-----|
| `YYYYMMDD` | 날짜 8자리 (KST) | `20260820` |
| `HHMMSS` | 시각 6자리 (24h, KST) | `151200` |
| 요약 | 요건 핵심 **20자 이내** (확장자 제외) | `신규보드생성` |

## 본문 필수 항목 (전부 포함)

### 맨 처음 4줄 (고정 형식 — 문서 최상단)

```markdown
* 최종 버전 --> (해당 프로젝트 버전)

* 로컬PC 보관   --> OK,  or Not-OK
* Vercel 배포  --> OK,  or Not-OK
* GitHUB Commit --> OK,  or Not-OK
```
