import pandas
import geojson
import geocoder
from OSMPythonTools.overpass import overpassQueryBuilder, Overpass

POSTAL_CODES_PIESCHEN = ['01127', '01139']

# Nomantin could not provide exact locations although openstreetmap had them (but only as a node?)
# arcgis could only project near street (but best I could find)
# bing could only find f.i. 5A and '5 A' was reduced to '5' (could be solved by removing spaces ?)
def localizeAdress(addr: str):
    location = geocoder.arcgis(addr).json
    if location['ok']:
        coord = geojson.Point(coordinates=[location["lat"], location["lng"]])
    else:
        coord = None
    return coord

# TODO: use overpass query based on given area (using address: tag)
def localizeBasedOnArea(addr: str):
    # area would be pieschen or dresden for now
    # TODO: adjust scraper to return city, housenumber, street, postcode instead of whole address
    # Problem: some buildings are only saved as ways (not single node) --> would need to take center of this?
    return

# based on a panda row from df.iterrow() (whatever type that has)
def companyToGeoJson(companyRow):
    address = "{}, {} {}".format(companyRow["street"], companyRow["postalCode"], companyRow["area"])
    coord = localizeAdress(address)
    if coord:
        if isinstance(companyRow["branch"], str) and companyRow["branch"]:
            branches = list(set(companyRow["branch"].split(';')))
        else:
            branches = []
        properties = {
            "name": companyRow["name"], 
            "branch": branches, 
            "city": companyRow["area"], 
            "postalcode": companyRow["postalCode"], 
            "street": str(companyRow["street"])
            }
        return geojson.Feature(geometry=coord, properties=properties)
    else:
        return None

def localizeCompanies(filePath: str):
    file = open(filePath + ".csv", encoding="utf-8") 
    companiesDf = pandas.read_csv(file, delimiter=',', dtype={'postalCode': str, 'branch':str})
    print(companiesDf.dtypes)
    companyFeatures = []

    # TODO: .isin cannot be used to filter on strings !?
    pieschenCompaniesDF = companiesDf[companiesDf.postalCode.str.contains('01127') | companiesDf.postalCode.str.contains('01139')]
    progress = 0 
    total_companies = len(pieschenCompaniesDF)

    for _, row in pieschenCompaniesDF.iterrows():
        if progress % 100 == 0:
            print("Localized {}/{}".format(progress, total_companies))
        geoJsonObject = companyToGeoJson(row)
        if geoJsonObject:
            companyFeatures.append(geoJsonObject)
        else:
            print("could not locate {}".format(row))
        progress +=1 
    companies = geojson.FeatureCollection(companyFeatures)

    outFile = open(filePath + "_pieschen_localised.json", 'w', newline='', encoding="utf-8")
    geojson.dump(companies, outFile, ensure_ascii=False)
    file.close
    outFile.close

#localizeCompanies("scripts\scraper\companiesScraper\yellowPages_Dresden")
localizeCompanies("scripts\scraper\companiesScraper\handelsregister_Dresden")