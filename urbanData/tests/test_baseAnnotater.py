import unittest

import sys, os
sys.path.insert(1, os.path.abspath('..'))
from annotater.annotator import BaseAnnotator

class TestBaseAnnotator(unittest.TestCase):
    
    def test_Constructor(self):
        dataSource = {"test":1}
        writeProperty = "annotatedProperty"
        annotator = BaseAnnotator(dataSource, writeProperty)
        self.assertEquals(annotator.dataSource, dataSource)
        self.assertEquals(annotator.writeProperty, writeProperty)
    
    def test_AbstractMethod(self):
        self.assertRaises(TypeError, BaseAnnotator(None, None).annotate(None, None))


if __name__ == '__main__':
    unittest.main()