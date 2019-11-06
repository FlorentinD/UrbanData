import json
import folium
import matplotlib
from jsonToGeoJSON import groupBy, getSchema
from OSMPythonTools.nominatim import Nominatim
from folium.plugins.measure_control import MeasureControl


def cmMapColorToHex(color):
    rgb = color[:3]
    return matplotlib.colors.rgb2hex(rgb)


def styleFunction(colorMap, property: str):
    """style function for folium.geojson based on map (propertyValue -> color)"""
    return lambda feature: {
        "color": colorMap[feature['properties'][property]]
    }

def collapseSubLayers(groupColorMap):
    """ generaters HTML to show in layer control """
    itemString = "<span style='color:{}'> <br> &nbsp; {} </span>"
    layerDescription = [itemString.format(color, name) for name, color in groupColorMap.items()]
    return '\n'.join(layerDescription)

def generateFeatureCollection(groups, name: str, colormapName, propertyForColor: str):
    """groups: dictoniary with geojson.FeatureCollections as values"""

    colormap = matplotlib.cm.get_cmap(name=colormapName, lut=len(groups))
    # similar often groups, should get different colours
    #groupSizes = [(key, len(gr["features"])) for key, gr in groups.items()]
    #groupSizes.sort(key=lambda tup: tup[1])
    groupColorMap = {key: cmMapColorToHex(colormap(i)) for i, (key, _)  in enumerate(groups.items())}

    # TODO: get top10 properties to work
    featureCollection = folium.FeatureGroup(name=name + collapseSubLayers(groupColorMap))
    for type, group in groups.items():
        properties = list(group["features"][0]["properties"].keys())
        #properties = getSchema(group)
        layer = folium.GeoJson(
            group,
            name=type,
            style_function=styleFunction(groupColorMap, propertyForColor),
            tooltip=folium.features.GeoJsonTooltip(
                fields=properties),
            show=True
        )
        layer.add_to(featureCollection)

    return featureCollection
