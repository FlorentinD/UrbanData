from folium import Map, LayerControl, Icon
from helper.geoJsonToFolium import geoFeatureCollectionToFoliumFeatureGroup, generateFeatureCollectionForGroups
from helper.overPassHelper import OverPassHelper
from helper.OsmDataQuery import OsmDataQuery
from helper.OsmObjectType import OsmObjectType
from helper.crossRoadHelper import getCrossRoads
from helper.geoJsonHelper import unionFeatureCollections, groupBy, centerPoint, lineToPolygon
from helper.voronoiHelper import voronoiFeatureCollection
from helper.shapelyHelper import intersections
from annotater.buildingClassifier import BuildingType
import logging
import geojson
import re

# TODO: restructure into functions for pattern group
# TODO: get icons To work
logging.basicConfig(level=logging.DEBUG)
overpassFetcher = OverPassHelper()
dresdenAreaId = overpassFetcher.getAreaId("Dresden, Germany")
pieschenAreaId = overpassFetcher.getAreaId("Pieschen, Dresden, Germany")
saxonyAreaId = overpassFetcher.getAreaId("Saxony, Germany")

def lessThanEqual5Levels(properties):
    # TODO add option "OnlyWithRoofTop"
    levels = properties.get("building:levels", None)
    if levels:
        levels = int(levels)
        if levels <= 4:
            return "<= 4 levels"
        elif levels > 4:
            return "> 4 levels"
    else:
        estimation = properties.get("estimatedLevels", None) 
        if estimation == None:
            return "Unknown"
        if estimation <= 5:
            return "Maybe <= 5 levels"
        else:
            return "Maybe > 5 levels"

def openAtMidnight(openingHours):
    if openingHours == "24/7":
        return True
    else:
        matches = re.findall(r"(\d+):(\d+)\s*-\s*(\d+):(\d+)", openingHours)
        for openingHour, _, closingHour, _ in matches:
            # has open over midnight
            openingHour = int(openingHour)  
            closingHour = int(closingHour)  
            if (openingHour > closingHour) or openingHour in range(0,3) or closingHour in range(0,6):
                return True
        if not matches:
            matches = re.findall(r"(\d+)(:\d+)\+", openingHours)
            if matches:
                # TODO: 09:00+ -> maybe open at midnight even (could be extra group)
                return "Open end"
            else:
                logging.debug(openingHours)
        return False

def getOpenAtMidnightThings():
    thingsWithOpeningHour = next(OverPassHelper().directFetch(
        dresdenAreaId, 
        [OsmDataQuery(
            "Midnight things", 
            OsmObjectType.ALL, 
            ['"opening_hours"', 
            '"highway"!~"."',
            '"tourism"!~"."',
            '"leisure"!~"park|fitness_centre|bowling_alley|play_ground|playground"',
            '"amenity"!~"parking|atm|hospital|charging_station|toilets|car_|vending_|bank|restaurant|bar$|pub$|nightclub|stripclub|brothel|cinema|theatre|drinking_water|nursing_home|recycling|shower|police|bicycle_"'
            ])
        ]))
    # general problem: opening hours must be filled in and valid & what should be excluded
    # TODO: easier to state what tags are allowed?

    midnightThings = groupBy(thingsWithOpeningHour, lambda props: openAtMidnight(props["opening_hours"]))
    midnightThings.pop('False')
    return midnightThings

