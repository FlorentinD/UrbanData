# Pattern

* hard to find a raster --> use voronoi diagrams (use scipy)

## (16) public transport

* 1. get dvb stops (point with tag highway="bus_stop")
  * https://docs.traveltimeplatform.com/reference/time-map
* 2. use webservice for _5-minute walk areas_ around stops

## (21) at most 4 building-level

* based on already fetched buildings
* rooftop level does not count extra here

## (22) 9% parking lots

* only partyl tagged
* based on ground areas
* amenity = "parking"

## (23) parallel streets

* at what point are 2 streets parallel?
* rewritten into: crossroads with 3-4 edges (excluding bigger crossroads) , these are not specially tagged
* roundabouts tagged in openstreetmap with _highway=mini_roundabout_

## (30) activity nodes

* crossroads with more than 4 edges & some amenities/leisures around

## (33) Night life

* Spaetis, Bars, Pub, Gambling, ... (use amenity tag)
* also could use opening hours as an indicator
* aminity=bar|pub
* amenity=cafe with good opening hours


## (34) change-points

* stops used by more than one line (probably use different data source besides openstreetmap like DVB)

## (38) row houses

* based on buildingGroups with more than 1 residential building

## (44) local townhall

* stored in amenity=townhall

## (47) health care centres

* rewritten into: use doctor practices, try amenity="pharmacy|doctors" , "healthcare=doctor|dentist|center"

## (50) T-Crossroads

* included into (23) but could be extra layer

## (66) & (70) holy ground

* churches, graveyard (thus including 70) and other places of worship
* use:  amenity=place_of_worship ,  landuse=cemetery

## (72) Local sport

* places for sport activities (public gym, sport centre, sport park, ..)
* leisure=sports_centre|stadium|track|pitch|horse_riding|swimming_pool|recreation_ground|golf_course
* club=sport
* ! sport tag (should include most of it)

## (89) grocery stores

* local ones including backeries, butcher, fruit shop (and try with supermarkets)
* shop = convenience|butcher|pastry|bakery

* then also add shop=supermarket (just a single node inside a huge building ... hard to get area here)
  
## (90) Bierhalle

* Spaetis, Doener, Pub, Gambling areas (leisure=adult_gaming_centre|amusement_arcade)
* more suspicious than normal night life

* amenity=pub
* smoking=yes (maybe start only trying this one)
* openinghours=24/7 ?

## (91) Inn ? ()

* try tourism=guest_house

* mostly pension like
* no hotels or apartments 