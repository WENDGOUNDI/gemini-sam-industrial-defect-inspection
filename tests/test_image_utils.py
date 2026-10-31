import io
import unittest
import numpy as np
from PIL import Image
from utils.image_utils import decode_image, defect_box, align_to_reference

class ImageUtilsTests(unittest.TestCase):
    def test_decode(self):
        b=io.BytesIO();Image.fromarray(np.zeros((32,64,3),dtype=np.uint8)).save(b,format='PNG')
        self.assertEqual(decode_image(b.getvalue()).shape,(32,64,3))
    def test_bad_upload(self):
        with self.assertRaises(ValueError):decode_image(b'not an image')
    def test_box(self):
        self.assertEqual(defect_box([100,200,500,600],100,200),[20,20,60,100])
        self.assertIsNone(defect_box([100,500,100,600],100,200))
    def test_alignment_no_features(self):
        img=np.zeros((100,100,3),dtype=np.uint8)
        aligned,why=align_to_reference(img,img)
        self.assertIsNone(aligned)

if __name__=='__main__':unittest.main()
