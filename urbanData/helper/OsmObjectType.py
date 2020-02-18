from enum import Enum

class OsmObjectType(Enum):
    WAY = "way"
    NODE = "node"
    WAYANDNODE = [WAY, NODE]
    RELATIONSHIP = "rel"
    WAYANDRELATIONSHIP = [WAY, RELATIONSHIP]
    ALL = [WAY, NODE, RELATIONSHIP]
