from folium import Map, LayerControl
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

map = Map(location=[51.078875, 13.728524], tiles='Open Street Map', zoom_start=15)

# TODO: get boundary of area
boundary = next(overpassFetcher.directFetch(pieschenAreaId, [OsmDataQuery(
    "Area boundaries", OsmObjectType.RELATIONSHIP, ['"boundary"~"administrative"', '"name"="Pieschen"'])]))
geoFeatureCollectionToFoliumFeatureGroup(
    boundary, 'grey', "Area boundary").add_to(map)

# (16) Public transport (https://docs.traveltimeplatform.com/reference/time-map)

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


# TODO: groupby: name calculate center for each stop (and add number of stops as attribute?)
# TODO: draw time map (5min area walk radius)
geoFeatureCollectionToFoliumFeatureGroup(geojson.FeatureCollection(stopsByName), '#990000', pattern).add_to(map)


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
nightLifeOsmQuery = OsmDataQuery("Night Life", OsmObjectType.WAYANDNODE, ['"amenity"~"bar|pub|nightclub|stripclub"'])
# TODO: add cafes with opening hour?
nightLife = next(overpassFetcher.directFetch(pieschenAreaId, [nightLifeOsmQuery]))
geoFeatureCollectionToFoliumFeatureGroup(nightLife, '#52E74B', pattern).add_to(map)


pattern = "Parking lots (Pattern 22)"
logging.info(pattern)
parkingOsmQuery = OsmDataQuery("Parking Lots", OsmObjectType.WAYANDNODE, ['"amenity"="parking"'])
parkingLots = next(overpassFetcher.directFetch(pieschenAreaId, [parkingOsmQuery]))
# TODO: count parking lots on roofs/underground?
# TODO: calculating base area for each parking lot? (idealy using a annotater)
geoFeatureCollectionToFoliumFeatureGroup(parkingLots, 'grey', pattern).add_to(map)


pattern = "Town Halls (Pattern 44)"
logging.info(pattern)
townHallOsmQuery = OsmDataQuery("Town Halls", OsmObjectType.WAYANDNODE, ['"amenity"="townhall"'])
townHalls = next(overpassFetcher.directFetch(pieschenAreaId, [townHallOsmQuery]))
# TODO: calculating base area for each parking lot? (idealy using a annotater)
# TODO: allow setting an icon?
geoFeatureCollectionToFoliumFeatureGroup(townHalls, 'red', pattern).add_to(map)


pattern = "Health Care (Pattern 47)"
logging.info(pattern)
healthAmenityQuery = OsmDataQuery("amenity health", OsmObjectType.WAYANDNODE, ['"amenity"~"pharmacy|doctors"'])
healthCareQuery = OsmDataQuery("health care", OsmObjectType.WAYANDNODE, ['"healthcare"~"doctor|dentist|center"', '"amenity"!~"pharmacy|doctors"'])
# TODO: use unique union
townHalls = unionFeatureCollections(*overpassFetcher.directFetch(pieschenAreaId, [healthAmenityQuery, healthCareQuery]))
# TODO: allow setting an icon?
geoFeatureCollectionToFoliumFeatureGroup(townHalls, '#0099ff', pattern).add_to(map)

pattern = "Holy Ground (Pattern 66 & 70)"
logging.info(pattern)
holyOsmQuery = OsmDataQuery("Religious Things", OsmObjectType.WAYANDNODE, ['"amenity"~"place_of_worship"'])
graveyardOsmQuery = OsmDataQuery("Cementries", OsmObjectType.WAYANDNODE, ['"landuse"~"cemetery"'])
holyGround = unionFeatureCollections(*overpassFetcher.directFetch(pieschenAreaId, [holyOsmQuery, graveyardOsmQuery]))
geoFeatureCollectionToFoliumFeatureGroup(holyGround, 'black', pattern).add_to(map)
# TODO: try vonoi diagram here


pattern = "LocalSport (Pattern 72)"
logging.info(pattern)
sportsQuery = OsmDataQuery("Local Sport", OsmObjectType.WAYANDNODE, ["sport", '"opening hours"!~"."'])
sports = next(overpassFetcher.directFetch(pieschenAreaId, [sportsQuery]))
geoFeatureCollectionToFoliumFeatureGroup(sports, 'green', pattern).add_to(map)
# TODO: leisure=sports_centre|stadium|track|pitch|horse_riding|swimming_pool|recreation_ground|golf_course
# TODO: club=sport


pattern = "Local grocery store (Pattern 89)"
logging.info(pattern)
groceryQuery = OsmDataQuery("Local grocery store", OsmObjectType.WAYANDNODE, ['"shop"~"convenience|butcher|pastry|bakery"'])
grocery = next(overpassFetcher.directFetch(pieschenAreaId, [groceryQuery]))
# TODO: use style_function instead of groupBy
groceryGroups = groupBy(grocery, "shop")
generateFeatureCollectionForGroups(groceryGroups, "autumn", pattern).add_to(map)
#shop ~ supermarket
groceryVoronoi = voronoiFeatureCollection(grocery)
geoFeatureCollectionToFoliumFeatureGroup(groceryVoronoi, "#996633", "Grocery store voronois").add_to(map)

pattern = "Smoking and Gambling Areas (similar to Pattern 90)"
logging.info(pattern)
smokerOsmQuery = OsmDataQuery("smoking pubs", OsmObjectType.WAYANDNODE, ['"smoking"="yes"',"amenity"])
gamblingOsmQuery = OsmDataQuery("gambling", OsmObjectType.WAYANDNODE, ['"leisure"~"adult_gaming_centre|amusement_arcade"','"smoking"!~"yes"'])
weirdOsmAreas = overpassFetcher.directFetch(pieschenAreaId, [smokerOsmQuery, gamblingOsmQuery])
weirdAreas = unionFeatureCollections(*weirdOsmAreas)
geoFeatureCollectionToFoliumFeatureGroup(weirdAreas, 'yellow', pattern).add_to(map)


# (91) Inn ? 


## TODO: allotments, parks, forest?




LayerControl().add_to(map)

fileName = "out/maps/patternMap_Pieschen.html"
map.save(fileName)
logging.info("Map saved in {}".format(fileName))
