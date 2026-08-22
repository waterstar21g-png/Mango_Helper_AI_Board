# P5_카테고리_엑셀추출

오픈마켓 **전체 카테고리**를 읽어 **카테고리분류표(1~6단계)** 엑셀로 저장합니다.

## 접근 URL

```
https://tmg1898.cafe24.com/mall/admin/admin_category_set.php?tm=F&ps_ftid=790
```

`ps_ftid` 는 검색필터마다 다릅니다. 보드 「접근 URL」 칸에 그대로 붙여넣거나
CLI 에서 `--ftid 721` 로 지정하면 됩니다.

**전용 탭에서 엽니다.** 수집조건수정 팝업(`admin_group_modify.php`) 같은 다른 창을
재사용해 덮어쓰지 않습니다. 이미 열린 카테고리설정 탭이 있으면 그 탭을 쓰고,
없으면 새 탭을 만들어 앞으로 가져옵니다.

## 동작 (스크린샷 순서)

1. 위 화면 접속 — 마켓별 매핑 행 (`tr#mapping_category_AUC20` = 옥션2.0)
2. **[전체카테고리]** 클릭
   `<a onclick="search_category('AUC20','openmarket_category_search_list_AUC20','allview');">`
3. 목록 리스트박스가 채워질 때까지 대기 (ajax, 최대 15초)
   `select#openmarket_category_search_list_AUC20`
4. 옵션 전체를 읽어 `>` 기준으로 쪼개 **1~6단계**로 정리 → 엑셀 저장

예시 — `e쿠폰/모바일상품권 > 교육/어학이용권 > 온라인교육/외국어`

| 마켓 | 구분 | 1단계 | 2단계 | 3단계 | 4단계 | 5단계 | 6단계 | 전체경로 |
|------|------|-------|-------|-------|-------|-------|-------|----------|
| 옥션2.0 | | e쿠폰/모바일상품권 | 교육/어학이용권 | 온라인교육/외국어 | | | | (원문 경로) |
| 11번가 | 국내카테고리 | 패션의류 | 남성의류 | 티셔츠 | | | | (원문 경로) |

- 안내 옵션(`- 카테고리를 선택해주세요 -`)과 중복 경로는 제외합니다
- 6단계보다 깊으면 나머지를 6단계에 합쳐 양식(6단계)을 유지하고, 최대 깊이를 로그에 남깁니다

## 마켓 코드

| 코드 | 표기 | 화면 행 |
|------|------|---------|
| `AUC20` | 옥션2.0 (기본) | `tr#mapping_category_AUC20` |
| `11ST` | 11번가 | `tr#mapping_category_11ST` |
| `GMK20` | G마켓2.0 | `tr#mapping_category_GMK20` |
| `SMART` | 스마트스토어 | `tr#mapping_category_SMART` |
| `COUP` | 쿠팡 | `tr#mapping_category_COUP` |
| `LTON` | 롯데ON | `tr#mapping_category_LTON` |
| `ALL` | **전체 마켓 일괄** | 위 6개를 순서대로 |

### 카테고리 구분 (11번가 · 롯데ON)

이 두 마켓은 화면에 구분 라디오가 있고 목록이 서로 다릅니다. **양쪽을 각각 추출**해
엑셀 `구분` 열로 나눠 담습니다.

| 마켓 | 구분 | 라디오 |
|------|------|--------|
| 11번가 | 해외카테고리 / 국내카테고리 | `input[name="openmarket_seller_type2_11ST"]` |
| 롯데ON | 해외직구 카테고리 / 일반카테고리(국내) | `input[name="openmarket_seller_type2_LTON"]` |

라디오는 같은 `label` 안의 `span` 텍스트로 찾아 **항상 클릭**합니다. 이미 체크된
구분(롯데ON 일반카테고리·11번가 해외카테고리)은 `check()` 로는 아무 일도 일어나지
않아 `onclick="change_category_list(...)"` 이 실행되지 않기 때문입니다. 클릭 후 목록
교체를 기다린 다음 [전체카테고리] 를 누릅니다.

### 구현 제외 (요건)

화면에 행이 있어도 추출하지 않습니다 — **LFMall · 머스트잇 · 쇼피 ·
큐텐(일본) · 플레이오토(EMP)**. `ALL` 에서도 제외되고, 코드로 직접 지정하면
"구현 제외 마켓입니다" 로 끝냅니다.

마켓마다 목록 select 이 `openmarket_category_search_list_<코드>` 와
`openmarket_category_search_list2_<코드>` 두 벌 있고 **보이는 쪽이 다릅니다**
(11번가·롯데ON). 롯데ON 은 두 select 의 `name` 이 같고 `display` 로만 전환되므로,
**보이는 select 을 우선**해 읽습니다. 숨은 select 에는 직전 구분의 목록이 남아 있어
그걸 읽으면 다른 구분이 누락되기 때문입니다.

구분을 바꾼 뒤에는 목록 지문(건수·첫·끝 항목)이 직전 구분과 달라질 때까지 기다립니다
(최대 15초). 끝까지 같으면 로그에 「이전 구분과 동일 — 교체 지연 가능」 을 남기고
읽은 값은 그대로 저장합니다.

## 출력

`output\카테고리분류표_<마켓>_<날짜_시각>.xlsx` (경로 지정 시 그 경로)

## CLI

```powershell
python extract_categories.py                    # 옥션2.0
python extract_categories.py --market ALL       # 6개 마켓 한 파일로
python extract_categories.py --market LTON
python extract_categories.py --out D:\out\분류표.xlsx
python extract_categories.py --from-text 목록.txt   # 브라우저 없이 텍스트 → 엑셀
```

## 보드

망고보드 **P5_카테고리_엑셀추출** 탭 — 마켓 선택 → [추출 시작] → [엑셀 열기]

## 중단

`.p5_stop` 플래그 (보드 [작업중단] 이 생성)
