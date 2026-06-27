@echo off
echo ==============================================
echo   DONG GOI TOOL TAO THE - PORTABLE VERSION
echo ==============================================

echo [1] Dang chay PyInstaller...
python -m PyInstaller --noconfirm --onedir --console --name "Tool_Tao_The" "tool_tao_the.py"

echo [2] Copying assets to dist\Tool_Tao_The...
xcopy /Y "template_config.json" "dist\Tool_Tao_The\"
xcopy /Y "blank_template.png" "dist\Tool_Tao_The\"
xcopy /Y "pic2_bg.png" "dist\Tool_Tao_The\"
xcopy /Y "hologram.png" "dist\Tool_Tao_The\"
xcopy /Y "face_landmarker.task" "dist\Tool_Tao_The\"
xcopy /Y "blaze_face_short_range.tflite" "dist\Tool_Tao_The\"
xcopy /Y "deploy.prototxt" "dist\Tool_Tao_The\"
xcopy /Y "res10_300x300_ssd_iter_140000.caffemodel" "dist\Tool_Tao_The\"
xcopy /Y "selfie_segmenter.tflite" "dist\Tool_Tao_The\"

echo [3] Copying input directories...
xcopy /E /I /Y "anh_nam_tre" "dist\Tool_Tao_The\anh_nam_tre"
xcopy /E /I /Y "anh_nam_trung" "dist\Tool_Tao_The\anh_nam_trung"
xcopy /E /I /Y "anh_nam_gia" "dist\Tool_Tao_The\anh_nam_gia"
xcopy /E /I /Y "anh_nu_tre" "dist\Tool_Tao_The\anh_nu_tre"
xcopy /E /I /Y "anh_nu_trung" "dist\Tool_Tao_The\anh_nu_trung"
xcopy /E /I /Y "anh_nu_gia" "dist\Tool_Tao_The\anh_nu_gia"

echo [4] Tao thu muc output mac dinh...
if not exist "dist\Tool_Tao_The\output_cards" mkdir "dist\Tool_Tao_The\output_cards"
if not exist "dist\Tool_Tao_The\debug" mkdir "dist\Tool_Tao_The\debug"

echo HOAN TAT!
echo Thumuc Portable cua ban nam tai: dist\Tool_Tao_The
