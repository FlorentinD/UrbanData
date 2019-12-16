from dataclasses import dataclass
import re
from geojson import FeatureCollection
from csv import DictReader
from logging import Logger

from annotater.annotator import Annotator

class CompanyAnnotator(Annotator):
    """Annotates objects (probably buildings) with companies based on address information"""

    writeProperty = "companies"
    dataSource = []
    logger = Logger("CompanAnnotator Logger")

    defaultDataSources = ["handelsregister_Dresden", "yellowPages_Dresden"]

    # TODO: also insert osmCompanies (or similar to companies like crafts)

    def __init__(self, companyData = None, postalCodes = ["01127", "01139"]):
        """companyData as pandasDf else default to result of companyScraper""" 
        # cannot use DataFrame as Housenumbers is no primitive type
        if not companyData:
            # TODO:  !!! remove duplicates (if address alike and name very similar ?)
            for fileName in self.defaultDataSources:
                with open("urbanData\scraper\companiesScraper\{}.csv".format(fileName), 'r',  encoding="utf-8") as file:
                    for row in DictReader(file, skipinitialspace=True):
                        companyDic = {k: v   for k,v in row.items()}
                        if companyDic["postalCode"] in postalCodes:
                            if not "houseNumber" in companyDic.keys():
                                # TODO: split street and houseNumber at scrape time
                                match = re.match(r"([^0-9]*)(\d.*)", companyDic["street"])
                                if match:
                                    street, housenumber = match.group(1), match.group(2)
                                    companyDic["street"] = street.replace("str.", "straße").replace("Str.","Straße")
                                    companyDic["houseNumber"] = self.extractHousenumber(housenumber)
                                    if not companyDic["houseNumber"]:
                                        # known Problems: street names containing numbers like 'Str. des 17. Juni 25/Geb. 102'
                                        #                 'OneStreet 35/OtherStreet 42'
                                        #                 'OneStreet 172 Eingang B' (could be shortened to 172B probably?)
                                        self.logger.debug("could not parse houseNumber inside {} ".format(companyDic["street"]))
                                    self.dataSource.append(companyDic)
                                if not match:
                                    self.logger.debug("{} does not contain a housenumber".format(companyDic))
         
        else:
            self.dataSource = companyData
        self.logger.info("Loaded {} companies".format(len(self.dataSource)))

    # TODO: move annotate method
    def annotate(self, building):
        # TODO: map companies to building: {name, branch, number of entrances}
        raise NotImplementedError

    @staticmethod
    def extractHousenumber(input):
        # TODO: for later usages pull this towards scrapers
        normal = r"^\d+\w?$"
        range = r"^(\d+\w?)-(\d+\w?)"
        # TODO: allow 2 a/b (expand to 2a/2b)
        # TODO: allow 2 Haus A (reduce to 2a)
        twoNumbers = r"^(\d+\w?)[\\,\/,](\d+\w?)"
        
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