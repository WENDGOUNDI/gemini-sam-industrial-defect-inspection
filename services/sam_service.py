from threading import Lock
import numpy as np
import torch
from segment_anything import sam_model_registry, SamPredictor
from config import SAM_CHECKPOINT, SAM_TYPE

class SamEngine:
    def __init__(self):
        self.lock = Lock()
        self.predictor = None

    def load(self):
        if self.predictor is None:
            if not SAM_CHECKPOINT.is_file():
                raise FileNotFoundError(f'SAM checkpoint missing: {SAM_CHECKPOINT}. See README.')
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            model = sam_model_registry[SAM_TYPE](checkpoint=str(SAM_CHECKPOINT))
            model.to(device=device).eval()
            self.predictor = SamPredictor(model)

    def segment_many(self, rgb, boxes):
        # Predictor.set_image mutates internal state; lock covers entire batch.
        with self.lock:
            self.load()
            self.predictor.set_image(rgb)
            masks = []
            for box in boxes:
                with torch.inference_mode():
                    mask, _, _ = self.predictor.predict(box=np.asarray(box), multimask_output=False)
                masks.append(mask[0].astype(bool))
            return masks

sam_engine = SamEngine()
