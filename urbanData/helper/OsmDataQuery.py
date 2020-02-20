from dataclasses import dataclass
from helper.OsmObjectType import OsmObjectType
from typing import List

@dataclass
class OsmDataQuery():
    """
    helper class to store info for a overpass query
    """
    name: str
    osmObject: OsmObjectType
    osmSelector: List
    groupByProperty: str = ""
    # TODO: refactor into OsmQueryResult ?
    filePath: str = None
