from OSMPythonTools.nominatim import Nominatim
from OSMPythonTools.overpass import overpassQueryBuilder, Overpass
from geoJsonHelper import  osmObjectsToGeoJSON
import matplotlib.pyplot as plt
import geopandas
import pandas as pd
import seaborn as sb

areaName = "pieschen"
# area to query
pieschen = Nominatim().query('Pieschen, Dresden, Germany')

query = overpassQueryBuilder(
            area=pieschen.areaId(), elementType="way", selector=["'building'"], out='geom')
buildings = osmObjectsToGeoJSON(Overpass().query(query).toJSON()["elements"])

buildingsGdf = geopandas.GeoDataFrame.from_features(buildings["features"])
#buildingsGdf.plot("building", legend = True)


buildingsGdf["area"] = buildingsGdf.geometry.area

dataFrame = pd.DataFrame(buildingsGdf)
#dataFrame.hist(column="area", by="building")
avgAreaPerBuildingType = dataFrame.groupby(["building"]).agg(avg_area=("area","mean"), count=("area","count")).reset_index()
avgAreaPerBuildingType = avgAreaPerBuildingType.sort_values("count")
avgAreaPerBuildingType.plot.bar(x="building", y="count")
avgAreaPerBuildingType.plot.bar(x="building", y="avg_area", title="Ascending Sorted by group size")
plt.show()


