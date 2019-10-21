## Map APIs

* How to access different layers?
* How to access places in a given area?
  
### Google Maps

* needs a billing account (for the case that the requests exceed the free credit of 200$/month)
* therefore not further investigated

### OpenstreetView

* TODO

## Other resources

### OpenData Dresden

* [openData Dresden](https://opendata.dresden.de/DreiD/) looks promising
* [WMS API](https://en.wikipedia.org/wiki/Web_Map_Service):
  * will serve map images
  * _probably_ not useable if data should be included as a layer in an existing map (!investigate further!)
* [WFS API](https://en.wikipedia.org/wiki/Web_Feature_Service):
  * allows requesting geographical features (_source code_ of the map)
  &rarr; enables spatial analysis
* Fetching data from WMS and WFS Servers:
  * Option 1: request via URL (tedious)
  * Option 2: use [OWSLib](http://geopython.github.io/OWSLib/)

