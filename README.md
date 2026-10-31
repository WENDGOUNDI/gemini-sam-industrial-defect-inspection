# Gemini + SAM For Industrial Defect Inspection
AI-powered industrial visual inspection using Google Gemini for defect detection and Meta Segment Anything (SAM) for pixel-level segmentation.
# VisionAI — Industrial Defect Inspection with Gemini & SAM

AI-powered visual inspection application combining **Google Gemini** and **Meta Segment Anything Model (SAM)** for manufacturing defect detection, localization, and segmentation.
We used MVTEC dataset downloaded from kaggle for testing the implemented system.

## Overview

VisionAI compares a test image against a defect-free reference image to identify manufacturing anomalies. It leverages Gemini's multimodal reasoning capabilities to detect and describe potential defects, while SAM generates pixel-level segmentation masks of the identified regions.

The application provides an interactive web interface built with NiceGUI.

## Key Features

- **Reference-Based Inspection:** Compare test images against defect-free reference images.
- **AI Defect Detection:** Use Gemini to identify, describe, and localize potential manufacturing defects.
- **Multi-Defect Detection:** Identify multiple defects within a single image.
- **Pixel-Level Segmentation:** Use SAM to generate masks for detected regions.
- **Optional Image Alignment:** OpenCV-based image registration for geometric alignment.
- **Visual Inspection Results:** Display PASS/FAIL status, annotated images, defect details, and processing time.
- **Defect Measurement:** Calculate segmented areas in pixels, with optional physical calibration.
- **Inspection History:** Store and review previous inspections.
- **Batch Inspection:** Process multiple test images.
- **Report Export:** Export inspection results and annotated images in PDF or CSV.
- **Camera Support:** Capture images directly through the web interface.

## AI Inspection Pipeline

```text
Reference Image + Test Image
             |
             v
   Optional Image Alignment
             |
             v
      Google Gemini
  Defect Detection & Localization
             |
             v
      Bounding Boxes
             |
             v
    Segment Anything (SAM)
     Defect Segmentation
             |
             v
       Inspection Results
  PASS/FAIL | Masks | Defect Details
```

Gemini performs semantic image comparison and defect localization. SAM uses the generated bounding boxes to segment suspected defect regions.

## Technology Stack

| Technology | Purpose |
|---|---|
| Google Gemini | Multimodal defect detection and localization |
| Meta SAM (ViT-B) | Image segmentation |
| PyTorch | Model inference |
| OpenCV | Image processing and alignment |
| NiceGUI | Web application interface |
| SQLite | Inspection history |
| Python | Backend implementation |

## Installation

**1. Clone the repository**

```bash
git clone https://github.com/WENDGOUNDI/gemini-sam-industrial-defect-inspection.git
cd gemini-sam-industrial-defect-inspection
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

**3. Configure environment variables**

Create a `.env` file using `.env.example` and configure your Gemini API key, model name, and SAM checkpoint path.

```env
GEMINI_API_KEY=your_api_key
GEMINI_MODEL=your_supported_gemini_model
SAM_CHECKPOINT=./sam_vit_b_01ec64.pth
```

Download the compatible SAM ViT-B checkpoint from the official [Segment Anything repository](https://github.com/facebookresearch/segment-anything).

Download MVTEC dataset from kaggle [MVTEC Dataset](https://www.kaggle.com/datasets/ipythonx/mvtec-ad).

**4. Run the application**

```bash
python app.py
```

Open `http://localhost:8080` in your browser.

## Usage

1. Upload a defect-free reference image.
2. Upload a test image or capture one using the camera.
3. Optionally enable image alignment.
4. Click **START INSPECTION**.
5. Review detected defects, segmentation masks, and inspection metrics.
6. Export results or review inspection history.

## Application Demo
#### Bottle Inspection
<img width="1350" height="1587" alt="Image" src="https://github.com/user-attachments/assets/6acc9886-a0cb-4c60-b438-3dcb9840880b" />

#### Cable Inspection
<img width="1350" height="1587" alt="Image" src="https://github.com/user-attachments/assets/33e0b595-9456-416f-91af-97417ea9f551" />

#### Resistor Inspection
<img width="1350" height="1708" alt="Image" src="https://github.com/user-attachments/assets/d1a382c5-123e-45a0-a870-211643e85c9e" />

#### Tile Inspection
<img width="1350" height="1587" alt="Image" src="https://github.com/user-attachments/assets/457fb01f-41d3-47b5-ab03-dec68c1d4247" />

#### **Tile** Inspection
<img width="1350" height="1708" alt="Image" src="https://github.com/user-attachments/assets/aa9d5dc8-ff85-42cb-ab2d-a84f079b17c8" />

## Notes

VisionAI is a prototype demonstrating the integration of multimodal foundation models and image segmentation for industrial visual inspection. Detection and segmentation accuracy depend on image quality, model performance, and inspection conditions. Production deployment requires validation against representative manufacturing datasets.

## License

Add a license file if you intend to distribute the project under an open-source license.
