import io
import json
from PIL import Image
from google import genai
from google.genai import types
from config import GEMINI_MODEL
from models.schemas import InspectionPrediction

PROMPT = '''You are inspecting manufactured products. Image 1 is the approved defect-free reference; image 2 is the test image, registered to the same coordinate system when possible.
Compare their visible parts, geometry, texture and surface conditions. Detect ALL meaningful manufacturing anomalies (missing/extra parts, scratches, stains, cracks, damage, misalignment).
Ignore minor lighting/reflection variation. Do not invent defects. Give one tight bounding box per defect in TEST image coordinates, [ymin,xmin,ymax,xmax] scaled 0..1000. Describe only visible evidence, not assumptions.
If none, status PASS and empty defects. Otherwise status FAIL with one or more defects. Keep summary brief.'''

def predict(reference_rgb, test_rgb):
    client = genai.Client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[PROMPT, Image.fromarray(reference_rgb), Image.fromarray(test_rgb)],
        config=types.GenerateContentConfig(response_mime_type='application/json', response_schema=InspectionPrediction, temperature=0),
    )
    if not response.text:
        raise ValueError('Gemini returned an empty response (possibly blocked)')
    result = InspectionPrediction.model_validate_json(response.text)
    if result.status.upper() not in {'PASS','FAIL'}:
        raise ValueError('Gemini returned invalid status')
    if result.status.upper() == 'FAIL' and not result.defects:
        raise ValueError('Gemini reported FAIL but returned no defect locations')
    if result.status.upper() == 'PASS' and result.defects:
        raise ValueError('Gemini returned conflicting PASS and defect entries')
    return result
