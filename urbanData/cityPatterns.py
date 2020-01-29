from folium import Map, LayerControl, Icon
from helper.geoJsonToFolium import geoFeatureCollectionToFoliumFeatureGroup, generateFeatureCollectionForGroups
from helper.overPassHelper import OverPassHelper
from helper.OsmDataQuery import OsmDataQuery
from helper.OsmObjectType import OsmObjectType
from helper.geoJsonHelper import unionFeatureCollections, groupBy, centerPoint
from helper.voronoiHelper import voronoiFeatureCollection
import logging
import geojson


logging.basicConfig(level=logging.INFO)

overpassFetcher = OverPassHelper()
pieschenAreaId = overpassFetcher.getAreaId("Dresden, Germany")
saxonyAreaId = overpassFetcher.getAreaId("Saxony, Germany")

map = Map(location=[51.078875, 13.728524], tiles='Open Street Map', zoom_start=15)

# TODO: improve boundary shape (something is still wrong)
logging.info("Get area boundaries")
pieschenBoundary = next(overpassFetcher.directFetch(pieschenAreaId, [OsmDataQuery(
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
stops = next(overpassFetcher.directFetch(pieschenAreaId, [stopsOsmQuery]))
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
geoFeatureCollectionToFoliumFeatureGroup(geojson.FeatureCollection(stopsByName), '#990000', pattern).add_to(map)

try:
    pattern = "5 minute walk area around stops"
    logging.info(pattern)
    file = open("out/data/timeMapsPerStop.json", encoding='UTF-8')
    timeMaps = geojson.load(file)
    geoFeatureCollectionToFoliumFeatureGroup(timeMaps, '#990000', pattern, show = False).add_to(map)
except FileNotFoundError:
    logging.error("run timeMapsRetriever to get time maps")



# (34) change-points
pattern = "Public Transport Change Points (Pattern 34)"
logging.info(pattern)

try:
    file = open("out/data/dvbChangePoints.json", encoding='UTF-8')
    changePoints = geojson.load(file)
    geoFeatureCollectionToFoliumFeatureGroup(changePoints, '#000099', pattern).add_to(map)
except FileNotFoundError:
    logging.error("run dvbRetriever to get info about change Points")
        



###################
# use buildingGroups (only for !!pieschen!!) 
# (21) at most 4 building-level

# (38) row houses

#############
# TODO: find good query
# (23) parallel streets

# (30) activity nodes

# (50) T-Crossroads


##########

pattern = "Night Life (Pattern 33)"
logging.info(pattern)
nightLifeOsmQuery = OsmDataQuery("Night Life", OsmObjectType.ALL, ['"amenity"~"bar|pub|nightclub|stripclub"'])
# TODO: add cafes with opening hour?
nightLife = next(overpassFetcher.directFetch(pieschenAreaId, [nightLifeOsmQuery]))
geoFeatureCollectionToFoliumFeatureGroup(nightLife, '#52E74B', pattern).add_to(map)


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
# TODO: use city boroughs as areas and mark them if they have a town hall ... extra ""
# TODO: use relations (also town halls) (inner and outer lines ? use type=multipolygon)
logging.info(pattern)
townHallOsmQuery = OsmDataQuery("Town Halls", OsmObjectType.ALL, ['"amenity"="townhall"'])
townHalls = next(overpassFetcher.directFetch(pieschenAreaId, [townHallOsmQuery]))
# TODO: calculating base area for each parking lot? (idealy using a annotater)
# TODO: allow setting an icon?
geoFeatureCollectionToFoliumFeatureGroup(townHalls, 'red', pattern).add_to(map)



pattern = "Health Care (Pattern 47)"
logging.info(pattern)
pharmacyQuery = OsmDataQuery("amenity health", OsmObjectType.ALL, ['"amenity"~"pharmacy"'])
healthAmenityQuery = OsmDataQuery("amenity health", OsmObjectType.ALL, ['"amenity"~"doctors"'])
healthCareQuery = OsmDataQuery("health care", OsmObjectType.ALL, ['"healthcare"~"doctor|dentist|center"', '"amenity"!~"pharmacy|doctors"'])
osmResult = overpassFetcher.directFetch(pieschenAreaId, [pharmacyQuery ,healthAmenityQuery, healthCareQuery])

healthGroups = {
    "pharmacies": next(osmResult),
    "doctors":  unionFeatureCollections(*osmResult)
    }
#TODO: get icons to work
""" icons = {
    "pharmacies": Icon(icon="pills", color='lightgray', icon_color = 'red'), 
    "doctors": Icon(icon="suitcase-doctor", color='lightgray', icon_color = 'red')
    } """
generateFeatureCollectionForGroups(healthGroups, "tab10", pattern, iconMap={}).add_to(map)



pattern = "Holy Ground (Pattern 66 & 70)"
logging.info(pattern)
holyOsmQuery = OsmDataQuery("Religious Things", OsmObjectType.ALL, ['"amenity"~"place_of_worship"'])
graveyardOsmQuery = OsmDataQuery("Cementries", OsmObjectType.ALL, ['"landuse"~"cemetery"'])
osmResult = overpassFetcher.directFetch(pieschenAreaId, [holyOsmQuery, graveyardOsmQuery])
holygrounds = {
    "places of worship": next(osmResult),
    "cementries": next(osmResult)
}
generateFeatureCollectionForGroups(holygrounds, 'copper', pattern, show = True).add_to(map)



pattern = "LocalSport (Pattern 72)"
logging.info(pattern)
sportsQuery = OsmDataQuery("Local Sport", OsmObjectType.ALL, ["sport", '"sport"!="no"' , '"opening_hours"!~"."'])
fitnessCentreQuery = OsmDataQuery("Local Sport", OsmObjectType.ALL, ['"leisure"~"fitness_centre"'])
osmResult = overpassFetcher.directFetch(pieschenAreaId, [sportsQuery, fitnessCentreQuery])
sports = next(osmResult)
fitnessCentres = next(osmResult)
geoFeatureCollectionToFoliumFeatureGroup(sports, 'green', pattern).add_to(map)
geoFeatureCollectionToFoliumFeatureGroup(fitnessCentres, 'brown', "FitnessCentres (also sports)", show=False).add_to(map)


# alternatives: leisure=sports_centre|stadium|track|pitch|horse_riding|swimming_pool|recreation_ground|golf_course
#       or club=sport


pattern = "Local grocery store (Pattern 89)"
logging.info(pattern)
groceryQuery = OsmDataQuery("Local grocery store", OsmObjectType.WAYANDNODE, ['"shop"~"convenience|butcher|pastry|bakery|supermarket"'])
grocery = next(overpassFetcher.directFetch(pieschenAreaId, [groceryQuery]))
# TODO: use style_function instead of groupBy
groceryGroups = groupBy(grocery, "shop")
generateFeatureCollectionForGroups(groceryGroups, "autumn", pattern).add_to(map)
# TODO: extra voronoi for supermarkets !


pattern = "Smoking and Gambling Areas (similar to Pattern 90)"
# TODO: try spaetis, doner und tankstellen
logging.info(pattern)
smokerOsmQuery = OsmDataQuery("smoking pubs", OsmObjectType.WAYANDNODE, ['"smoking"="yes"',"amenity"])
gamblingOsmQuery = OsmDataQuery("gambling", OsmObjectType.WAYANDNODE, ['"leisure"~"adult_gaming_centre|amusement_arcade"','"smoking"!~"yes"'])
weirdOsmAreas = overpassFetcher.directFetch(pieschenAreaId, [smokerOsmQuery, gamblingOsmQuery])
weirdAreas = unionFeatureCollections(*weirdOsmAreas)
geoFeatureCollectionToFoliumFeatureGroup(weirdAreas, 'yellow', pattern).add_to(map)


## TODO: allotments, parks, forest? (green area)
# TODO: 



## Voronoi Layers 
logging.info("Computing voronoi diagrams")

# Check for single boundary feature
voronoiBoundary = None
dresdenBorder = dresdenBoundary["features"][0]
groceryVoronoi = voronoiFeatureCollection(grocery, mask=dresdenBorder)
supermarketVoronoi = voronoiFeatureCollection(groceryGroups["supermarket"])

geoFeatureCollectionToFoliumFeatureGroup(groceryVoronoi, "#996633", "Grocery store voronois", show = False).add_to(map)
geoFeatureCollectionToFoliumFeatureGroup(supermarketVoronoi, "#0000ff", "Supermarket voronoi", show = False).add_to(map)

worshipVoronoi = voronoiFeatureCollection(holygrounds["places of worship"])
cementryVoronoi = voronoiFeatureCollection(holygrounds["cementries"])
geoFeatureCollectionToFoliumFeatureGroup(cementryVoronoi, 'grey', "cementry voronoi", show=False).add_to(map)
geoFeatureCollectionToFoliumFeatureGroup(worshipVoronoi, 'black', "Places of worship voronoi", show=False).add_to(map)

townHallVoronoi = voronoiFeatureCollection(townHalls)
geoFeatureCollectionToFoliumFeatureGroup(townHallVoronoi, 'Olive ', "cityhall voronoi", show=False).add_to(map)

doctorsVoronoi = voronoiFeatureCollection(healthGroups["doctors"])
pharmacyVoronoi = voronoiFeatureCollection(healthGroups["pharmacies"])
geoFeatureCollectionToFoliumFeatureGroup(doctorsVoronoi, 'IndianRed ', "doctors voronoi", show=False).add_to(map)
geoFeatureCollectionToFoliumFeatureGroup(pharmacyVoronoi, 'Crimson', "pharmacy voronoi", show=False).add_to(map)

LayerControl().add_to(map)

fileName = "out/maps/patternMap_Pieschen.html"
map.save(fileName)
logging.info("Map saved in {}".format(fileName))
