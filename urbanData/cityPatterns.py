from folium import Map, LayerControl, Icon
from helper.geoJsonToFolium import geoFeatureCollectionToFoliumFeatureGroup, generateFeatureCollectionForGroups
from helper.overPassHelper import OverPassHelper
from helper.OsmDataQuery import OsmDataQuery
from helper.OsmObjectType import OsmObjectType
from helper.crossRoadHelper import getCrossRoads
from helper.geoJsonHelper import unionFeatureCollections, groupBy, centerPoint, lineToPolygon
from helper.voronoiHelper import voronoiFeatureCollection
from helper.shapelyHelper import intersections
import logging
import geojson
import re

# TODO: proper coloring !!!
# TODO: get icons To work
logging.basicConfig(level=logging.INFO)

overpassFetcher = OverPassHelper()
dresdenAreaId = overpassFetcher.getAreaId("Dresden, Germany")
pieschenAreaId = overpassFetcher.getAreaId("Pieschen, Dresden, Germany")
saxonyAreaId = overpassFetcher.getAreaId("Saxony, Germany")

map = Map(location=[51.078875, 13.728524], tiles='Open Street Map', zoom_start=15)

logging.info("Get area boundaries")
pieschenBoundary = next(overpassFetcher.directFetch(dresdenAreaId, [OsmDataQuery(
    "Area boundaries", OsmObjectType.RELATIONSHIP, ['"boundary"~"administrative"', '"name"="Pieschen"'])]))
geoFeatureCollectionToFoliumFeatureGroup(
    pieschenBoundary, 'grey', "Pieschen boundary", show = False).add_to(map)

dresdenBoundary = next(overpassFetcher.directFetch(saxonyAreaId, [OsmDataQuery(
    "Area boundaries", OsmObjectType.RELATIONSHIP, ['"boundary"~"administrative"', '"name"="Dresden"'])]))
geoFeatureCollectionToFoliumFeatureGroup(
    dresdenBoundary, 'grey', "Dresden boundary", show = False).add_to(map)

#busStopsOsmQuery = OsmDataQuery("Bus stops", OsmObject.NODE, ['"highway"~"bus_stop"'])
pattern = "Public Transport (Pattern 16)"
logging.info(pattern)
stopsOsmQuery = OsmDataQuery("Public Transport stops", OsmObjectType.NODE, ['"public_transport"="stop_position"'])
stops = next(overpassFetcher.directFetch(dresdenAreaId, [stopsOsmQuery]))
stopsByName = []
for name, group in groupBy(stops, "name").items():
    center = centerPoint(group)
    # TODO: more properties?
    # TODO: maybe draw line instead of just center point?
    properties = {
        "name": name,
        "stop_positions": len(group["features"])
    }
    stopByName = geojson.Feature(geometry=center, properties=properties)
    stopsByName.append(stopByName)

# Simple stops
geoFeatureCollectionToFoliumFeatureGroup(geojson.FeatureCollection(stopsByName), '#990000', pattern, show= False).add_to(map)

try:
    pattern = "5 minute walk area around stops"
    logging.info(pattern)
    with open("out/data/timeMapsPerStop.json", encoding='UTF-8') as file:
        timeMaps = geojson.load(file)
    geoFeatureCollectionToFoliumFeatureGroup(timeMaps, '#990000', pattern, show = False).add_to(map)
    heatMapGroups = intersections(timeMaps)
    generateFeatureCollectionForGroups(heatMapGroups, "hsv", "Public Transport Heatmap", show=False).add_to(map)
except FileNotFoundError:
    logging.error("run timeMapsRetriever to get time maps")



# (34) change-points
pattern = "Public Transport Change Points (Pattern 34)"
logging.info(pattern)

try:
    with open("out/data/dvbChangePoints.json", encoding='UTF-8') as file:
        changePoints = geojson.load(file)
    geoFeatureCollectionToFoliumFeatureGroup(changePoints, '#000099', pattern, show= False).add_to(map)
except FileNotFoundError:
    logging.error("run dvbRetriever to get info about change Points")
        



###################
# use buildingGroups (only for !!pieschen!!) 
# (21) at most 4 building-level
pattern = "At most 4 Building-level (Pattern 21)"
logging.info(pattern)

