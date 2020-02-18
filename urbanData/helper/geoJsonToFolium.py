import json
import folium
from folium.plugins.measure_control import MeasureControl
from folium.plugins import FeatureGroupSubGroup
import re
from matplotlib import colors as pltClrs, cm as pltCm
import logging
from enum import Enum

from helper.geoJsonHelper import groupBy, getSchema
from helper.OsmDataQuery import OsmDataQuery
from helper.OsmObjectType import OsmObjectType


def cmMapColorToHex(color):
    rgb = color[:3]
    return pltClrs.rgb2hex(rgb)


def styleFunction(colorMap, property: str):
    """style function for folium.geojson based on map (propertyValue -> color)"""
    return lambda feature: {
        "color": colorMap[feature['properties'][property]]
    }


def collapseSubLayers(groupColorMap, groupsCount):
    """ generaters HTML to show in layer control """
    layerDescription = ["<br> &nbsp;&nbsp;&nbsp;&nbsp;" + enhanceFeatureName(name, color, groupsCount[str(name)]) for name, color in groupColorMap.items()]
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
    if isinstance(value, Enum):
        return value.value
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

def geoFeatureCollectionToFoliumFeatureGroup(geoFeatureCollection, color, name, switchLatAndLong = True, show = True):
    """
    converts a geojson feature collection to a folium feature group    
    """

    name = enhanceFeatureName(name, color, len(geoFeatureCollection["features"]))
    featureCollection = folium.FeatureGroup(name = name, show = show)

    # TODO: try MarkerCluster if atleast one point
    # TODO factor switchLatAndLong into geoJsonHelper (geom transformer)
    # Self mapped as geojson layer not fully functional yet (open PRs)
    for feature in geoFeatureCollection["features"]:
            geom = feature["geometry"]
            describtion = "<br>".join(["<b>{}</b>: {}".format(k, escapePropertyValue(v)) for k, v in feature["properties"].items(
            ) if (not k.startswith("__") or logging.getLogger().level == logging.DEBUG) and v])
            if not describtion:
                # set to None if empty string (default for folium tooltip parameter)
                describtion = None
            if geom["type"] == "Point":
                loc = geom["coordinates"]
                if switchLatAndLong:
                    point = (loc[1], loc[0])
                else:
                    point = (loc[0], loc[1])
                folium.vector_layers.CircleMarker(
                    location=point,
                    radius=3,
                    tooltip=describtion,
                    color=color).add_to(featureCollection)
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
                exteriorLines = []
                for polygon in geom["coordinates"]:
                    if len(polygon) > 1:
                            logging.debug("Folium does not support holes in Polygon -> just exterior line")
                    exteriorLine = polygon[0]
                    points = []
                    for lon, lat in exteriorLine:
                        if switchLatAndLong:
                            points.append((lat, lon))
                        else:
                            points.append((lon, lat))
                    exteriorLines.append(points)
                # a leaflet polygon supports multiPolygons via multiple polygon shapes inside locations
                folium.vector_layers.Polygon(
                    locations= exteriorLines, 
                    tooltip=describtion, 
                    color=color, 
                    fill_color=color).add_to(featureCollection)
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

def generateFeatureCollectionForGroups(groups, colors, featureName: str, show = True):
    """groups: dictionary with geojson.FeatureCollections as values
        
        colors: 
            str (name for matplotlib colormap https://matplotlib.org/3.1.0/gallery/color/colormap_reference.html) 
            or list of colors (if less colors than groups -> based on custom linearsegmented colormap)
            or dictionary (groupName: color)
    """

    if isinstance(colors, str):
        matPlotColorMap = pltCm.get_cmap(name=colors, lut=len(groups))
        colors = [cmMapColorToHex(matPlotColorMap(i)) for i in range(0, len(groups))]
    if isinstance(colors, list):
        if len(colors) == len(groups):
            colorMap = dict(zip(groups.keys(), colors))
        else:
            # creating custom colormap
            matPlotColorMap = pltClrs.LinearSegmentedColormap.from_list("", colors, N=len(groups))
            colors = [cmMapColorToHex(matPlotColorMap(i)) for i in range(0, len(groups))]
            colorMap = dict(zip(sorted(groups.keys()), colors))
    if isinstance(colors, dict):
        colorMap = colors


    name = featureName

    # TODO: move into collapseSubLayers
    if len(groups.items()) > 1:
        groupsCount = {name: len(group["features"])
                             for name, group in groups.items()}
        name += collapseSubLayers(colorMap, groupsCount)
    else:
        name += "({})".format((len(list(groups.values())[0]["features"])))

    layer = folium.FeatureGroup(name = name, show=show)
    for type, group in groups.items():
        if not type in colorMap:
            raise ValueError("{} not defined in the colormap: {}".format(type, colorMap)) 
        color = colorMap[type]
        featureGroup = geoFeatureCollectionToFoliumFeatureGroup(group, color, type, show = show)
        featureGroup.add_to(layer)
    return layer
