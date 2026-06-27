@echo off
echo ==============================================
echo   TOOL TAO THE CAN CUOC TU DONG
echo ==============================================

echo [1] Cai dat thu vien...
pip install pandas requests pillow deepface tf-keras

echo.
echo [2] Xoa ket qua cu...
if exist output_cards rmdir /s /q output_cards

echo.
echo [3] Khoi dong Tool...
python tool_tao_the.py

echo.
pause
