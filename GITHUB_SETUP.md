# GitHub — 망고보드(Mango_Helper_AI_Board) 저장소

**망고보드**는 GitHub 저장소 **`Mango_Helper_AI_Board`** 로 관리합니다.

| 항목 | 값 |
|------|-----|
| Repository | https://github.com/waterstar21g-png/Mango_Helper_AI_Board |
| PC 경로 | `D:\My_Project\Mango_Helper_AI_Board` |
| 상태 | ✅ 저장소 생성 완료 → **② publish는 PC에서 실행** |

---

## ② 소스 publish (PC에서 1회)

```powershell
Set-Location D:\My_Project\AI_Program_Main_Board
git pull origin main
Set-Location Mango_Helper_AI_Board
.\scripts\publish-standalone.ps1
```

## ③ PC clone · 실행

```powershell
Set-Location D:\My_Project
git clone https://github.com/waterstar21g-png/Mango_Helper_AI_Board.git
Set-Location Mango_Helper_AI_Board
.\scripts\setup-pc.ps1
.\run.bat
```

한 페이지 요약: **PC_클론가이드.md**
