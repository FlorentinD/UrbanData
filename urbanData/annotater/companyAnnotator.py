from dataclasses import dataclass
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
        return NotImplementedError


@dataclass
class HouseNumberRange():
    start: str
    end:   str