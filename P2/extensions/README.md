# Chrome 확장 — 더망고 솔루션

- Web Store ID: `lgfjcapohoongednoojdaiedebgbcelp` (`manifest.json` 의 `key` 로 고정)
- 서비스 URL / 인증 KEY 자동 입력은 `P2/collect.py` 의 `ensure_mango_extension_settings()` 가 수행합니다.

## 로드 방식

P2 전용 Chrome 프로필(`P2/.chrome-profile`) 기동 시 `--load-extension` 으로 이 폴더를
넘기지만, **정품 Chrome 137+ 에서는 이 스위치가 제거되어 무시됩니다**
(크롬 로그: `--load-extension is not allowed in Google Chrome, ignoring.`).
Chromium · Chrome for Testing 에서는 그대로 동작하므로 인자는 유지합니다.

정품 Chrome 을 쓰는 경우에는 **전용 프로필에 웹스토어로 1회 설치**해야 합니다.
확장이 없으면 `P2/collect.py` 가 설치 페이지를 자동으로 띄우고
`wait_for_extension_install()` 로 설치를 기다렸다가 그대로 이어서 진행합니다.

`--disable-extensions-except` 는 넣지 않습니다 — 지정 경로 외 모든 확장을
비활성화해서 위 웹스토어 설치분까지 꺼버립니다.