try:
    with open("out/data/buildings_pieschen.json", encoding='UTF-8') as file:
        buildings = geojson.load(file)
    with open("out/data/buildingGroups_pieschen.json", encoding='UTF-8') as file:
        buildingGroups = geojson.load(file)
except FileNotFoundError:
    logging.error("run buildingComplexes to get buildings and their groups")
# use property levels for True
# use estimatedLevels for Maybe (estimated)

# as rooftop level does not count -> allow 5 instead of 4
def lessThanEqual5Levels(properties):
    levels = properties.get("levels", None)
    if levels:
        return levels <= 5
    else:
        estimation = properties.get("estimatedLevels", 42) <= 5 
        if estimation:
            return "Maybe"
        return False

buildingsByLevelRestriction = groupBy(buildings, lessThanEqual5Levels)
if len(buildingsByLevelRestriction) == 1:
    logging.warn("Only one building level found. Maybe the file is not correct. Rebuild via buildingComplexex.py !")
generateFeatureCollectionForGroups(buildingsByLevelRestriction, {"True": "#33cc33", "False": "#ff0000", 'Maybe': "DimGrey"}, pattern, show=False).add_to(map)

# (38) row houses
# TODO: more suffisticated function? (could also include building type and number of addresses)
rowHouseGroups = groupBy(buildingGroups, lambda properties: "RowHouses" if len(properties["__buildings"]) > 1 else "SingleHouses")
generateFeatureCollectionForGroups(rowHouseGroups, {"RowHouses": "#33cc33", "SingleHouses": "#ff0000"}, pattern, show=True).add_to(map)


# TODO: read pattern again, if only apartment like houses count here! (also exploit multiple addresses for bigger building)

############

logging.info("Searching for crossroads")

# ! not counting service crossroad as these are not "real" cross roads (probably way less traffic I assume)
# also excluding: link streets 
streets = next(overpassFetcher.directFetch(
    dresdenAreaId,
    [OsmDataQuery("streets", OsmObjectType.WAY, [
        '"highway"~"primary$|secondary$|tertiary$|residential$|motorway$|unclassified"']
    )]
))

crossRoads = getCrossRoads(streets)
crossRoadsByEdgeCount = groupBy(crossRoads, "edgeCount")

# TODO: points on streets with tag: junction="roundabout" can be unified to one
pattern = "T-CrossRoads (Pattern 50)"
geoFeatureCollectionToFoliumFeatureGroup(crossRoadsByEdgeCount["3"], "black", pattern, show= False).add_to(map)
generateFeatureCollectionForGroups(crossRoadsByEdgeCount, "viridis", "All CrossRoads", show= False).add_to(map)

# (23) parallel streets (crossroads with 3-4 edges (excluding bigger crossroads))

# (30) activity nodes (4 edges and some aminity/leisure/shop stuffs around)
# try just grouping of shops/leisure/amenity?


##########

pattern = "Night Life (Pattern 33)"
logging.info(pattern)
nightLifeOsmQuery = OsmDataQuery("Night Life", OsmObjectType.ALL, ['"amenity"~"bar|pub|nightclub|stripclub"'])
nightLife = next(overpassFetcher.directFetch(dresdenAreaId, [nightLifeOsmQuery]))
geoFeatureCollectionToFoliumFeatureGroup(nightLife, '#52E74B', pattern, show= False).add_to(map)


""" 
# Pattern was decided to be not considerable due to parking at the side of the road which are not marked in openStreetMap
pattern = "Parking lots (Pattern 22)"
# TODO: probably just delete
logging.info(pattern)
parkingOsmQuery = OsmDataQuery("Parking Lots", OsmObjectType.WAYANDNODE, ['"amenity"="parking"'])
parkingLots = next(overpassFetcher.directFetch(pieschenAreaId, [parkingOsmQuery]))
# TODO: count parking lots on roofs/underground?
# TODO: calculating base area for each parking lot? (idealy using a annotater)
geoFeatureCollectionToFoliumFeatureGroup(parkingLots, 'grey', pattern).add_to(map) """


pattern = "Town Halls (Pattern 44)"
logging.info(pattern)
townHallOsmQuery = OsmDataQuery("Town Halls", OsmObjectType.ALL, ['"amenity"="townhall"'])
townHalls = next(overpassFetcher.directFetch(dresdenAreaId, [townHallOsmQuery]))

