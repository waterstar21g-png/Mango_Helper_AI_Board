# P3_설정수정_카테고리매핑초기화

검색필터 목록에서 지정한 **행 범위**의 카테고리매핑 설정을 순차적으로 **초기화**합니다.
초기화는 [설정수정] 팝업의 **[검색필터 설정삭제]** 버튼을 누르는 것과 같습니다
(버튼 이름은 망고 화면 그대로입니다).
`P3_필터단위_수집조건수정` 을 복제했고, 목록·팝업 조작은
`P5_101_카테고리매핑_필터세부설정`(`map_categories.py`) 의 검증된 로직을 재사용합니다.

## 입력

- **수집사이트명** — `select[name="site_id"]` (비우면 화면에 이미 선택된 사이트 유지)
- **작업 목록 URL** — 작업 시작 시 **[선택조건으로 검색하기]** 자동 클릭
- **작업 행 범위** — [부터]-[까지] (1부터, 양끝 포함 · 기본 1~5)

## 동작 (행 범위 안에서 순차)

1. **[설정수정]**(`onclick="market_mapping_new('<ftid>')"`) 클릭 → 팝업
   (`admin_category_set.php?tm=F&ps_ftid=<ftid>`)
2. 팝업에서 **[검색필터 설정삭제]**(`onclick="config_remove('','Y')"`) 클릭
3. 팝업 닫기
4. 다음 행

팝업이 안 열리면 팝업 URL 을 직접 열고, 삭제 버튼을 못 찾으면 `config_remove('','Y')`
를 직접 호출합니다. 실패해도 팝업은 반드시 닫고 다음 행으로 넘어갑니다.

## 몇 번째 행인지 확인

`--list-rows` (또는 보드 [행 목록 확인]) 로 삭제 없이 행 번호·ftid·필터명만 먼저
확인할 수 있습니다.

## CLI

```powershell
python reset_category_mapping.py --row-from 1 --row-to 5
python reset_category_mapping.py --site-id MUSINSA.com --row-from 11 --row-to 11
python reset_category_mapping.py --list-rows --row-from 11 --row-to 11   # 확인만
```

## 보드

망고보드 **P3_설정수정_카테고리매핑초기화** 탭 — 사이트·목록URL·행범위 입력 →
[행 목록 확인] 또는 [초기화 시작]

## 중단

`.reset_stop` 플래그 (보드 [작업중단] 이 생성)

## ⚠️ 주의

**되돌릴 수 없는 초기화 작업입니다.** 실행 전 [행 목록 확인] 으로 대상을 반드시
확인하세요.
