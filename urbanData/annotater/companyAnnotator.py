from dataclasses import dataclass
import re
from geojson import FeatureCollection
from csv import DictReader
from collections import defaultdict
from annotater.baseAnnotator import BaseAnnotator
from annotater.osmAnnotater import AddressAnnotator

class CompanyAnnotator(BaseAnnotator):
    """Annotates objects (probably buildings) with companies based on address information"""

    writeProperty = "companies"
    dataSource = []

    defaultDataSources = ["handelsregister_Dresden", "yellowPages_Dresden"]

    # TODO: also insert osmCompanies (or similar to companies like crafts)

    def __init__(self, companyData = None, postalCodes = ["01127", "01139"]):
        """companyData as pandasDf else default to result of companyScraper""" 
        # cannot use DataFrame as Housenumbers is no primitive type
        if not companyData:
            # TODO:  !!! remove duplicates (if address alike and name very similar ?)
            for fileName in self.defaultDataSources:
                with open("scraper\companiesScraper\{}.csv".format(fileName), 'r',  encoding="utf-8") as file:
                    for row in DictReader(file, skipinitialspace=True):
                        companyDic = {k: v   for k,v in row.items()}
                        if companyDic["postalCode"] in postalCodes:
                            if not "houseNumber" in companyDic.keys():
                                # TODO: split street and houseNumber at scrape time
                                match = re.match(r"([^0-9]*)(\d.*)", companyDic["street"])
                                if match:
                                    street, housenumber = match.group(1), match.group(2)
                                    companyDic["street"] = street.replace("str.", "straße").replace("Str.","Straße").strip()
                                    companyDic["houseNumber"] = self.extractHousenumber(housenumber)
                                    if not companyDic["houseNumber"]:
                                        # known Problems: street names containing numbers like 'Str. des 17. Juni 25/Geb. 102'
                                        #                 'OneStreet 35/OtherStreet 42'
                                        #                 'OneStreet 172 Eingang B' (could be shortened to 172B probably?)
                                        self.logger.debug("{}: could not parse houseNumber inside {} ".format(__name__,companyDic["street"]))
                                    else:
                                        self.dataSource.append(companyDic)
                                if not match:
                                    self.logger.debug("{}: {} does not contain a housenumber".format(__name__,companyDic))
         
        else:
            self.dataSource = companyData
        self.logger.info("{}: Loaded {} companies with a well-formed address".format(__name__, len(self.dataSource)))


    
    # TODO: move annotate method
    def annotateAll(self, buildings):
        """adds companies by matching addresses"""
        # overwrites method, as 
        # TODO: map companies to building: {name, branch, number of entrances (for relative area of building later on)}
        # TODO: loop over buildings first? (would not need to overwrite annotateAll)
        
        # TODO: replace this nested loop join (extract join condition)
        compainesAdded = 0
        for company in self.dataSource:
            companyHouseNumber =  company["houseNumber"]
            addressKey = AddressAnnotator.generateAddressKey(company["postalCode"], company["street"]) 
            findMatch = False
            for building in buildings["features"]:
                # TODO: look for values first and then check if key could match ?
                addresses = building["properties"].get("addresses")
                if addresses:
                    houseNumbers = addresses.get(addressKey)
                    if houseNumbers:
                        entrances = 0
                        if isinstance(companyHouseNumber, str):
                            if companyHouseNumber in houseNumbers:
                                entrances = 1
                        elif isinstance(companyHouseNumber, list):
                            overlappingNumbers = set(companyHouseNumber).intersection(houseNumbers)
                            entrances = len(overlappingNumbers)
                        elif isinstance(companyHouseNumber, HouseNumberRange):
                            overlappingNumbers = [n for n in houseNumbers if companyHouseNumber.start <= n <= companyHouseNumber.end]
                            entrances = len(overlappingNumbers)
                        else:
                            raise ValueError("Unexpected type for houseNumber {}".format(type(companyHouseNumber)))
                        if entrances > 0:
                            findMatch = True
                            compainesAdded += 1
                            branch = company["branch"].strip()
                            if not branch:
                                branch = "various"
                            companyEntry = (company["name"], branch, entrances)
                            if self.writeProperty in building.keys():
                                building["properties"][self.writeProperty].append(companyEntry)
                            else:
                                building["properties"][self.writeProperty] = [companyEntry]
            if not findMatch:
                self.logger.debug("{}: Could not find building for {}".format(__name__, company))
        # TODO: find out missing companies
        self.logger.info("{}: Could add {} companies".format(__name__, compainesAdded))

        return FeatureCollection(buildings)

    def annotate(self, building):
        raise NotImplementedError("Each company is mapped to one or more buildings instead of building to company")
    
    def aggregateProperties(self, buildingProperties):
        # TODO: remove duplicates here?
        entrancesPerBranch = defaultdict(int)
        for companiesPerBuilding in buildingProperties:
            # as None is not iterable
            if companiesPerBuilding:
                for _, branch, entrances in companiesPerBuilding:
                    entrancesPerBranch[branch] += entrances
        return entrancesPerBranch
    
    def aggregateToRegions(self, groups, regions):
        return self.aggregate(groups, regions, "__buildingGroups", self.aggregateGroupProperties)

    def aggregateGroupProperties(self, properties):
        entrancesPerBranch = defaultdict(int)
        for groupDic in properties:
            for branch, entrances in groupDic.items():
                entrancesPerBranch[branch] += entrances
        return entrancesPerBranch

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