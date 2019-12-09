import sys, os

from annotater.annotator import Annotator

class AddressAnnotator(Annotator):
    """Annotates an object with addresses of contained objects
        f.i. buildings gets addresses of all entrances"""

    writeProperty = "addresses"
    dataSource = None

    def __init__(self, addressObjects):
        self.dataSource = addressObjects
    
    def annotate(self, dataSource):
        # TODO: copy method
        return NotImplementedError


if not __name__ == "__main__":
    print("here")
    