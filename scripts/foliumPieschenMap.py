import json
import folium
from matplotlib import cm
from jsonToGeoJSON import groupBy
from foliumHelper import generateFeatureCollection, styleFunction, cmMapColorToHex
from OSMPythonTools.nominatim import Nominatim
from folium.plugins.measure_control import MeasureControl
from overpassHelper import fetchBuildingsAndStreets

pieschen = Nominatim().query('Pieschen, Dresden, Germany')
pieschenCoord = pieschen.toJSON()[0]
fetchBuildingsAndStreets(pieschen.areaId(), "pieschen")

map = folium.Map(
    location=[pieschenCoord["lat"], pieschenCoord["lon"]], tiles='Stamen Toner', zoom_start=15)


file = open("out/streets_pieschen.json", encoding='UTF-8')
all_streets = json.load(file)
streetGroups = groupBy(all_streets, ["highway"])

streetsMap = generateFeatureCollection(
    streetGroups, "Streets", "BrBG", "highway")

streetsMap.add_to(map)

# colormap = cm.get_cmap(name="BrBG", lut=len(streetGroups))
# streetColors = {key: colormap(i) for i, key in enumerate(streetGroups.keys())}

""" for type, streets in streetGroups.items():
    properties = list(streets["features"][0]["properties"].keys())
    layer = folium.GeoJson(
        streets,
        name=type,
        style_function=lambda feature: {
            "color": cmMapColorToHex(streetColors[feature['properties']['highway']])
        },
        tooltip=folium.features.GeoJsonTooltip(
            fields=properties),
        show=True,
    )
    layer.add_to(map) """


file = open("out/buildings_pieschen.json", encoding='UTF-8')
all_buildings = json.load(file)
buildingGroups = groupBy(all_buildings, ["building"])

buildingsMap = generateFeatureCollection(
    buildingGroups, "Buildings", "coolwarm", "building")

buildingsMap.add_to(map)
folium.LayerControl().add_to(map)

map.save("out/map_pieschen.html")
