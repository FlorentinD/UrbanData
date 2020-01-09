# Pattern

* hard to find a raster --> use voronoi diagrams (use scipy)

## (16) public transport

* use webservice for _5-minute walk areas_ around stops

## (21) at most 4 building-level

* rooftop level does not count extra here

## (22) 9% parking lots

* only partyl tagged
* based on ground areas

## (23) parallel streets

* at what point are 2 streets parallel?
* rewritten into: crossroads with 3-4 edges (excluding bigger crossroads) , these are not specially tagged
* roundabouts tagged in openstreetmap with _highway=mini_roundabout_

## (30) activity nodes

* crossroads with more than 4 edges & some amenities/leisures around

## (33) Night life

* Spaetis, Bars, Pub, Gambling, ... (use amenity tag)
* also could use opening hours as an indicator


## (34) change-points

* stops used by more than one line (probably use different data source besides openstreetmap like DVB)

## (38) row houses

* based on buildingGroups with more than 1 residential building

## (44) local townhall

* stored in amenity tag

## (47) health care centres

* rewritten into: use doctor practices

## (50) T-Crossroads

* included into (23) but could be extra layer

## (66) & (70) holy ground

* churches, graveyard (thus including 70) and other places of worship

## (72) Local sport

* places for sport activities (public gym, sport centre, sport park, ..)

## (89) grocery stores

* local ones including backeries, butcher, fruit shop (and try with supermarkets)

## (90) Bierhalle

* Spaetis, Doener, Pub, Gambling areas (leisure=adult_gaming_centre|amusement_arcade)
* more suspicious than normal night life

## (91) Inn

* mostly pension like
* no hotels or apartments 