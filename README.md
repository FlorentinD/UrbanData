# Urban Data Seminar

# Getting started

* Install dependencies
* Look at the notebooks or scripts (f.i. `scripts/foliumPieschenMap`)

## Todo

- [ ] Find working python framework for newer WMS versions (not really a high priotity if WFS service works) (may be supported directly by folium)
- [x] How to convert json from overpassQL to geojson (works for current queries)
- [ ] How to translate gml into geojson? (not convertable with ogr?)
- [x] GeoPandas? (takes very long to load file, probably because multipoint lines get transformed to normal lines)
- [ ] ?create layer images (better performance, but not interactive (what informations to display?))
  
## Package dependency

- OWSLib (for request on WMS and WFS for openDataDresden)
- OSMPythonTools (for access to openstreetmap services)
- Folium (map visualization)
- geojson (format for importing data into folium map)
- geopandas