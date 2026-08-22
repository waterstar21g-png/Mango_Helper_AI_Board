# P2 자동 테스트

```bat
cd P2
python tests/test_save_popup_gate.py
```

`test_save_popup_gate.py` — 저장하기 후 팝업창 모달 필수 대기 회귀:

- 모달만 닫힘 ≠ 성공
- 팝업 없으면 오류 (초기화 진행 금지)
- 팝업(레이어) 뜨면 통과
- 모두저장 vs 하단 저장하기 구분
