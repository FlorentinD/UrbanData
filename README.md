# Urban Data Seminar

# Getting started

1. Execute the `scripts/overpassHelper.py` for generating the datasets
2. Explore the datasets using the jupyter notebook `notebooks/foliumNotebook`

## Todo

- [ ] Find working python framework for newer WMS versions (not really a high priotity if WFS service works) (may be supported directly by folium)
- [ ] How to convert json from overpassQL to geojson (in progress -- done for way-objects)
- [ ] How to translate gml into geojson?
- [ ] GeoPandas?
- [ ] create layer images (better performance, but not interactive)
  
## Package dependency

- OWSLib (for request on WMS and WFS for openDataDresden)
- OSMPythonTools (for access to openstreetmap services)
- Folium (map visualization)
- geojson (format for importing data into folium map)
