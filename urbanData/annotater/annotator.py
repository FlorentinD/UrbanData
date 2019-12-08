from abc import abstractmethod

class Annotator():
    """Base Class for annotaters of geojson-objects
    Attributes:
        writeProperty   property which will be added to the objects by annotate()
        dataSource      data source used for annotation (f.i. company data)
    """
    """Property added to the geojson object"""
    writeProperty = None
    dataSource = None

    def __init__(self, dataSource, writeProperty):
        self.dataSource = dataSource
        self.writeProperty = writeProperty

    @abstractmethod
    def annotate(self, objects, matchCondition):
        # TODO: is a matchCondition reasonable?
        pass
