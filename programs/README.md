# programs — 망고보드 프로그램 레지스트리

`registry.json` 에 망고보드 전체 프로그램 목록·실행 경로가 정의되어 있습니다.

## PC에서 호출

```powershell
# 목록 보기
py -3 scripts\launch.py list

# 망고보드 메인
py -3 scripts\launch.py board

# 개별 프로그램 (폴더로 이동 후 run.bat)
py -3 scripts\launch.py p3_fitcl
```

또는 `scripts\launch\` 아래 배치 파일을 더블클릭하세요.
