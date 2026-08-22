# P1_필터단위_마진정책적용

더망고 **필터단위 마진정책 목록**에서 체크된 행만 순차 처리합니다.

## 입력

- **정책명** — 각 행의 정책 리스트박스에서 찾을 이름

## 동작

1. 망고 필터단위 마진정책 목록 화면 연결 (또는 `--mango-url` 지정)
2. 체크박스가 **체크된 행만** 읽음
3. 행별 `select` 에서 정책명 일치 항목 선택
4. **적용확인** 클릭

## CLI

```powershell
python apply_policy.py --policy-name "할인정책A"
python apply_policy.py --policy-name "할인정책A" --mango-url "https://tmg1898.cafe24.com/..."
```

## 보드

망고보드 좌측 **P1_필터단위_마진정책적용** 탭에서 실행합니다.
