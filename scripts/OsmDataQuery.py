from dataclasses import dataclass
from OsmObjectType import OsmObjectType
from typing import List

@dataclass
class OsmDataQuery():
    name: str
    osmObject: OsmObjectType
    osmSelector: List
    groupByProperty: str 
    filePath: str = None
    #colormap: str = "coolwarm"
