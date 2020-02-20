from enum import Enum

class OsmObjectType(Enum):
    """different object types retrieve-able via overpass"""
    WAY = "way"
    NODE = "node"
    WAYANDNODE = [WAY, NODE]
    RELATIONSHIP = "rel"
    WAYANDRELATIONSHIP = [WAY, RELATIONSHIP]
    ALL = [WAY, NODE, RELATIONSHIP]
