import unittest

import sys
import os

sys.path.insert(0, os.path.abspath('../..'))
from annotater.annotator import Annotator

class TestBaseAnnotator(unittest.TestCase):
    
    def test_Constructor(self):
        dataSource = {"test":1}
        writeProperty = "annotatedProperty"
        annotator = Annotator(dataSource, writeProperty)
        self.assertEquals(annotator.dataSource, dataSource)
        self.assertEquals(annotator.writeProperty, writeProperty)
    
    def test_AbstractMethod(self):
        self.assertRaises(TypeError, Annotator(None, None).annotate(None, None))


if __name__ == '__main__':
    unittest.main()