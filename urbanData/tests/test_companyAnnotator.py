# TODO: Class for annotating osm-Buildings with "companies" property containing names *and area percentage of building
import unittest

import sys, os
sys.path.insert(1, os.path.abspath('..'))

from annotater.companyAnnotator import CompanyAnnotator, HouseNumberRange

class TestCompanyAnnotator(unittest.TestCase):

    def test_HouseNumberExtraction(self):
        test_cases = {" 8a ": "8a", "8A": "8a", "8/10": ["8", "10"],
                        "8a/ 9f": ["8a", "9f"], "8 - 10": HouseNumberRange("8", "10"),
                        "a": None, "8a - 10f": HouseNumberRange("8a", "10f"), "1a  1": None}

        for input, expectedResult in test_cases.items():
            result = CompanyAnnotator.extractHousenumber(input)
            self.assertEquals(result, expectedResult)
    

# TODO: mostly check if regexp catches all cases


if __name__ == '__main__':
    unittest.main()

