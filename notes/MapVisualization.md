# Map Visualization

* Requirement:
  * alter shown layers
  * zoom in/out

## Static Map

* geopandas
  * uses matplotlib
  * easy to use
  * how to add object info?
* [Mapnik](https://mapnik.org/)
* [streamlit](https://streamlit.io/docs/api.html) seems to have high

## Slippy Map

* [folium](https://github.com/python-visualization/folium)
  * supports Png, GeoJSON, TopoJSON files as layers
  * or could add a colorline based on a list of points latitude and longitude
  * possible to add markers
  * ! slippy maps seem to have performance problems with f.i. 50 MB data, thus static maps would be a way to go there
* * [streamlit](https://streamlit.io/docs/api.html) (deck_gl) says to be more performant, but seems to be only a javascript api