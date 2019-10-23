import osmapi as osm

# Example analyses the data schema and which tags are often used
# Tags could be used to extract different layers (f.i. buildings)

api = osm.OsmApi()

# maybe store this locally if this is the fixed area
dresdenPieschen = api.Map(13.72098, 51.07177, 13.74452, 51.08448)

dataSchema = {}
tagsPerType = {}
for item in dresdenPieschen:
    type: str = item["type"]
    tag: dict = item["data"]["tag"]
    if tag:
        if type in tagsPerType.keys():
            tagsPerType[type].append(tag)
        else:
            tagsPerType[type] = list()
    if type not in dataSchema:
        dataSchema[type] = set()
    else:
        [dataSchema[type].add(key) for key in item["data"].keys()]

print("DataSchema: \n {}".format('\n'.join(
    ["\t Type: {} Schema: {}".format(x[0], x[1]) for x in dataSchema.items()])))

# Count occurence of tags
for type, tags in tagsPerType.items():
    tagCombinations = {}
    tagKeys = [list(tag.keys()) for tag in tags]

    for keys in tagKeys:
        isSubset = False

        if keys:
            # canonical label (only take main tags (therefore split))
            keys = sorted(list(set([key.split(':')[0] for key in keys])))
            keyString = '|'.join(keys)

            for tagCombination in list(tagCombinations.keys()):
                # test if subset of existing combinations
                if all(tag in tagCombination for tag in keys):
                    tagCombinations[tagCombination] += 1
                    isSubset = True

            if not isSubset:
                if keyString in tagCombinations:
                    tagCombinations[keyString] += 1
                else:
                    tagCombinations[keyString] = 1

    # Most used tag combinations
    popularTagCombinations = sorted(
        tagCombinations.items(), key=lambda kv: kv[1], reverse=True)
    print("Most used tags for {}".format(type))
    [print("\t {}: {}".format(comb[0], comb[1]))
     for comb in list(popularTagCombinations)[:10]]
