import math
from pyproj import Proj
from shapely.ops import transform

# TODO: derive Zone from coordinates
utm_projection = Proj(proj='utm', zone=33, ellps='WGS84', preserve_units=False)


def transformWgsToUtm(shapelyObject):
    """transform coordinates of shapely object to UTM from WGS 84"""
    return transform(utm_projection, shapelyObject)


def transformUtmToWgs(shapelyObject):
    """transform coordinates of shapely object from UTM to WGS 84"""
    return transform(lambda x, y, z=None: utm_projection(x, y, inverse=True), shapelyObject)


def wgsToUtm(x, y):
    """transforms x and y coordinate to UTM"""
    return utm_projection(x, y)


def utmToWgs(x, y):
    return utm_projection(x, y, inverse=True)

def distance(p0, p1):
    return math.sqrt((p0[0] - p1[0])**2 + (p0[1] - p1[1])**2)