@echo off
chcp 65001 >nul
echo ========================================
echo 使用爬虫Profile打开Chrome
echo ========================================
echo.

set PROFILE_DIR=%cd%\chrome_profile
set PROFILE_NAME=CrawlerProfile

echo Profile目录: %PROFILE_DIR%
echo Profile名称: %PROFILE_NAME%
echo.
echo 正在启动Chrome...
echo.

"C:\Program Files\Google\Chrome\Application\chrome.exe" --user-data-dir="%PROFILE_DIR%" --profile-directory="%PROFILE_NAME%"

echo.
echo Chrome已关闭
pause

