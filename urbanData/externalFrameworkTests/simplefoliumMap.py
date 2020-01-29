import json
from OSMPythonTools.nominatim import Nominatim
import folium
from folium.plugins.measure_control import MeasureControl

import sys, os
sys.path.insert(1, os.path.abspath('..'))
from helper.geoJsonHelper import groupBy
from helper.overPassHelper import OverPassHelper
from helper.OsmDataQuery import OsmDataQuery
from helper.OsmObjectType import OsmObjectType

pieschen = Nominatim().query('Pieschen, Dresden, Germany')

osmQuery =  OsmDataQuery("streets", OsmObjectType.WAY, ["'highway'"], "highway")
all_streets = next(OverPassHelper().directFetch(pieschen.areaId(), [osmQuery]))
street_types = groupBy(all_streets, ["highway"])

piescheonCoord = [pieschen.toJSON()[0]["lat"], pieschen.toJSON()[0]["lon"]]
streetMap = folium.Map(
    location=piescheonCoord, tiles='Stamen Toner', zoom_start=15)


icon = folium.Icon(icon="pills", color='lightgray', icon_color = 'red')

folium.Marker(
                        location=piescheonCoord,
                        tooltip="test",
                        icon=icon
                    ).add_to(streetMap)

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
streetMap.save("../out/maps/streetmap.html")
