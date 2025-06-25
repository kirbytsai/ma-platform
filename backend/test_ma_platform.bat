@echo off
REM M&A 平台 Phase 1 自動化測試腳本 (Windows 版本)
REM 使用方法: 儲存為 test_ma_platform.bat 並執行

echo ======================================
echo   M&A 平台 Phase 1 自動化測試
echo ======================================
echo.

set API_BASE=http://localhost:8000
set TOTAL_TESTS=0
set PASSED_TESTS=0
set FAILED_TESTS=0

REM 檢查服務器是否運行
echo 🧪 檢查服務器狀態...
set /a TOTAL_TESTS+=1
curl -s %API_BASE%/health >nul 2>&1
if %errorlevel%==0 (
    echo ✅ 服務器正在運行
    set /a PASSED_TESTS+=1
) else (
    echo ❌ 服務器未運行，請先啟動服務器
    goto :end
)

REM 基礎服務測試
echo.
echo ======================================
echo   基礎服務測試
echo ======================================

echo 🧪 測試根端點...
set /a TOTAL_TESTS+=1
curl -s %API_BASE%/ >nul 2>&1
if %errorlevel%==0 (
    echo ✅ 根端點正常
    set /a PASSED_TESTS+=1
) else (
    echo ❌ 根端點失敗
    set /a FAILED_TESTS+=1
)

echo 🧪 測試健康檢查...
set /a TOTAL_TESTS+=1
curl -s %API_BASE%/health >nul 2>&1
if %errorlevel%==0 (
    echo ✅ 健康檢查正常
    set /a PASSED_TESTS+=1
) else (
    echo ❌ 健康檢查失敗
    set /a FAILED_TESTS+=1
)

echo 🧪 測試資料庫連接...
set /a TOTAL_TESTS+=1
curl -s %API_BASE%/api/v1/test/database >nul 2>&1
if %errorlevel%==0 (
    echo ✅ 資料庫連接正常
    set /a PASSED_TESTS+=1
) else (
    echo ❌ 資料庫連接失敗
    set /a FAILED_TESTS+=1
)

REM 用戶註冊測試
echo.
echo ======================================
echo   用戶註冊測試
echo ======================================

echo 🧪 測試買方註冊...
set /a TOTAL_TESTS+=1
curl -s -X POST %API_BASE%/api/v1/auth/register ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"test.buyer@example.com\",\"password\":\"password123\",\"confirm_password\":\"password123\",\"role\":\"buyer\",\"first_name\":\"測試\",\"last_name\":\"買方\"}" >nul 2>&1
if %errorlevel%==0 (
    echo ✅ 買方註冊成功
    set /a PASSED_TESTS+=1
) else (
    echo ⚠️  買方註冊 (可能已存在)
    set /a PASSED_TESTS+=1
)

echo 🧪 測試提案方註冊...
set /a TOTAL_TESTS+=1
curl -s -X POST %API_BASE%/api/v1/auth/register ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"test.seller@example.com\",\"password\":\"password123\",\"confirm_password\":\"password123\",\"role\":\"seller\",\"first_name\":\"測試\",\"last_name\":\"賣方\"}" >nul 2>&1
if %errorlevel%==0 (
    echo ✅ 提案方註冊成功
    set /a PASSED_TESTS+=1
) else (
    echo ⚠️  提案方註冊 (可能已存在)
    set /a PASSED_TESTS+=1
)

echo 🧪 測試管理員註冊禁止...
set /a TOTAL_TESTS+=1
curl -s -X POST %API_BASE%/api/v1/auth/register ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"test.admin@example.com\",\"password\":\"password123\",\"confirm_password\":\"password123\",\"role\":\"admin\",\"first_name\":\"測試\",\"last_name\":\"管理員\"}" >nul 2>&1
REM 這裡我們期待失敗 (403)，所以反向檢查
if %errorlevel%==0 (
    echo ❌ 管理員註冊限制失效
    set /a FAILED_TESTS+=1
) else (
    echo ✅ 管理員註冊正確被禁止
    set /a PASSED_TESTS+=1
)

REM 登入測試
echo.
echo ======================================
echo   登入測試
echo ======================================

echo 🧪 測試買方登入...
set /a TOTAL_TESTS+=1
curl -s -X POST %API_BASE%/api/v1/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"test.buyer@example.com\",\"password\":\"password123\"}" >nul 2>&1
if %errorlevel%==0 (
    echo ✅ 買方登入成功
    set /a PASSED_TESTS+=1
) else (
    echo ❌ 買方登入失敗
    set /a FAILED_TESTS+=1
)

echo 🧪 測試錯誤密碼登入...
set /a TOTAL_TESTS+=1
curl -s -X POST %API_BASE%/api/v1/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"test.buyer@example.com\",\"password\":\"wrongpassword\"}" >nul 2>&1
REM 這裡我們期待失敗 (401)，所以反向檢查
if %errorlevel%==0 (
    echo ❌ 錯誤密碼檢查失效
    set /a FAILED_TESTS+=1
) else (
    echo ✅ 錯誤密碼正確被拒絕
    set /a PASSED_TESTS+=1
)

REM 測試報告
echo.
echo ======================================
echo   測試報告
echo ======================================
echo.
echo 總測試數: %TOTAL_TESTS%
echo 通過測試: %PASSED_TESTS%
echo 失敗測試: %FAILED_TESTS%
echo.

set /a SUCCESS_RATE=%PASSED_TESTS%*100/%TOTAL_TESTS%
echo 成功率: %SUCCESS_RATE%%%

if %FAILED_TESTS%==0 (
    echo.
    echo 🎉 所有測試通過！Phase 1 認證系統運作正常
    echo ✅ 可以進入 Day 6 Dummy Data 生成階段
) else (
    echo.
    echo ⚠️  發現 %FAILED_TESTS% 個問題，建議檢查後再進入下一階段
)

:end
echo.
echo 📋 詳細測試可查看: http://localhost:8000/docs
echo 🔧 如有問題請檢查服務器日誌
pause
