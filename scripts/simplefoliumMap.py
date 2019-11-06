import json
import folium
from jsonToGeoJSON import groupBy
from OSMPythonTools.nominatim import Nominatim
from folium.plugins.measure_control import MeasureControl

# TODO: highway --> color
def style_function(feature):
    streetType = int(bytes(feature['properties']["highway"]))
    return {
        'fillOpacity': 0.5,
        'weight': 0,
        'fillColor': '#black'
    }


pieschen = Nominatim().query('Dresden Pieschen, Germany').toJSON()[0]

file = open("out/streets_dresden.json", encoding='UTF-8')
all_streets = json.load(file)
street_types = groupBy(all_streets, ["highway"])

streetMap = folium.Map(
    location=[pieschen["lat"], pieschen["lon"]], tiles='Stamen Toner', zoom_start=15)


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
streetMap.save("out/streetmap.html")
