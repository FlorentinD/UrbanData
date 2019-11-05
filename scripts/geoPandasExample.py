import geopandas
import matplotlib.pyplot as plt
from OSMPythonTools.nominatim import Nominatim
from overpassHelper import fetchBuildingsAndStreets

plt.rcParams["figure.figsize"] = (25,25)

pieschen = Nominatim().query('Pieschen, Dresden, Germany')
fetchBuildingsAndStreets(pieschen.areaId(), "pieschen")


highWayFrame = geopandas.read_file("out/streets_pieschen.json", driver='GeoJson')
print(highWayFrame.size)
print(highWayFrame.keys())

plot = highWayFrame.plot(column='highway', legend=True)
plt.show()


buildingsFrame = geopandas.read_file("out/buildings_pieschen.json")
print(buildingsFrame.size)
print(buildingsFrame.keys())
plot2 = buildingsFrame.plot(column='building', legend=True)
plt.show()

