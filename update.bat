@echo off
cd /d "%~dp0"
echo Updating Sebilis farm log from EQ logs... (takes ~2 min)
echo.
"C:\Users\Dercius\AppData\Local\Programs\Python\Python313\python.exe" farmgen.py
echo.
echo ============================================================
echo  Done. Local page (index.html) is updated - refresh browser.
echo  GitHub Pages will refresh in ~1 minute:
echo    https://buzzimij.github.io/eq-farm-log/
echo ============================================================
pause
