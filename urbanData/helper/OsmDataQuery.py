from dataclasses import dataclass
from helper.OsmObjectType import OsmObjectType
from typing import List

@dataclass
class OsmDataQuery():
    name: str
    osmObject: OsmObjectType
    osmSelector: List
    groupByProperty: str = ""
    # TODO: refactor into OsmQueryResult ?
    filePath: str = None
    #colormap: str = "coolwarm"
