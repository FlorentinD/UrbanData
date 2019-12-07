import json
from OSMPythonTools.nominatim import Nominatim
import folium
from folium.plugins.measure_control import MeasureControl

import sys
sys.path.insert(0, './helper')
from geoJsonHelper import groupBy
from overPassHelper import OverPassHelper
from OsmDataQuery import OsmDataQuery
from OsmObjectType import OsmObjectType

pieschen = Nominatim().query('Pieschen, Dresden, Germany')

osmQuery =  OsmDataQuery("streets", OsmObjectType.WAY, ["'highway'"], "highway")
all_streets = next(OverPassHelper().directFetch(pieschen.areaId(), [osmQuery]))
street_types = groupBy(all_streets, ["highway"])

piescheonCoord = [pieschen.toJSON()[0]["lat"], pieschen.toJSON()[0]["lon"]]
streetMap = folium.Map(
    location=piescheonCoord, tiles='Stamen Toner', zoom_start=15)


for type, streets in street_types.items():
    properties = list(streets["features"][0]["properties"].keys())
    folium.GeoJson(
        streets,
        name=type,
        tooltip=folium.features.GeoJsonTooltip(
            fields=properties),
        show=True,
    ).add_to(streetMap)
    
folium.LayerControl().add_to(streetMap)
streetMap.save("out/maps/streetmap.html")
