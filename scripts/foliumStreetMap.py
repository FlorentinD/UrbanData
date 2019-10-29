import json
import folium
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

map = folium.Map(location=[pieschen["lat"], pieschen["lon"]],
                 tiles='Stamen Toner', zoom_start=15)

folium.raster_layers.TileLayer('OpenStreetMap').add_to(map)


file = open("out/highways.json", encoding='UTF-8')
highways = json.load(file)
propertyFields = list(highways["features"][0]["properties"].keys())
print("{} streets loaded".format(len(highways["features"])))

print(propertyFields)


streetMap = folium.Map(
    location=[pieschen["lat"], pieschen["lon"]], tiles='Stamen Toner', zoom_start=15)

# TODO: add style function
# TODO: set embed to False (currently data is stored inside the html file?)
folium.GeoJson(
    "out/highways.json",
    name='Streets',
    tooltip=folium.features.GeoJsonTooltip(
        fields=["highway", "name", "surface", "maxspeed", "lit"]),
    show=True,
).add_to(streetMap)
folium.LayerControl().add_to(streetMap)
streetMap.save("out/streetmap.html")
