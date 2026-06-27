# ID Photo Montage Tool

A tool designed for creating and montaging ID photos onto blank templates. It utilizes computer vision and image processing techniques to automate face detection, background removal, and layout generation for ID cards.

## Features

- **Automated Face Detection**: Uses MediaPipe and OpenCV DNN for robust face detection across different angles and lighting conditions.
- **Background Removal**: Integrates `rembg` (with MediaPipe Selfie Segmenter as fallback) to cleanly extract portraits from their original backgrounds.
- **Image Enhancement**: Features image normalization techniques like CLAHE to improve portrait quality before compositing.
- **Template Compositing**: Accurately places the processed portrait, text data (name, DOB, address, ID number), and holograms onto a predefined ID card template based on precise coordinate configurations.
- **Batch Processing**: Reads data from a connected Google Sheets document to process multiple ID cards automatically.
- **GUI Interface**: Built with Tkinter for easy configuration and execution.
- **Validation and Testing**: Includes scripts for visual regression, stress testing, and benchmark generation.

## Requirements

- Python 3.x
- Dependencies: `opencv-python`, `numpy`, `Pillow`, `mediapipe`, `pandas`, `rembg`

Install the required packages:

```bash
pip install opencv-python numpy Pillow mediapipe pandas rembg
```

## Usage

1. Configure the `template_config.json` with appropriate coordinates and settings if needed.
2. Update the `EXCEL_URL` in `tool_tao_the.py` to point to your data source.
3. Ensure the blank template (`blank_template.png`) and necessary model files (`deploy.prototxt`, `res10_300x300_ssd_iter_140000.caffemodel`, `face_landmarker.task`, `blaze_face_short_range.tflite`) are in the root directory.
4. Run the main script:

```bash
python tool_tao_the.py
```
*(Or use `run_tool.bat` on Windows)*

Processed ID cards will be saved in the `output_cards` directory.

## Project Structure

- `tool_tao_the.py`: Main execution script containing GUI and image processing logic.
- `template_config.json`: Configuration for template positioning.
- `blank_template.png`: The base ID card template.
- `benchmark_pipeline.py`, `run_final_validation.py`, etc.: Scripts for testing and validating outputs.
- `download_models.py`: Helper script to download required ML models.

## License

MIT License
