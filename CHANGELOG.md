# Changelog

## [1.0.0] - 2026-06-27

### Added
- **Production-Grade AutoMode Batching**: Implemented `BatchContext` backend architecture capable of handling 1000+ images concurrently without memory leaks.
- **Disk-Based Processing**: Images from uploads and ZIP files are now extracted directly to disk before processing to prevent RAM exhaustion.
- **Async Event Loop Offloading**: Added `asyncio.to_thread` for CPU-heavy tasks allowing continuous polling and uninterrupted UI.
- **Live Preview Adjustments**: Introduced an Adjustments UI panel in AutoMode (Brightness, Contrast, Saturation) with a real-time Preview mechanism powered by a dedicated `/api/auto_preview` endpoint.
- **Resilient Error Logging**: The batch loop will now bypass failed images, logging errors into `outputs/batch_{id}/errors.log` instead of crashing the process.
- **Streaming ZIP Downloads**: Built the `/api/download_batch` endpoint to return large ZIP structures safely.
- **Startup Auto-Scan**: Backend now detects and registers previously completed batch jobs on boot to maintain download availability after restarts.
- Added `package.json` with `concurrently` wrapper for launching both backend and frontend via `npm run dev`.

### Fixed
- Fixed critical race conditions in AutoMode `batch_progress` tracking.
- Resolved memory leaks caused by unbounded OpenCV caching and PIL instances (explicit `del` and `gc.collect()`).
- Addressed cross-batch file pollution bugs by strictly asserting bounding output directories.
- Refactored `FastAPI` instance ordering to squash the `NameError: app not defined` startup crash.
