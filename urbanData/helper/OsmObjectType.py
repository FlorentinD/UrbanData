from enum import Enum

class OsmObjectType(Enum):
    WAY = "way"
    NODE = "node"
    WAYANDNODE = ["way", "node"]
    RELATIONSHIP = "relationship"