boroughs = next(overpassFetcher.directFetch(dresdenAreaId, [OsmDataQuery(
    "Dreasen boundaries", OsmObjectType.RELATIONSHIP, ['"boundary"~"administrative"', 'name', '"name:prefix"="Ortsamtsbereich"'])]))

# convert lines to polygons for better visualization
boroughs = geojson.FeatureCollection([geojson.Feature(
    geometry=lineToPolygon(feature["geometry"]), 
    properties=feature["properties"]
    ) 
    for feature in boroughs["features"]])

generateFeatureCollectionForGroups(
    {"areas": boroughs, "town halls": townHalls}, 
    ["grey", "red"], 
    pattern, 
    show= False).add_to(map)



pattern = "Health Care (Pattern 47)"
logging.info(pattern)
pharmacyQuery = OsmDataQuery("amenity health", OsmObjectType.ALL, ['"amenity"~"pharmacy"'])
healthAmenityQuery = OsmDataQuery("amenity health", OsmObjectType.ALL, ['"amenity"~"doctors"'])
healthCareQuery = OsmDataQuery("health care", OsmObjectType.ALL, ['"healthcare"~"doctor|dentist|center"', '"amenity"!~"pharmacy|doctors"'])
osmResult = overpassFetcher.directFetch(dresdenAreaId, [pharmacyQuery ,healthAmenityQuery, healthCareQuery])

healthGroups = {
    "pharmacies": next(osmResult),
    "doctors":  unionFeatureCollections(*osmResult)
    }
#TODO: get icons to work
""" icons = {
    "pharmacies": Icon(icon="pills", color='lightgray', icon_color = 'red'), 
    "doctors": Icon(icon="suitcase-doctor", color='lightgray', icon_color = 'red')
    } """
generateFeatureCollectionForGroups(healthGroups, "tab10", pattern, iconMap={}, show= False).add_to(map)



pattern = "Holy Ground (Pattern 66 & 70)"
logging.info(pattern)
holyOsmQuery = OsmDataQuery("Religious Things", OsmObjectType.ALL, ['"amenity"~"place_of_worship"'])
graveyardOsmQuery = OsmDataQuery("Cementries", OsmObjectType.ALL, ['"landuse"~"cemetery"'])
osmResult = overpassFetcher.directFetch(dresdenAreaId, [holyOsmQuery, graveyardOsmQuery])
holygrounds = {
    "places of worship": next(osmResult),
    "cementries": next(osmResult)
}
generateFeatureCollectionForGroups(holygrounds, 'copper', pattern, show = False).add_to(map)



pattern = "LocalSport (Pattern 72)"
logging.info(pattern)
sportsQuery = OsmDataQuery("Local Sport", OsmObjectType.ALL, ["sport", '"sport"!="no"' , '"opening_hours"!~"."'])
fitnessCentreQuery = OsmDataQuery("Local Sport", OsmObjectType.ALL, ['"leisure"~"fitness_centre"'])
osmResult = overpassFetcher.directFetch(dresdenAreaId, [sportsQuery, fitnessCentreQuery])
sports = next(osmResult)
fitnessCentres = next(osmResult)
geoFeatureCollectionToFoliumFeatureGroup(sports, 'green', pattern, show= False).add_to(map)
geoFeatureCollectionToFoliumFeatureGroup(fitnessCentres, 'brown', "FitnessCentres (also sports)", show=False).add_to(map)


# alternatives: leisure=sports_centre|stadium|track|pitch|horse_riding|swimming_pool|recreation_ground|golf_course
#       or club=sport


pattern = "Local grocery store (Pattern 89)"
logging.info(pattern)
groceryQuery = OsmDataQuery("Local grocery store", OsmObjectType.ALL, ['"shop"~"convenience|butcher|pastry|bakery|supermarket"'])
grocery = next(overpassFetcher.directFetch(dresdenAreaId, [groceryQuery]))
# TODO: use style_function instead of groupBy (or list of colors)
groceryGroups = groupBy(grocery, "shop")
generateFeatureCollectionForGroups(groceryGroups, "autumn", pattern, show=False).add_to(map)



