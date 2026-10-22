@echo off
REM ============================================================
REM  استئناف توليد الأسئلة — ألعاب أمين
REM  يشغّل مولّد الموجات من حيث توقف.
REM  اضبط AMEEN_API_SLOTS إذا أردت سرعة أقل (6 م valeurs مستقرة).
REM ============================================================
cd /d "%~dp0"

set AMEEN_API_SLOTS=6

echo.
echo   استئناف توليد الأسئلة...
echo   المنفذ الافتراضي للتزامن: %AMEEN_API_SLOTS%
echo.

REM إعادة بناء الخطط من العدد الحالي حتى لا يتكرر ما تم توليده
python tools\make_plans.py
echo.

REM تشغيل المنسّق (عملية واحدة، آمنة ضد الانقطاع)
python -u tools\run_all_waves.py --workers %AMEEN_API_SLOTS%

echo.
echo   انتهى التوليد.
pause
