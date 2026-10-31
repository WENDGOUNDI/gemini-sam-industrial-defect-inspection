# VisionAI Industrial Inspection — Gemini + SAM

AI-assisted visual inspection: compare a defect-free reference to a test image, localize multiple suspected defects with Gemini, segment them using SAM ViT-B, annotate results, and store inspection history.

## Setup (Python 3.11 or 3.12 recommended)

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Windows: copy .env.example .env
```

Set `GEMINI_API_KEY` in `.env`. Set `GEMINI_MODEL` to a Gemini model available to your account (default `gemini-2.5-flash`; change to your verified model name as needed). Download the official **SAM ViT-B checkpoint** (`sam_vit_b_01ec64.pth`) from the Meta Segment Anything project and put it in this folder, or set `SAM_CHECKPOINT` to its absolute path. On Windows, use a CUDA-enabled PyTorch installation if you have a compatible GPU. CPU mode works but is slower.

```bash
python app.py
```

Open http://localhost:8080.

## Features

- Server-validated uploads (NiceGUI newer `e.file.read()` and older `e.content.read()`), isolated by browser page
- Disabled inspection button until reference and test images are received and decoded
- Optional ORB/RANSAC registration with conservative rejection of unreliable transformations
- Gemini structured JSON response for multiple defects
- SAM segmentation for each proposed defect, protected by an inference lock
- Defect list, bounding boxes, segmentation overlays, runtime and optional calibrated area
- SQLite inspection history and local annotated images
- Export annotated JPG, CSV, PDF
- Batch inspection of up to 30 images from a ZIP archive
- Browser camera still capture (requires localhost or HTTPS, permission and camera)
- Optional HTTPS MES webhook (explicit button; no automatic data transfer)

## Notes and limitations

- **Prototype, not a validated industrial safety/quality gate.** Gemini detections may be inaccurate or inconsistent. Verify against labeled factory data before using for acceptance/rejection.
- SAM mask area represents the **segmented region**, not necessarily the true damaged area. `PIXELS_PER_MM` requires real calibration; leaving it at 0 disables mm² output.
- Registration is optional. If registration fails with equal-sized images, inspection continues unaligned with a warning. If dimensions differ, inspection fails rather than silently distorting images.
- Gemini image inputs are transmitted to Google's API. Obtain data-privacy approval before using sensitive factory images.
- History is stored locally in `data/` without user authentication. Add authentication, retention policies, rate limits and encrypted storage before network deployment.
- Batch mode is sequential; costs and latency scale with number of images. The SAM checkpoint is loaded on first FAIL inspection to avoid unnecessary startup overhead.
- MES webhook is a simple outbound JSON POST, not a specific MES vendor integration.
- Camera capture takes a still frame automatically after permission; it is not continuous video inspection.
- Gemini confidence scores are deliberately not fabricated. A production workflow should add human review and calibrated validation metrics.

## Troubleshooting uploads

If the upload progress shows 100% but status stays `Waiting for image`, check the server console for errors and confirm your installed NiceGUI version. The upload callbacks explicitly validate and save bytes and the inspection button only becomes enabled after both callbacks succeed.

## Final UI and startup behavior

- The reference and test image uploaders are hidden; use **Upload / Replace** to open the file picker. Only the current image preview is displayed.
- **Camera** and **Clear** remain available for both images.
- Auto-align is optional and defaults to off.
- SAM is loaded once at application startup, before NiceGUI begins serving the app. Startup will fail with a clear error if the SAM checkpoint is missing.
- The existing batch uploader, inspection history, exports, and MES integration are unchanged.
