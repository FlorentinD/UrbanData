import json
import folium
import matplotlib
from jsonToGeoJSON import groupBy
from OSMPythonTools.nominatim import Nominatim
from folium.plugins.measure_control import MeasureControl


def cmMapColorToHex(color):
    rgb = color[:3]
    return matplotlib.colors.rgb2hex(rgb)


def styleFunction(colormap, property: str):
    """style function for folium.geojson"""
    return lambda feature: {
        "color": cmMapColorToHex(colormap(hash(feature['properties'][property]) % colormap.N))
    }


def generateFeatureCollection(groups, name: str, colormap, propertyForColor: str):
    """gropus: dictoniary with geojson.FeatureCollections as values"""
    # colormap = matplotlib.col.get_cmap("GnBu", lut=len(groups)))
    featureCollection = folium.FeatureGroup(name=name)
    for type, group in groups.items():
        properties = list(group["features"][0]["properties"].keys())
        layer = folium.GeoJson(
            group,
            name=type,
            style_function=styleFunction(colormap, propertyForColor),
            tooltip=folium.features.GeoJsonTooltip(
                fields=properties),
            show=True,
        )
        layer.add_to(featureCollection)
    return featureCollection
