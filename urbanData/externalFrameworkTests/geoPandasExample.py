import geopandas
import matplotlib.pyplot as plt
from OSMPythonTools.nominatim import Nominatim

import sys, os
sys.path.insert(0, os.path.abspath('..'))
from helper.overPassHelper import OverPassHelper

plt.rcParams["figure.figsize"] = (25,25)

pieschen = Nominatim().query('Pieschen, Dresden, Germany')
OverPassHelper().fetch(pieschen.areaId(), "pieschen")


highWayFrame = geopandas.read_file("out/data/streets_pieschen.json", driver='GeoJson')
print(highWayFrame.size)
print(highWayFrame.keys())

plot = highWayFrame.plot(column='highway', legend=True)
plt.show()


buildingsFrame = geopandas.read_file("out/data/geoPandas_Example.json")
print(buildingsFrame.size)
print(buildingsFrame.keys())
plot2 = buildingsFrame.plot(column='building', legend=True)
plt.show()