def openAtMidnight(openingHours):
    if openingHours == "24/7":
        return True
    else:
        matches = re.findall(r"(\d+):(\d+)\s*-\s*(\d+):(\d+)", openingHours)
        for openingHour, _, closingHour, _ in matches:
            # has open over midnight 
            if int(openingHour) > int(closingHour):
                return True
        if not matches:
            matches = re.findall(r"(\d+)(:\d+)\+", openingHours)
            if matches:
                # TODO: 09:00+ -> maybe open at midnight even (could be extra group)
                return True
            else:
                logging.debug(openingHours)
        return False

pattern = "Late opening hours (similar to Pattern 90 Bierhalle??)"
logging.info(pattern) 

# tankstellen: amenity=fuel
# cuisine 	kebab (but could be included by open at midnight)


# TODO: also exclude bars and pubs?
# general problem: opening hours must be filled in and valid
thingsWithOpeningHour = next(overpassFetcher.directFetch(dresdenAreaId, [OsmDataQuery("Midnight things", OsmObjectType.ALL, 
['"opening_hours"', '"amenity"!~"parking|atm|hospital|charging_station|toilets|car_|vending_|bank"'])]))


midnightThings = []
for feature in thingsWithOpeningHour["features"]:
    openingHours = feature["properties"]["opening_hours"]
    if openAtMidnight(openingHours):
        midnightThings.append(feature)

midnightThings = geojson.FeatureCollection(midnightThings)
geoFeatureCollectionToFoliumFeatureGroup(midnightThings, '#000066', pattern).add_to(map)

#smokerOsmQuery = OsmDataQuery("smoking pubs", OsmObjectType.WAYANDNODE, ['"smoking"="yes"',"amenity"])
#gamblingOsmQuery = OsmDataQuery("gambling", OsmObjectType.WAYANDNODE, ['"leisure"~"adult_gaming_centre|amusement_arcade"','"smoking"!~"yes"'])
#weirdOsmAreas = overpassFetcher.directFetch(dresdenAreaId, [smokerOsmQuery, gamblingOsmQuery])
#weirdAreas = unionFeatureCollections(*weirdOsmAreas)
#geoFeatureCollectionToFoliumFeatureGroup(weirdAreas, 'yellow', pattern, show=False).add_to(map)


## TODO: allotments, parks, forest? (green area)
# TODO: 



## Voronoi Layers 
logging.info("Computing voronoi diagrams")

# Check for single boundary feature
voronoiBoundary = None
dresdenBorder = dresdenBoundary["features"][0]
groceryVoronoi = voronoiFeatureCollection(grocery, mask=dresdenBorder)
supermarketVoronoi = voronoiFeatureCollection(groceryGroups["supermarket"], mask=dresdenBorder)

geoFeatureCollectionToFoliumFeatureGroup(groceryVoronoi, "#996633", "Grocery store voronois", show = False).add_to(map)
geoFeatureCollectionToFoliumFeatureGroup(supermarketVoronoi, "#0000ff", "Supermarket voronoi", show = False).add_to(map)

worshipVoronoi = voronoiFeatureCollection(holygrounds["places of worship"], mask=dresdenBorder)
cementryVoronoi = voronoiFeatureCollection(holygrounds["cementries"], mask=dresdenBorder)
geoFeatureCollectionToFoliumFeatureGroup(cementryVoronoi, 'grey', "cementry voronoi", show=False).add_to(map)
geoFeatureCollectionToFoliumFeatureGroup(worshipVoronoi, 'black', "Places of worship voronoi", show=False).add_to(map)

townHallVoronoi = voronoiFeatureCollection(townHalls, mask=dresdenBorder)
geoFeatureCollectionToFoliumFeatureGroup(townHallVoronoi, 'Olive ', "cityhall voronoi", show=False).add_to(map)

doctorsVoronoi = voronoiFeatureCollection(healthGroups["doctors"], mask=dresdenBorder)
pharmacyVoronoi = voronoiFeatureCollection(healthGroups["pharmacies"], mask=dresdenBorder)
geoFeatureCollectionToFoliumFeatureGroup(doctorsVoronoi, 'IndianRed ', "doctors voronoi", show=False).add_to(map)
geoFeatureCollectionToFoliumFeatureGroup(pharmacyVoronoi, 'Crimson', "pharmacy voronoi", show=False).add_to(map)

LayerControl().add_to(map)

fileName = "out/maps/patternMap_Pieschen.html"
map.save(fileName)
logging.info("Map saved in {}".format(fileName))
