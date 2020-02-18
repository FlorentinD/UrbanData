# Urban Data Seminar

This project was created as part of the `Urban Data Seminar` at the TU Dresden.
It fetches data mostly from openstreetmap, but also from other sources as dvb for public transport, timetravel for time maps and yellow pages as well as the handelsregister for additional data regarding companies. 

The simplest script is the `urbanDataMap` which just fetches relevant openstreetmap data and visualizes it in a map. 
At the beginning the idea was group buildings and find building regions, which can be seen in `buildingComplexes` script.
Resulting are building-groups (buildings having at least one common point) and building-regions (building-groups not being further apart then 120 meters and having no street in between).
As the data from openstreetmap is not complete, f.i. many buildings are just tagges as _yes_, an additional building-type is introduced (see `annotater/buildingClassifier`).
There are several other properties annotated as seen in the `annotater` package.
Note that regions only contain the buildings and not the space inbetween (regarding area and shape).
Overlapping regions exist only visually as the convex hull of the shapes are used (could not find a good method to improve shape based on region borders).

![Image of a building map](images/buildingMap.png)

For more images of a building map see [here](images/)


At last there is the `cityPatterns` script, which uses the results from the `buildingComplexes` script and tries to find patterns as described by Christoph Alexander in `A Pattern-Language`.
Besides his patterns, which were also partly modified, also others can be found in the map. 
The patterns are visualized simply by highlithing the corresponding objects, but also Voronoi-Diagrams and TimeMaps exists, to show the coverage (f.i. public transport stops are have a 5-Minute-Walk area).
A more detailed describtion for each layer in the map can be found here: ... // TODO add link and describe each layer in more detail (like crossRoads).

TODO: add map images

## Getting started

The current scripts are for Dresden.
Executing the scripts for the first time can take quite a while as many data from openstreetmap needs to be pulled (responses will be cached, so subsequent execution will be faster).

If you change the city you should note the following:
* The tags the analysis is based on may have different meanings and/or values if you change the city 
* The scraped company data for Dresden is uploaded. For other cities they need to be scraped by yourself.
* If you want to include data for the public transport you need to find a corresponding API as dvb will probably not work. 
// TODO: add link
* If you want to build your own time maps (`timeMapRetriever` might be a good starting point), you will need your own API-KEY!
* You may notice the introduced pauses, which are introduced to respect the allowed request per minute limit for the free usage of TimeMaps.

 

## Package dependency 
TODO: add links to folium, timemap, 

### For scripts in main directory) 

Visualization:
- folium (fronted/map visualization)
- matplotlib (mostly for their color maps)
- scipy (for Voronio diagrams)
- numpy (also just for Voronoi diagrams)

Fetching data:
- OSMPythonTools (for access to openstreetmap services e.g. overpass and nomantin)
- scrapy (for scraping yellow pages and handelsregister for company data)
- dvb (for accessing data from the public transport provider for dresden)
- requests (sending requests to web services like timemap)
- OWSLib (for request on WMS and WFS for openDataDresden, currently only as an experiment)
  
Data Processing:
- geojson (data format assumed in most of the functions)
- shapely (operations on geometries and r-tree index)
- networkx (graph approach for grouping objects via connected components)
- pyproj (for projection between WGS84 and UTM coordinates)
- geopandas
- pandas  

Util:
- json 
- logging
- time 
- re
- abc (for abstract methods)
- dataclasses (something like scalas `case classes`)
- collections (like defaultdict)

## Further ideas 

* use data from openDataDresden (using their wms and wfs services)
* use multi-threading f.i. finding buildingRegions
* use streamlit for an interactive web app (allowing to interactivly add layers and so on)
* write way more tests
