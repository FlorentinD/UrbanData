from dataclasses import dataclass
import re
from annotater.annotator import Annotator

class CompanyAnnotator(Annotator):
    """Annotates objects (probably buildings) with companies based on address information"""

    writeProperty = "companies"
    companyData = None

    def __init__(self, companyData):
        self.companyData = companyData

    # TODO: move annotate method

    @staticmethod
    def extractHousenumber(input):
        normal = r"^\d+\w?$"
        range = r"^(\d+\w?)-(\d+\w?)$"
        twoNumbers = r"^(\d+\w?)[\\,\/,](\d+\w?)$"
        
        # lowercase 3A to 3a and remove whitespaces between in housenumbers 
        sanitizedInput = input.lower().replace(" ", "")
        normalMatch = re.match(normal, sanitizedInput)
        if normalMatch:
            return sanitizedInput 
        
        rangeMatch = re.match(range, sanitizedInput)
        if rangeMatch:
            return HouseNumberRange(rangeMatch.group(1), rangeMatch.group(2))
        else:
            twoNumbersMatch = re.match(twoNumbers, sanitizedInput)
            if twoNumbersMatch:
                return [twoNumbersMatch.group(1), twoNumbersMatch.group(2)]
        return None
        


@dataclass
class HouseNumberRange():
    start: str
    end:   str