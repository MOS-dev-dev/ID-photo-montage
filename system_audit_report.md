# Hệ thống "Tool Tạo Thẻ Căn Cước Tự Động" - Technical Audit Report

> [!NOTE]
> Báo cáo này được cấu trúc hóa dưới dạng tài liệu kỹ thuật dành cho AI và kỹ sư phần mềm. Nó mô tả toàn bộ luồng xử lý (pipeline), kiến trúc hệ thống, các dependency và mô hình Machine Learning đang được sử dụng trong dự án.

## 1. Tổng quan hệ thống (System Overview)
Đây là một hệ thống tự động hóa quá trình tạo hình ảnh thẻ căn cước (ID card) hàng loạt dựa trên thông tin dạng văn bản và kho ảnh có sẵn. Hệ thống sẽ chọn ảnh phù hợp, xử lý chân dung (nhận diện khuôn mặt, tách nền, chỉnh màu, làm viền mờ), sau đó dán (composite) chân dung, bóng ma (ghost image), watermark (hologram) và text lên một template thẻ (ID template).

Gần đây hệ thống đã được nâng cấp từ giao diện dòng lệnh (CLI) lên giao diện đồ họa (GUI) sử dụng Tkinter.

## 2. Kiến trúc & Các thành phần chính (Core Components)

### 2.1 File thực thi chính
- **`tool_tao_the.py`**: Trái tim của hệ thống. Chứa GUI (Tkinter), logic tải dữ liệu, đa luồng (threading), và toàn bộ Image Processing Pipeline.
- **`template_config.json`**: File cấu hình chứa tọa độ (X, Y) và kích thước của khu vực in ảnh chân dung (`main_frame`) và ảnh bóng ma (`ghost_frame`).

### 2.2 Nguồn dữ liệu (Data Sources)
- **Văn bản**: Đọc dữ liệu trực tiếp từ Google Sheets (định dạng CSV qua URL) bằng thư viện `pandas`. Chứa các trường như: ID_NUM, LAST_NAME, FIRST_NAME, MIDDLE_NAME, DOB, ADDRESS, GENDER.
- **Kho ảnh (Portrait Banks)**: Các thư mục chứa ảnh ngẫu nhiên được phân loại theo giới tính và độ tuổi: `anh_nam_tre`, `anh_nam_trung`, `anh_nam_gia`, `anh_nu_tre`...
- **Tài nguyên thiết kế (Assets)**:
  - `blank_template.png`: Phôi thẻ (đã tích hợp sẵn patch nền mờ phía sau chân dung).
  - `pic2_bg.png`: Nền phụ (nếu có).
  - `hologram.png`: Hình ảnh watermark chống giả.
  - Các file Font `.ttf` (Arial, Arial Bold) trỏ trực tiếp vào thư mục Windows Fonts.

### 2.3 Mô hình AI (Machine Learning Models)
Hệ thống sử dụng một cơ chế **Multi-stage Face Detection** (Phát hiện khuôn mặt qua nhiều lớp dự phòng) và **Background Removal** (Tách nền).

**Face Detectors (Cascade/Fallback System):**
1. **MediaPipe Face Landmarker** (`face_landmarker.task`): Ưu tiên số 1 để tìm khung khuôn mặt dựa trên landmarks.
2. **MediaPipe Face Detector** (`blaze_face_short_range.tflite`): Dự phòng nếu landmarker thất bại.
3. **OpenCV DNN Face Detector** (`deploy.prototxt`, `res10_300x300_ssd_iter_140000.caffemodel`): Fallback cuối cùng nếu MediaPipe không nhận diện được.

**Background Removal:**
1. **Rembg**: Ưu tiên sử dụng thư viện `rembg` (U^2-Net) để tách nền chất lượng cao.
2. **MediaPipe Selfie Segmenter** (`selfie_segmenter.tflite`): Fallback nếu `rembg` lỗi hoặc trả về ảnh trống.

## 3. Luồng xử lý hình ảnh (Image Processing Pipeline)

Khi bắt đầu tạo 1 thẻ, hệ thống chạy qua pipeline sau:

