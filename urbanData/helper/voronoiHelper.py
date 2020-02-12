import numpy as np
import geojson
import matplotlib.pyplot as plt
import logging
from shapely.geometry import MultiPoint, Point, Polygon, mapping, shape
from shapely.ops import polygonize
from shapely.strtree import STRtree
from scipy.spatial import Voronoi

def voronoi_finite_polygons_2d(vor, radius=None):
    """
    Reconstruct infinite voronoi regions in a 2D diagram to finite
    regions.

    Parameters
    ----------
    vor : Voronoi
        Input diagram
    radius : float, optional
        Distance to 'points at infinity'.

    Returns
    -------
    regions : list of tuples
        Indices of vertices in each revised Voronoi regions.
    vertices : list of tuples
        Coordinates for revised Voronoi vertices. Same as coordinates
        of input vertices, with 'points at infinity' appended to the
        end.

    Source: https://gist.github.com/pv/8036995
    """

    if vor.points.shape[1] != 2:
        raise ValueError("Requires 2D input")

    new_regions = []
    new_vertices = vor.vertices.tolist()

    center = vor.points.mean(axis=0)
    if radius is None:
        radius = vor.points.ptp().max()

    # Construct a map containing all ridges for a given point
    all_ridges = {}
    for (p1, p2), (v1, v2) in zip(vor.ridge_points, vor.ridge_vertices):
        all_ridges.setdefault(p1, []).append((p2, v1, v2))
        all_ridges.setdefault(p2, []).append((p1, v1, v2))

    # Reconstruct infinite regions
    for p1, region in enumerate(vor.point_region):
        vertices = vor.regions[region]

        if all(v >= 0 for v in vertices):
            # finite region
            new_regions.append(vertices)
            continue

        # reconstruct a non-finite region
        ridges = all_ridges[p1]
        new_region = [v for v in vertices if v >= 0]

        for p2, v1, v2 in ridges:
            if v2 < 0:
                v1, v2 = v2, v1
            if v1 >= 0:
                # finite ridge: already in the region
                continue

            # Compute the missing endpoint of an infinite ridge

            t = vor.points[p2] - vor.points[p1] # tangent
            t /= np.linalg.norm(t)
            n = np.array([-t[1], t[0]])  # normal

            midpoint = vor.points[[p1, p2]].mean(axis=0)
            direction = np.sign(np.dot(midpoint - center, n)) * n
            far_point = vor.vertices[v2] + direction * radius

            new_region.append(len(new_vertices))
            new_vertices.append(far_point.tolist())

        # sort region counterclockwise
        vs = np.asarray([new_vertices[v] for v in new_region])
        c = vs.mean(axis=0)
        angles = np.arctan2(vs[:,1] - c[1], vs[:,0] - c[0])
        new_region = np.array(new_region)[np.argsort(angles)]

        # finish
        new_regions.append(new_region.tolist())

    return new_regions, np.asarray(new_vertices)

def voronoiFeatureCollection(points, mask = None):
    """
        creates a Voronoi diagram as a geojson feature collection
        points: geojson-featureCollection (features must be points else the center of the geometry is used) 
        mask: border for voroinoi areas (defaults to convex hull of points)
        returns a geojsonFeatureCollection
    """
    features = points["features"]
    propertyMap = {}
    points = []
    for feature in features:
        properties = feature["properties"]
        geometry = feature["geometry"]
        if geometry["type"] == "Point":
            point = geometry["coordinates"]
            points.append(point)
        else:
            # centerPoint
            point = shape(geometry).centroid.coords[0]
            points.append(point)
        propertyMap[tuple(point)] = properties

    vor = Voronoi(points)
    regions, vertices = voronoi_finite_polygons_2d(vor)
    pts = MultiPoint([Point(i) for i in points])
    pointIndex = STRtree([p for p in pts])

    if not mask:
        mask = pts.convex_hull
    else:
        mask = shape(mask["geometry"])
        if not isinstance(mask, Polygon):
            maskPolygons = list(polygonize(mask))
            if len(maskPolygons) == 1:
                mask = maskPolygons[0]
            else:
                # Fallback if not one polygon could be generated
                # otherwise a GeometryCollection would result ... probably
                mask = mask.convex_hull
    for region in regions:
        polygon = vertices[region]
        shapes = list(polygon.shape)
        shapes[0] += 1
        p = Polygon(np.append(polygon, polygon[0]).reshape(*shapes)).intersection(mask)

        # TODO: get polygon to featurePoint mapping from voronoi diagram
        pointsInPolygon = [point for point in pointIndex.query(p) if p.contains(point)]
        # TODO: log if multiple points in polygon (should never happen)
        if pointsInPolygon:
            properties = propertyMap[tuple(pointsInPolygon[0].coords[0])]
        else:
            properties = None

        if p.geom_type == "MultiPolygon":
            polygons = list(p)
            for poly in polygons:
                geoJsonGeom = mapping(poly)
                features.append(geojson.Feature(geometry=geoJsonGeom, properties=properties))
        else: 
            geoJsonGeom = mapping(p)
            if not geoJsonGeom["type"] == 'Polygon':
                raise ValueError("Voronoi area should be a polygon but got {}".format(geoJsonGeom["type"]))
        features.append(geojson.Feature(geometry=geoJsonGeom, properties=properties))
    return geojson.FeatureCollection(features)