if __name__ == "__main__":
    COMPUTE_HEATMAPS = True
    COMPUTE_VORONOI = True

    map = Map(location=[51.078875, 13.728524], tiles='Open Street Map', zoom_start=15)

    logging.info("Get boundaries")
    boroughs = next(overpassFetcher.directFetch(
        dresdenAreaId, 
        [OsmDataQuery(
            "Area boundaries", 
            OsmObjectType.RELATIONSHIP, 
            ['"boundary"~"administrative"', '"admin_level"="11"']
            )
        ]))

    cityBoundary = next(overpassFetcher.directFetch(
        saxonyAreaId, 
        [OsmDataQuery(
            "Area boundaries", 
            OsmObjectType.RELATIONSHIP, 
            ['"boundary"~"administrative"', '"name"="Dresden"']
            )
        ]))

    boundaries = {
        "boroughs": boroughs,
        "city": cityBoundary
    }

    generateFeatureCollectionForGroups(boundaries, ["grey", "black"], "Boundaries", show=True).add_to(map)

    #busStopsOsmQuery = OsmDataQuery("Bus stops", OsmObject.NODE, ['"highway"~"bus_stop"'])
    pattern = "Public Transport (Pattern 16)"
    logging.info(pattern)
    stopsOsmQuery = OsmDataQuery(
        "Public Transport stops", 
        OsmObjectType.NODE, 
        ['"public_transport"="stop_position"', '"name"','"name"!~"(Ausstieg)"'])
    stops = next(overpassFetcher.directFetch(dresdenAreaId, [stopsOsmQuery]))
    stopsByName = []

    for name, group in groupBy(stops, "name").items():
        center = centerPoint(group)
        # TODO: more properties?
        # TODO: maybe draw line instead of just center point?
        properties = {
            "name": name,
            "stop_positions": len(group["features"])
        }
        stopByName = geojson.Feature(geometry=center, properties=properties)
        stopsByName.append(stopByName)

    # Simple stops
    geoFeatureCollectionToFoliumFeatureGroup(geojson.FeatureCollection(stopsByName), '#990000', pattern, show= False).add_to(map)

    try:
        pattern = "5 minute walk area around stops"
        logging.info(pattern)
        with open("out/data/timeMapsPerStop.json", encoding='UTF-8') as file:
            timeMaps = geojson.load(file)
        # removes duplicates (empty name and containing "(Ausstieg)") (can be removed when timeMaps are recomputed)
        if COMPUTE_HEATMAPS:
            timeMaps = geojson.FeatureCollection(
                [t for t in timeMaps["features"]
                if t["properties"].get("name") and not "(Ausstieg)" in t["properties"]["name"]]
            )
            heatMapGroups = intersections(timeMaps)
            generateFeatureCollectionForGroups(heatMapGroups, ["#0000cc", "#ff00ff"], pattern, show=False).add_to(map)
        else:
            logging.info("skipped heatmap generation")
            geoFeatureCollectionToFoliumFeatureGroup(timeMaps, '#990000', pattern, show = False).add_to(map)
    except FileNotFoundError:
        logging.error("run timeMapsRetriever to get time maps")

    # (34) change-points
    pattern = "Public Transport Change Points (Pattern 34)"
    logging.info(pattern)

    try:
        with open("out/data/dvbChangePoints.json", encoding='UTF-8') as file:
            changePoints = geojson.load(file)
            
        # replacing E as these are just substitute lines for another line like E8 and 8
        changePointsPerLineCount = groupBy(
            changePoints, 
            lambda props: len([line for line in props.get("lines", []) if not line.strip().startswith("E")]))
        changePointsPerLineCount.pop("1")
        generateFeatureCollectionForGroups(
            changePointsPerLineCount, ['#000099', "#cc0099"], pattern, show=False).add_to(map)
    except FileNotFoundError:
        logging.error("run dvbRetriever to get info about change Points")
        
    ###################
    # use buildingGroups (only for !!pieschen!!) 
    pattern = "At most 4 Building-level (Pattern 21)"
    logging.info(pattern)

    try:
        with open("out/data/buildings_pieschen.json", encoding='UTF-8') as file:
            buildings = geojson.load(file)
        with open("out/data/buildingGroups_pieschen.json", encoding='UTF-8') as file:
            buildingGroups = geojson.load(file)
    except FileNotFoundError:
        logging.error("run buildingComplexes to get buildings and their groups")

    buildingsByLevelRestriction = groupBy(buildings, lessThanEqual5Levels)
    if len(buildingsByLevelRestriction) == 2:
        logging.warn("Only one building level found. Maybe the file is not correct. Rebuild via buildingComplexex.py !")
    generateFeatureCollectionForGroups(
        buildingsByLevelRestriction, 
        {
            "<= 4 levels": "#33cc33", 
            "> 4 levels": "#ff0000", 
            "Maybe <= 5 levels": "#cccc00",
            "Maybe > 5 levels": "#ff3300",
            "Unknown": "#a3a3c2" 
        }, 
        pattern, 
        show=False
        ).add_to(map)


    pattern = "Row houses (Pattern 38)"
    # TODO !!! fix address annotation from osm data (probably node data unused (right shapely op?))
    # example https://www.openstreetmap.org/node/2480574494
    residentalBuildingGroups = []
    for group in buildingGroups["features"]:
        # TODO: more suffisticated function? (could also include building type and number of addresses)
        # only include buildings that are living or have no building type
        # not ("type" in f["properties"]) or "residential" in f["properties"]["type"]]
        if BuildingType.RESIDENTIAL.value in group["properties"]["type"] or group["properties"]["type"] == [] :
            residentalBuildingGroups.append(group)
    residentalBuildingGroups = geojson.FeatureCollection(residentalBuildingGroups)

    rowHouseGroups = groupBy(residentalBuildingGroups, lambda properties: "RowHouses" if sum([houseNumbers for houseNumbers in properties["addresses"].values()]) > 1 else "SingleHouses")
    generateFeatureCollectionForGroups(rowHouseGroups, {"RowHouses": "#996633", "SingleHouses": "#ff9900"}, pattern, show=False).add_to(map)


    ############ cross roads

    logging.info("Searching for crossroads")

    # ! not counting service crossroad as these are not "real" cross roads (probably way less traffic I assume)
    # also excluding: link streets 
    streets = next(overpassFetcher.directFetch(
        dresdenAreaId,
        [OsmDataQuery(
            "streets", 
            OsmObjectType.WAY, 
            ['"highway"~"primary$|secondary$|tertiary$|residential$|motorway$|unclassified"']
        )]
    ))

    crossRoads, roundAbouts = getCrossRoads(streets)
    crossRoadsByEdgeCount = groupBy(crossRoads, "edgeCount")

    pattern = "T-CrossRoads (Pattern 50)"
    geoFeatureCollectionToFoliumFeatureGroup(crossRoadsByEdgeCount["3"], "black", pattern, show= False).add_to(map)
    generateFeatureCollectionForGroups(crossRoadsByEdgeCount, ["#003399", "#00ffff"], "All CrossRoads", show= False).add_to(map)
    geoFeatureCollectionToFoliumFeatureGroup(roundAbouts, "green", "Round Abouts", show= False).add_to(map)

    ##########

    pattern = "Night Life (Pattern 33)"
    logging.info(pattern)
    nightLifeOsmQuery = OsmDataQuery("Night Life", OsmObjectType.ALL, ['"amenity"~"bar$|pub$|nightclub|stripclub"'])
    nightLife = next(overpassFetcher.directFetch(dresdenAreaId, [nightLifeOsmQuery]))
    nightLifeGroups = groupBy(nightLife, "amenity")
    generateFeatureCollectionForGroups(nightLifeGroups, ["#660033", "#6600ff"], pattern, show=False).add_to(map)


    """ 
    # Pattern was decided to be not considerable due to parking at the side of the road which are not marked in openStreetMap
    pattern = "Parking lots (Pattern 22)"
    logging.info(pattern)
    parkingOsmQuery = OsmDataQuery("Parking Lots", OsmObjectType.WAYANDNODE, ['"amenity"="parking"'])
    parkingLots = next(overpassFetcher.directFetch(pieschenAreaId, [parkingOsmQuery]))
    # TODO: count parking lots on roofs/underground?
    # TODO: calculating base area for each parking lot? (idealy using a annotater)
    geoFeatureCollectionToFoliumFeatureGroup(parkingLots, 'grey', pattern).add_to(map) 
    """


    pattern = "Town Halls (Pattern 44)"
    logging.info(pattern)
    townHallOsmQuery = OsmDataQuery("Town Halls", OsmObjectType.ALL, ['"amenity"="townhall"'])
    townHalls = next(overpassFetcher.directFetch(dresdenAreaId, [townHallOsmQuery]))

    townHallAreas = next(overpassFetcher.directFetch(
        dresdenAreaId,
        [OsmDataQuery(
            "Dreasen boundaries",
            OsmObjectType.RELATIONSHIP,
            ['"boundary"~"administrative"', 'name',
                '"name:prefix"="Ortsamtsbereich"']
        )
        ]))

    townHallAreas = geojson.FeatureCollection([geojson.Feature(
        geometry=lineToPolygon(feature["geometry"]),
        properties=feature["properties"]
        )
        for feature in townHallAreas["features"]])

    generateFeatureCollectionForGroups(
        {"areas": townHallAreas, "town halls": townHalls},
        ["grey", "red"],
        pattern,
        show=False).add_to(map)

    try:
        pattern = "15 minutes area around town halls (public transport)"
        logging.info(pattern)
        with open("out/data/timeMapsPerCityHall.json", encoding='UTF-8') as file:
            timeMaps = geojson.load(file)
        if COMPUTE_HEATMAPS:
            heatMapGroups = intersections(timeMaps, kindOfFeatures="town halls")
            generateFeatureCollectionForGroups(heatMapGroups, ["#0000cc", "#9900cc"], pattern, show=False).add_to(map)
        else:
            logging.info("skipped heatmap generation")
            geoFeatureCollectionToFoliumFeatureGroup(timeMaps, '#990000', pattern, show = False).add_to(map)
    except FileNotFoundError:
        logging.error("run timeMapsRetriever to get time maps")


    pattern = "Health Care (Pattern 47)"
    logging.info(pattern)
    pharmacyQuery = OsmDataQuery("amenity health", OsmObjectType.ALL, ['"amenity"~"pharmacy"'])
    healthAmenityQuery = OsmDataQuery("amenity health", OsmObjectType.ALL, ['"amenity"~"doctors"'])
    healthCareQuery = OsmDataQuery(
        "health care", 
        OsmObjectType.ALL, 
        ['"healthcare"~"doctor|dentist|center"', '"amenity"!~"pharmacy|doctors"'])
    osmResult = overpassFetcher.directFetch(dresdenAreaId, [pharmacyQuery ,healthAmenityQuery, healthCareQuery])

    healthGroups = {
        "pharmacies": next(osmResult),
        "doctors":  unionFeatureCollections(*osmResult)
        }
    #TODO: get icons to work
    """ icons = {
        "pharmacies": Icon(icon="pills", color='lightgray', icon_color = 'red'), 
        "doctors": Icon(icon="suitcase-doctor", color='lightgray', icon_color = 'red')
        } """
    generateFeatureCollectionForGroups(healthGroups, "tab10", pattern, iconMap={}, show= False).add_to(map)

    try:
        pattern = "5 minutes walking area around pharmacies"
        logging.info(pattern)
        with open("out/data/timeMapsPerPharmacy.json", encoding='UTF-8') as file:
            timeMaps = geojson.load(file)
        if COMPUTE_HEATMAPS:
            heatMapGroups = intersections(timeMaps, maxIterations=2, kindOfFeatures="pharmacies")
            generateFeatureCollectionForGroups(heatMapGroups, ["#0000cc", "#9900cc"], pattern, show=False).add_to(map)
        else:
            logging.info("skipped heatmap generation")
            geoFeatureCollectionToFoliumFeatureGroup(timeMaps, '#990000', pattern, show = False).add_to(map)
    except FileNotFoundError:
        logging.error("run timeMapsRetriever to get time maps")


    pattern = "Holy Ground (Pattern 66 & 70)"
    logging.info(pattern)
    holyOsmQuery = OsmDataQuery("Religious Things", OsmObjectType.ALL, ['"amenity"~"place_of_worship"'])
    graveyardOsmQuery = OsmDataQuery("Cementries", OsmObjectType.ALL, ['"landuse"~"cemetery"'])
    osmResult = overpassFetcher.directFetch(dresdenAreaId, [holyOsmQuery, graveyardOsmQuery])
    holygrounds = {
        "places of worship": next(osmResult),
        "cementries": next(osmResult)
    }
    generateFeatureCollectionForGroups(holygrounds, 'copper', pattern, show = False).add_to(map)



    pattern = "LocalSport (Pattern 72)"
    logging.info(pattern)
    sportsQuery = OsmDataQuery("Local Sport", OsmObjectType.ALL, ["sport", '"sport"!="no"' , '"opening_hours"!~"."'])
    fitnessCentreQuery = OsmDataQuery("Local Sport", OsmObjectType.ALL, ['"leisure"~"fitness_centre"'])
    osmResult = overpassFetcher.directFetch(dresdenAreaId, [sportsQuery, fitnessCentreQuery])
    sports = next(osmResult)
    fitnessCentres = next(osmResult)
    geoFeatureCollectionToFoliumFeatureGroup(sports, 'green', pattern, show= False).add_to(map)
    #geoFeatureCollectionToFoliumFeatureGroup(fitnessCentres, 'brown', "FitnessCentres (also sports)", show=False).add_to(map)


    # alternatives: leisure=sports_centre|stadium|track|pitch|horse_riding|swimming_pool|recreation_ground|golf_course
    #       or club=sport


    pattern = "Local grocery store (Pattern 89)"
    logging.info(pattern)
    groceryQuery = OsmDataQuery("Local grocery store", OsmObjectType.ALL, ['"shop"~"convenience|butcher|pastry|bakery|supermarket"'])
    grocery = next(overpassFetcher.directFetch(dresdenAreaId, [groceryQuery]))
    groceryGroups = groupBy(grocery, "shop")
    generateFeatureCollectionForGroups(
        groceryGroups,
        {
            "convenience": "#006600",
            "butcher": "#ff0000",
            "pastry": "#ffcc00",
            "bakery": "#ff9900",
            "supermarket": "#007399"
        },
        pattern,
        show=False).add_to(map)



    # rooted in Pattern 90 Bierhalle (but now very different)
    pattern = "Open at midnight (excluding nightlife)"
    logging.info(pattern) 

    generateFeatureCollectionForGroups(
        getOpenAtMidnightThings(), {
            "True": '#000066',
            "Open end": '#666699'
        },
        pattern,
        show=False).add_to(map)

    try:
        pattern = "5 minutes walking area around things open at midnight"
        logging.info(pattern)
        with open("out/data/timeMapsPerMidnightThingOpenEnd.json", encoding='UTF-8') as file:
            openEndTimeMaps = geojson.load(file)
        with open("out/data/timeMapsPerMidnightThing.json", encoding='UTF-8') as file:
            openAtMidnightTimeMaps = geojson.load(file)
        if COMPUTE_HEATMAPS:
            heatMapGroups = intersections(
                unionFeatureCollections(openAtMidnightTimeMaps, openEndTimeMaps), 
                maxIterations=2, 
                kindOfFeatures="places open at midnight")
            generateFeatureCollectionForGroups(heatMapGroups, ["#0000cc", "#9900cc"], pattern, show=False).add_to(map)
        else:
            logging.info("skipped heatmap generation")
            geoFeatureCollectionToFoliumFeatureGroup(openEndTimeMaps, '#666699', pattern, show = False).add_to(map)
            geoFeatureCollectionToFoliumFeatureGroup(openAtMidnightTimeMaps, '#000066', pattern, show = False).add_to(map)
    except FileNotFoundError:
        logging.error("run timeMapsRetriever to get time maps")


    pattern = "Green area"
    logging.info(pattern)
    allotmentsAndForestQuery = OsmDataQuery("Forests", OsmObjectType.WAYANDRELATIONSHIP, ['"landuse"~"allotments|forest"'])
    gardenAndParkQuery = OsmDataQuery("Garden and parks", OsmObjectType.WAYANDRELATIONSHIP, ['"leisure"~"garden|^park$"', '"access"!~"private"'])
    osmResult = overpassFetcher.directFetch(dresdenAreaId, [allotmentsAndForestQuery, gardenAndParkQuery])
    allotmentsAndForest = groupBy(next(osmResult), "landuse")
    gardenAndParks = groupBy(next(osmResult), "leisure")
    greenAreas = {**allotmentsAndForest, **gardenAndParks}
    generateFeatureCollectionForGroups(greenAreas, ["#006600", "#00e673"], pattern, show=False).add_to(map)

    if COMPUTE_VORONOI: 
        logging.info("Computing voronoi diagrams")

        # Check for single boundary feature
        assert(len(cityBoundary["features"]) == 1)
        dresdenBorder = cityBoundary["features"][0]
        groceryVoronoi = voronoiFeatureCollection(grocery, mask=dresdenBorder)
        supermarketVoronoi = voronoiFeatureCollection(groceryGroups["supermarket"], mask=dresdenBorder)

        geoFeatureCollectionToFoliumFeatureGroup(groceryVoronoi, "#996633", "Grocery store voronois", show = False).add_to(map)
        geoFeatureCollectionToFoliumFeatureGroup(supermarketVoronoi, "#0000ff", "Supermarket voronoi", show = False).add_to(map)

        worshipVoronoi = voronoiFeatureCollection(holygrounds["places of worship"], mask=dresdenBorder)
        cementryVoronoi = voronoiFeatureCollection(holygrounds["cementries"], mask=dresdenBorder)
        geoFeatureCollectionToFoliumFeatureGroup(cementryVoronoi, 'grey', "cementry voronoi", show=False).add_to(map)
        geoFeatureCollectionToFoliumFeatureGroup(worshipVoronoi, 'black', "Places of worship voronoi", show=False).add_to(map)

        townHallVoronoi = voronoiFeatureCollection(townHalls, mask=dresdenBorder)
        geoFeatureCollectionToFoliumFeatureGroup(townHallVoronoi, 'Olive ', "cityhall voronoi", show=False).add_to(map)

        doctorsVoronoi = voronoiFeatureCollection(healthGroups["doctors"], mask=dresdenBorder)
        pharmacyVoronoi = voronoiFeatureCollection(healthGroups["pharmacies"], mask=dresdenBorder)
        geoFeatureCollectionToFoliumFeatureGroup(doctorsVoronoi, 'IndianRed ', "doctors voronoi", show=False).add_to(map)
        geoFeatureCollectionToFoliumFeatureGroup(pharmacyVoronoi, 'Crimson', "pharmacy voronoi", show=False).add_to(map)
    else:
        logging.info("skipped voronoi diagram generation")
    LayerControl().add_to(map)

    fileName = "out/maps/patternMap_Pieschen.html"
    logging.info("Starting to save map in {} (this might take a while)".format(fileName))
    map.save(fileName)
    logging.info("Map saved in {}".format(fileName))