1. **Tìm kiếm (Lookup)**: Chọn ngẫu nhiên 1 ảnh từ kho thư mục phù hợp với Giới tính và Độ tuổi.
2. **Chuẩn hóa (Normalization)**: Áp dụng thuật toán CLAHE (Contrast Limited Adaptive Histogram Equalization) trên không gian màu LAB để cân bằng ánh sáng tự nhiên.
3. **Tách nền (Matting/Segmentation)**: Dùng Rembg hoặc MediaPipe Selfie Segmentation.
4. **Cắt cúp chân dung (Adaptive Cropping)**:
   - Dựa vào tọa độ Face Box tìm được, tính toán kích thước Portrait Box sao cho Face Width chiếm một tỷ lệ tối ưu và căn chỉnh (Eye Y) sao cho vừa vặn.
   - Resize về kích thước chuẩn theo `template_config.json`.
5. **Color Matching & Enhancement**:
   - Khử viền (Edge Cleanup & Decontamination) bằng hình thái học (Morphology) và Premultiplied Blur.
   - Match màu nền cục bộ từ template vào chân dung.
   - Giảm mạnh độ sáng (0.75), độ tương phản (0.85) và màu sắc (0.70) qua `PIL.ImageEnhance` để tạo cảm giác giống ảnh được in ra.
6. **Tạo cảm giác ảnh in (Print-feel) & Cắt góc**:
   - Áp dụng Portrait Density Reduction bằng cách trộn với bản Gaussian Blur.
   - **Hard Cut + Rounded Corners**: Cắt bo góc (radius=25) trên alpha mask để hình ảnh không bị tràn sắc cạnh ra ngoài khung xám.
7. **Tạo ảnh bóng ma (Ghost Image)**:
   - Resize chân dung (đã tách nền và bo góc) xuống kích thước nhỏ gọn (`ghost_frame`).
   - Chuyển sang Grayscale và giảm độ đục (Opacity) xuống mức 25%.
8. **Kiểm tra chất lượng (Quality Assurance)**:
   - Đo tỷ lệ "Halo" (viền xanh) xung quanh phần rìa của nhân vật. Nếu tỷ lệ Halo > 5%, in ra cảnh báo nhưng **vẫn tiếp tục tạo ảnh** (đã bỏ qua chặn lỗi).
9. **Dán thẻ (Compositing)**:
   - Dùng `alpha_composite` ghép theo thứ tự: Template -> Main Portrait -> pic2_bg -> Ghost Portrait -> Hologram.
   - Dùng `ImageDraw.Draw().text` in các trường thông tin. Riêng trường ADDRESS được in với opacity giảm để nhạt màu giống thẻ gốc.
10. **Xuất file**: Lưu vào thư mục đánh số tăng dần (ví dụ `1`, `2`...) dưới định dạng PNG (ảnh thẻ) kèm 1 file TXT chứa thông tin.

## 4. Cơ chế hoạt động của GUI (Tkinter)
- Hệ thống UI chạy trên Main Thread (event loop của Tkinter).
- Pipeline sinh thẻ được bọc trong hàm `run_generation` và chạy trên một luồng tách biệt (`threading.Thread`) để tránh treo UI (Non-blocking).
- Việc giao tiếp giữa Worker Thread và Main Thread được thực hiện qua `queue.Queue`. Main Thread liên tục poll queue (`_poll_queue`) để cập nhật Progress Bar và Log Console (scrolledtext).
- `sys.stdout` được ghi đè (redirect) để mọi câu lệnh `print` từ các hàm xử lý ảnh đều được đẩy vào Queue và hiện lên UI.

## 5. Các công cụ và tính năng kiểm thử (Test & Utility Scripts)
Trong hệ thống còn có rất nhiều script phụ phục vụ cho đo lường và phát triển:
- **Đo lường / Alignment**: `measure_template.py`, `measure_coords.py`, `measure_face_pos.py`, `find_frame.py` (giúp tìm bounding box tự động bằng OpenCV).
- **Kiểm thử (Validation/Testing)**: `benchmark_pipeline.py`, `regression_test.py`, `run_final_validation.py`.
- **Đóng gói**: `Tool_Tao_The.spec` và `build_portable.bat` dùng PyInstaller để build thành file exe.

> [!TIP]
> **Summary for ChatGPT/LLMs:**
> This is a highly robust ID card generator in Python using multi-stage ML face detectors, U^2-Net/Selfie Segmentation for background removal, and advanced alpha-compositing (with CLAHE, contamination removal, print-feel density reduction, and rounded corners). The code is multi-threaded with a Tkinter GUI. When generating new features or debugging, keep in mind the strict coordinate systems, the fallback nature of the detectors, and the thread-safe Queue logging system.
