import json
import folium
import matplotlib
from jsonToGeoJSON import groupBy, getSchema
from OsmDataQuery import OsmDataQuery
from OsmObjectType import OsmObjectType
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


def collapseSubLayers(groupColorMap, groupsCount):
    """ generaters HTML to show in layer control """
    itemString = "<span style='color:{}'> <br> &nbsp; {} ({}) </span>"
    layerDescription = [itemString.format(
        color, name, groupsCount[name]) for name, color in groupColorMap.items()]
    return '\n'.join(layerDescription)


def generateFeatureCollection(groups, colormapName: str, featureName: str):
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
    
    featureCollection = folium.FeatureGroup(name = name)

    for type, group in groups.items():
        # Self mapped as geojson layer not fully functional yet (open PRs)
        for feature in group["features"]:
            geom = feature["geometry"]
            describtion = "<br>".join(["<b>{}</b>: {}".format(k, v) for k, v in feature["properties"].items()])
            color = groupColorMap[type]
            if geom["type"] == "Point":
                loc = geom["coordinates"]
                # ! switch lat and lon in coordinate
                folium.vector_layers.CircleMarker(
                    location=(loc[1], loc[0]), 
                    radius=3, 
                    tooltip=describtion, 
                    color=color).add_to(featureCollection)
            elif geom["type"] == "LineString":
                # ! switch lat and lon in coordinate
                loc = [(point[1], point[0])
                            for point in geom["coordinates"]]
                folium.vector_layers.PolyLine(
                    loc, 
                    color=color, 
                    tooltip=describtion).add_to(featureCollection)
            elif geom["type"] in ['MultiLineString', "Polygon"]:
                loc = []
                for lines in geom["coordinates"]:
                    for lon, lat in lines:
                        # !! switch lat and lon for correct representation
                        loc.append((lat, lon))
                folium.vector_layers.Polygon(loc, color=color, fill_color=color).add_to(featureCollection)
            elif geom["type"] == "MultiPolygon":
                loc = []
                for polygon in geom["coordinates"]:
                    for lines in polygon:
                        [loc.append((lat, lon)) for point in lines]
                        # !! switch lat and lon for correct representation
                folium.vector_layers.Polygon(loc, color=color, fill_color=color).add_to(featureCollection)
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
