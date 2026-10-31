import time
import cv2
import numpy as np
import requests
from config import PIXELS_PER_MM, WEBHOOK_URL, WEBHOOK_TOKEN
from utils.image_utils import decode_image, align_to_reference, defect_box, to_jpg
from services.gemini_service import predict
from services.sam_service import sam_engine
from services.history_service import save_inspection

def inspect(reference_bytes, test_bytes, align=True):
    started = time.perf_counter()
    reference, test = decode_image(reference_bytes), decode_image(test_bytes)
    alignment = 'Not requested'
    if align:
        registered, alignment = align_to_reference(reference, test)
        if registered is not None:
            test = registered
        elif reference.shape[:2] != test.shape[:2]:
            raise ValueError(f'{alignment}. Images have different dimensions; supply aligned images or crop to same dimensions.')
        else:
            alignment += '; proceeded unaligned (results may be less reliable)'
    elif reference.shape[:2] != test.shape[:2]:
        raise ValueError('Without alignment, reference and test must have the same dimensions')
    prediction = predict(reference, test)
    height,width = test.shape[:2]
    valid = []
    for d in prediction.defects:
        box = defect_box(d.box, width, height)
        if box is not None:
            valid.append((d,box))
    if prediction.status.upper() == 'FAIL' and not valid:
        raise ValueError('Gemini returned no valid bounding boxes; retry with clearer images')
    masks = sam_engine.segment_many(test, [box for _,box in valid]) if valid else []
    annotated = test.copy()
    defects = []
    for i, ((d, box), mask) in enumerate(zip(valid,masks), 1):
        # SAM mask can encompass a whole object. This is segmented-region area, not proven defect area.
        area = int(mask.sum())
        overlay = annotated.copy()
        overlay[mask] = [235, 50, 65]
        annotated = cv2.addWeighted(overlay, 0.38, annotated, 0.62, 0)
        x1,y1,x2,y2 = box
        cv2.rectangle(annotated,(x1,y1),(x2,y2),(235,50,65),3)
        cv2.putText(annotated,f'#{i} {d.type[:22]}',(x1,max(24,y1-8)),cv2.FONT_HERSHEY_SIMPLEX,0.65,(235,50,65),2)
        defects.append({'id':i,'type':d.type,'description':d.description,'box':box,'area_px':area,'area_mm2':round(area / PIXELS_PER_MM**2,3) if PIXELS_PER_MM > 0 else None})
    if not defects:
        cv2.rectangle(annotated,(1,1),(width-2,height-2),(30,185,95),8)
    status = 'FAIL' if defects else 'PASS'
    elapsed = round(time.perf_counter()-started, 3)
    summary = prediction.summary or ('Defects found' if defects else 'No visible defects detected')
    ref_jpg, result_jpg = to_jpg(reference), to_jpg(annotated)
    uid = save_inspection(status,summary,elapsed,defects,alignment,ref_jpg,result_jpg)
    return {'id':uid,'status':status,'summary':summary,'defects':defects,'elapsed':elapsed,'alignment':alignment,'reference_jpg':ref_jpg,'result_jpg':result_jpg}

def notify_mes(result):
    if not WEBHOOK_URL:
        return 'MES webhook not configured'
    payload = {k:result[k] for k in ('id','status','summary','defects','elapsed')}
    headers = {'Authorization':f'Bearer {WEBHOOK_TOKEN}'} if WEBHOOK_TOKEN else {}
    response = requests.post(WEBHOOK_URL,json=payload,headers=headers,timeout=8)
    response.raise_for_status()
    return f'MES notified ({response.status_code})'
