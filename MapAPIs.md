# Map APIs

* How to access different layers?
  * via layers methods/options
  * or load
* How to access places in a given area?
  * often stored as nodes
  
## Google Maps

* needs a billing account (for the case that the requests exceed the free credit of 200$/month)
* therefore not further investigated

## OpenstreetView

* [osmapi](http://osmapi.metaodi.ch/)
  * low-lvl api (no support for search by location name f.i.)
  * layers possible via using [tag information](<https://wiki.openstreetmap.org/wiki/Category:Features>)
    * free tagging system --> cummunity aggrees on certain combinations
    * [tag info project](<https://taginfo.openstreetmap.org/keys>)
    * TODO: search for important tags / But may be too tedious (probably use other API)
  * limit of 50.000 nodes per request (Dresden has more --> only show specific areas?)
  * or use [export function](https://www.openstreetmap.org/export#map=10/50.9891/14.1051&layers=H)
  * alternative use planet.osm (compressed size: 80 GB)

* [Overpass API](<https://wiki.openstreetmap.org/wiki/Overpass_API>)
  * more advanced API [extra query language (OverpassQL](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL))
  * TODO: try to isolate different layers using this API

* Nomainatim API
  * for reverse geocoding (string -> geoObject)

* [OSMPythonTools](<https://github.com/mocnik-science/osm-python-tools>) for accessing OverpassAPI, NominatimAPI as well as OsmAPI
  * problems to install under windows (work around: use Anaconda or not Windows)

## Other resources

### OpenData Dresden

* [openData Dresden](https://opendata.dresden.de/DreiD/)
* need to manually select important data and corresponding server
* [Web Map Service](https://en.wikipedia.org/wiki/Web_Map_Service):
  * will serve map images  
  * _probably_ not useable if data should be included as a layer in an existing map (!some visualization frameworks allow an _addLayer_ method based on WMS !)
* [Web Feature Service](https://en.wikipedia.org/wiki/Web_Feature_Service):
  * allows requesting geographical features (_source code_ of the map)
  &rarr; enables spatial analysis & feature extraction
* Fetching data from WMS and WFS Servers:
  * Option 1: request via URL (tedious)
  * Option 2: use [OWSLib](http://geopython.github.io/OWSLib/)
