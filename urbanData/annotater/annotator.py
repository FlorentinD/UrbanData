from abc import abstractmethod
from geojson import FeatureCollection

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

    def annotateAll(self, objects):
        """annotates a geojson-featureCollection"""
        annotatedFeatures = [self.annotate(object) for object in objects["features"]]
        return FeatureCollection(annotatedFeatures)

    @abstractmethod
    def annotate(self, object):
       raise NotImplementedError
