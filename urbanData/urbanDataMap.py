import json
import folium
from matplotlib import cm
from OSMPythonTools.nominatim import Nominatim
from folium.plugins.measure_control import MeasureControl

from helper.geoJsonHelper import groupBy
from helper.geoJsonToFolium import generateFeatureCollection
from helper.overPassHelper import OverPassHelper
from helper.OsmObjectType import OsmObjectType as OsmObject
from helper.OsmDataQuery import OsmDataQuery

# TODO: groupby on either amenity or building? (overlapping) (layers based on multiple tags not on single tag)
# TODO: layers Safety, Health, Leisure, Commercial (shops, craft, building manaufture, ...), Religion,

# postfix for f.i. file_names
areaName = "pieschen"
# area to query
pieschen = Nominatim().query('Pieschen, Dresden, Germany')

streetsSelector = [
    'highway~"primary|primary_link|secondary|secondary_link|tertiary|tertiary_link|residential|service|motorway|unclassified"']
buildingsSelector = ['building~"industrial|cementry|school|commercial|office|kindergarten|manufacture|power|church|hotel|public|residential|supermarket|shop|ambulance-station|chapel|sports_centre|retail"',
                     "amenity!~'.'", "leisure!~'.'"]
landuseSelector = ['landuse~"industrial|civic_admin|commercial|retail"',
                   "amenity!~'.'", "leisure!~'.'"]
leisureSelector = ['leisure']
railwaySelector = ['railway~"tram|rail"']
# TODO: probably split into different layers
amenitySelector = ['amenity~"restaurant|cinema|pharmacy|post_office|pub|fast_food|biergarten|cafe|dentist|police|place_of_worship|ice_cream|doctors|theatre|library|gambling|music_school|social_facility|marketplace|fire_station|townhall|nightclub|community_centre|social_club"', 'leisure!~"."']
shopSelector = ['shop', 'leisure!~"."',
                'building!~"."', 'amenity!~"."']
craftSelector = ['craft', 'leisure!~"."', 'shop!~"."',
                 'building!~"."', 'amenity!~"."']


# add openDataDresden mapping (obsolete)
# objectTypeTagMapping = {
#     "landnutzung1": "kuek_kl", "landnutzung2": "textstring"}

# openDataDresdenDir = "out/data/openDataDresden/"
# openDataDresdenFiles = {"landnutzung1": "{}nutzungsarten_1.geojson".format(
#     openDataDresdenDir), "landnutzung2": "{}nutzungsarten_2.geojson".format(openDataDresdenDir)}

osmQueries = [OsmDataQuery("streets", OsmObject.WAY, streetsSelector, "highway"),
              OsmDataQuery("buildings", OsmObject.WAY,
                           buildingsSelector, "building"),
              OsmDataQuery("landuse", OsmObject.WAY,
                           landuseSelector, "landuse"),
              OsmDataQuery("railway", OsmObject.WAY,
                           railwaySelector, "railway"),
              OsmDataQuery("amenity", OsmObject.WAYANDNODE,
                           amenitySelector, "amenity"),
              OsmDataQuery("leisure", OsmObject.WAYANDNODE,
                           leisureSelector, "leisure"),
              OsmDataQuery("shop", OsmObject.NODE, shopSelector, "shop"),
              OsmDataQuery("craft", OsmObject.NODE, craftSelector, "craft"),
              ]

osmDataFiles = OverPassHelper().fetch(pieschen.areaId(), areaName,
                                      osmQueries=osmQueries, overrideFiles=True)


pieschenCoord = pieschen.toJSON()[0]
map = folium.Map(
    location=[pieschenCoord["lat"], pieschenCoord["lon"]], tiles='Stamen Toner', zoom_start=15)

# matplotlib colormap names
colormaps = ["hsv", "BrBG", "coolwarm"]


for i, osmDataQuery in enumerate(osmDataFiles):
    file = open(osmDataQuery.filePath, encoding='UTF-8')
    allObjects = json.load(file)
    objectGroups = groupBy(allObjects, osmDataQuery.groupByProperty)

    objectMap = generateFeatureCollection(
        objectGroups, colormaps[i % len(colormaps)], osmDataQuery.name)
    objectMap.add_to(map)

folium.LayerControl().add_to(map)

fileName = "out/combinedMap_{}.html".format(areaName)
map.save(fileName)
print("Map saved in {}".format(fileName))
