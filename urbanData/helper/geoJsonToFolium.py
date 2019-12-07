import json
import folium
from folium.plugins.measure_control import MeasureControl
import re
import matplotlib

from geoJsonHelper import groupBy, getSchema
from OsmDataQuery import OsmDataQuery
from OsmObjectType import OsmObjectType


def cmMapColorToHex(color):
    rgb = color[:3]
    return matplotlib.colors.rgb2hex(rgb)


def styleFunction(colorMap, property: str):
    """style function for folium.geojson based on map (propertyValue -> color)"""
    return lambda feature: {
        "color": colorMap[feature['properties'][property]]
    }


def collapseSubLayers(groupColorMap, groupsCount):
    """ generaters HTML to show in layer control """
    layerDescription = [enhanceFeatureName(name, color, groupsCount[name]) for name, color in groupColorMap.items()]
    return '\n'.join(layerDescription)


def enhanceFeatureName(name, color, count) -> str:
    """adding count and value to the name as HTML span element"""
    itemString = "<span style='color:{}'> {} ({}) </span>"
    return itemString.format(color, name, count)

def escapePropertyValue(value):
    if isinstance(value, str):
        return value.replace("`", "\`")
    if isinstance(value, list):
        return [escapePropertyValue(v) for v in value]
    if isinstance(value, dict):
        return "<br>".join(["&nbsp;&nbsp; {}: {}".format(k,v) for k, v in value.items()])
    else:
        return value

def geoFeatureCollectionToFoliumFeatureGroup(geoFeatureCollection, color, name, switchLatAndLong = True):
    """from geojson feature collection to folium feature group"""
    name = enhanceFeatureName(name, color, len(geoFeatureCollection["features"]))
    featureCollection = folium.FeatureGroup(name = name)
    
    # Self mapped as geojson layer not fully functional yet (open PRs)
    for feature in geoFeatureCollection["features"]:
            geom = feature["geometry"]
            # ` was not allowed in Leatleaf JS 
            describtion = "<br>".join(["<b>{}</b>: {}".format(k, escapePropertyValue(v)) for k, v in feature["properties"].items() if not k.startswith("__") and v])
            if geom["type"] == "Point":
                loc = geom["coordinates"]
                if switchLatAndLong:
                    point = (loc[1], loc[0])
                else:
                    point = (loc[0], loc[1])
                # ! switch lat and lon in coordinate
                folium.vector_layers.CircleMarker(
                    location=point, 
                    radius=3, 
                    tooltip=describtion, 
                    color=color).add_to(featureCollection)
            elif geom["type"] == "LineString":
                # ! switch lat and lon in coordinate
                if switchLatAndLong:
                    loc = [(point[1], point[0])
                            for point in geom["coordinates"]]
                else:
                    loc = geom["coordinates"]
                folium.vector_layers.PolyLine(
                    loc, 
                    color=color, 
                    tooltip=describtion).add_to(featureCollection)
            elif geom["type"] in ['MultiLineString', "Polygon"]:
                loc = []
                for lines in geom["coordinates"]:
                    for lon, lat in lines:
                        if switchLatAndLong:
                            loc.append((lat, lon))
                        else:
                            loc.append((lon, lat))
                folium.vector_layers.Polygon(
                    loc, 
                    tooltip=describtion, 
                    color=color, 
                    fill_color=color).add_to(featureCollection)
            elif geom["type"] == "MultiPolygon":
                loc = []
                for polygon in geom["coordinates"]:
                    for lines in polygon:
                        if switchLatAndLong:
                            [loc.append((lat, lon)) for point in lines]
                        else:
                          [loc.append((lon, lat)) for point in lines]  
                folium.vector_layers.Polygon(loc, tooltip=describtion, color=color, fill_color=color).add_to(featureCollection)
            else:
                raise ValueError("{} not mapped onto folium object yet".format(geom["type"]))
        #  layer = folium.GeoJson(
        #             group,
        #             name=type,
        #             style_function=styleFunction(groupColorMap, query.groupByProperty),
        #             tooltip=folium.features.GeoJsonTooltip(
        #                 fields=properties),
        #             show=True
        #         )
        #         layer.add_to(featureCollection)
    return featureCollection

def generateFeatureCollection(groups, colormapName: str, featureName: str):
    """groups: dictoniary with geojson.FeatureCollections as values"""

    colormap = matplotlib.cm.get_cmap(name=colormapName, lut=len(groups))
    # similar often groups, should get different colours
    # groupSizes = [(key, len(gr["features"])) for key, gr in groups.items()]
    # groupSizes.sort(key=lambda tup: tup[1])
    groupColorMap = {key: cmMapColorToHex(
        colormap(i)) for i, (key, _) in enumerate(groups.items())}

    name = featureName

    layer = folium.FeatureGroup(name = name)

    # TODO: move into collapseSubLayers
    if len(groups.items()) > 1:
        groupsCount = {name: len(group["features"])
                             for name, group in groups.items()}
        name += collapseSubLayers(groupColorMap, groupsCount)
    else:
        name += "({})".format((len(list(groups.values())[0]["features"])))
    
    for type, group in groups.items():
        color = groupColorMap[type]
        featureGroup = geoFeatureCollectionToFoliumFeatureGroup(group, color, type)
        featureGroup.add_to(layer)
    return layer
