import json
import folium
from folium.plugins.measure_control import MeasureControl
from folium.plugins import FeatureGroupSubGroup
import re
import matplotlib
import logging

from helper.geoJsonHelper import groupBy, getSchema
from helper.OsmDataQuery import OsmDataQuery
from helper.OsmObjectType import OsmObjectType


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
    layerDescription = ["<br> &nbsp;&nbsp;&nbsp;&nbsp;" + enhanceFeatureName(name, color, groupsCount[name]) for name, color in groupColorMap.items()]
    return ''.join(layerDescription)


def enhanceFeatureName(name, color, count) -> str:
    """adding count and value to the name as HTML span element"""
    itemString = "<span style='color:{}'> {} ({}) </span>"
    return itemString.format(color, name, count)

def escapePropertyValue(value):
    """escape and insert line breaks for a friendly description output"""
    if isinstance(value, str):
        # ` was not allowed in Leatleaf JS 
        return value.replace("`", "\`")
    if isinstance(value, list):
        itemsPerLine = 6
        numberOfLineBreaks = round(len(value) / itemsPerLine)
        if numberOfLineBreaks:
            for i in range(1, numberOfLineBreaks):
                value.insert(i * itemsPerLine, "<br>")
        return [escapePropertyValue(v) for v in value]
    if isinstance(value, dict):
        return "".join(["<br> &nbsp;&nbsp; {}: {}".format(k, escapePropertyValue(v)) for k, v in value.items() if v])
    else:
        return value

def geoFeatureCollectionToFoliumFeatureGroup(geoFeatureCollection, color, name, switchLatAndLong = True, icon = None, show = True):
    """from geojson feature collection to folium feature group

        icon: name of the marker sign based on https://fontawesome.com/icons (only for points?)
    """

    name = enhanceFeatureName(name, color, len(geoFeatureCollection["features"]))
    featureCollection = folium.FeatureGroup(name = name, show = show)

    # TODO: try MarkerCluster if atleast one point
    # Self mapped as geojson layer not fully functional yet (open PRs)
    for feature in geoFeatureCollection["features"]:
            geom = feature["geometry"]
            describtion = "<br>".join(["<b>{}</b>: {}".format(k, escapePropertyValue(v)) for k, v in feature["properties"].items() if not k.startswith("__") and v])
            if not describtion:
                # set to None if empty string (default for folium tooltip parameter)
                describtion = None
            if geom["type"] == "Point":
                loc = geom["coordinates"]
                if switchLatAndLong:
                    point = (loc[1], loc[0])
                else:
                    point = (loc[0], loc[1])
                if icon:
                    folium.Marker(
                        location=point,
                        tooltip=describtion,
                        icon=icon
                    ).add_to(featureCollection)
                else:
                    folium.vector_layers.CircleMarker(
                        location=point,
                        radius=3,
                        tooltip=describtion,
                        color=color,
                        icon=icon).add_to(featureCollection)
            elif geom["type"] == "LineString":
                if switchLatAndLong:
                    loc = [(point[1], point[0])
                            for point in geom["coordinates"]]
                else:
                    loc = geom["coordinates"]
                folium.vector_layers.PolyLine(
                    loc, 
                    color=color, 
                    tooltip=describtion).add_to(featureCollection)
            elif geom["type"] == 'MultiLineString':
                loc = []
                for line in geom["coordinates"]:
                    for lon, lat in line:
                        if switchLatAndLong:
                            loc.append((lat, lon))
                        else:
                            loc.append((lon, lat))
                folium.vector_layers.Polygon(
                    loc, 
                    tooltip=describtion, 
                    color=color, 
                    fill_color=color).add_to(featureCollection)
            elif geom["type"] == 'Polygon':
                lines = geom["coordinates"]
                if len(lines) > 1:
                    logging.debug("Folium does not support holes in Polygon -> just exterior line")

                loc = []
                for lon, lat in lines[0]:
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
                raise ValueError("Folium does not support MultiPolygons")
                """ loc = []
                # TODO: rewrite MultiPolygon into multiple Polygon objects?
                for polygon in geom["coordinates"]:
                    for lines in polygon:
                        if switchLatAndLong:
                            [loc.append((lat, lon)) for point in lines]
                        else:
                          [loc.append((lon, lat)) for point in lines]  
                folium.vector_layers.Polygon(loc, tooltip=describtion, color=color, fill_color=color).add_to(featureCollection) """
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

def generateFeatureCollectionForGroups(groups, colormapName: str, featureName: str, iconMap = {}, show = True):
    """groups: dictoniary with geojson.FeatureCollections as values"""

    colormap = matplotlib.cm.get_cmap(name=colormapName, lut=len(groups))
    # similar often groups, should get different colours
    # groupSizes = [(key, len(gr["features"])) for key, gr in groups.items()]
    # groupSizes.sort(key=lambda tup: tup[1])
    groupColorMap = {key: cmMapColorToHex(
        colormap(i)) for i, (key, _) in enumerate(groups.items())}

    name = featureName

    # TODO: move into collapseSubLayers
    if len(groups.items()) > 1:
        groupsCount = {name: len(group["features"])
                             for name, group in groups.items()}
        name += collapseSubLayers(groupColorMap, groupsCount)
    else:
        name += "({})".format((len(list(groups.values())[0]["features"])))

    layer = folium.FeatureGroup(name = name)
    for type, group in groups.items():
        color = groupColorMap[type]
        featureGroup = geoFeatureCollectionToFoliumFeatureGroup(group, color, type, show = show, icon=iconMap.get(type, None))
        featureGroup.add_to(layer)
    return layer
