# Web Application: Card Generator

Dự án đã được nâng cấp từ tool Desktop (Tkinter) lên Web Application (FastAPI + React Vite), đồng thời tích hợp **V2.1 Background Erasure Patch**.

## Cấu trúc thư mục

- `backend/`: Chứa mã nguồn FastAPI server.
  - `main.py`: Entry point API endpoint `/api/upload`, `/api/preview`, `/api/generate`.
  - `pipeline/`: Chứa các module tách lẻ (`detector.py`, `background.py`, `crop.py`, `render.py`).
- `frontend/`: Chứa mã nguồn React.
  - `src/`: Các file components React (`App.jsx`, `CanvasEditor.jsx`, `Controls.jsx`, `Upload.jsx`).

## Hướng dẫn chạy (Local)

### 1. Khởi chạy Backend (FastAPI)
Chạy file `start_backend.bat` hoặc sử dụng lệnh:
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Server sẽ lắng nghe tại `http://localhost:8000`.

### 2. Khởi chạy Frontend (React Vite)
Chạy file `start_frontend.bat` hoặc sử dụng lệnh:
```bash
cd frontend
npm run dev
```

Mở trình duyệt tại `http://localhost:3000`.

### 3. Open Browser
Trình duyệt sẽ mở giao diện sử dụng tại địa chỉ `http://localhost:3000` (nếu có Node.js).


## Cách sử dụng Web App
1. **Upload**: Kéo thả ảnh chân dung vào ô bên trái.
2. **Khung hình (Framing)**: Ở giữa là giao diện CanvasEditor. 
   - Backend sẽ tự động loại bỏ phông nền của ảnh gốc bằng công nghệ Rembg (hoặc Selfie Segmenter) và trả về ảnh tách nền chuẩn (chưa crop).
   - Bạn có thể **kéo, di chuyển, phóng to, thu nhỏ, hoặc xoay** hình người bên trong khung để căn góc tùy ý.
3. **Tuỳ chỉnh ảnh**: Ở cột bên phải, sử dụng slider để chỉnh:
   - **Brightness** (Mặc định 1.0)
   - **Contrast** (Mặc định 1.0)
   - **Saturation** (Mặc định 1.0)
4. **Tạo thẻ**: Nhấn `GENERATE CARD`. Hệ thống sẽ gửi tọa độ khung hình (`x, y, scale, rotation`) về backend để tiến hành xử lý `Background Erasure V2.1`, làm mờ print-feel (3%), body fade (100% -> 85%), bo góc cứng và chèn chữ, hologram vào phôi gốc.
5. Ảnh thành phẩm sẽ hiển thị bên dưới ô Upload để tải về.
