# TODO: mostly check if regexp catches all cases

import unittest

class TestAddressAnnotator(unittest.TestCase):
    
    def test_HouseNumberExtraction(self):
        self.assertTrue("TRUE".isupper())


if __name__ == '__main__':
    unittest.main()