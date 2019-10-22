import osmapi as osm

api = osm.OsmApi()

# maybe store this locally if this is the fixed area
dresdenPieschen = api.Map(13.72098, 51.07177, 13.74452, 51.08448)

dataSchema = {}
tags = []
for item in dresdenPieschen:
    type: str = item["type"]
    tag: dict = item["data"]["tag"]
    if tag: 
        tags.append(tag)
    if type not in dataSchema:
        dataSchema[type] = set()
    else:  
        [dataSchema[type].add(key) for key in item["data"].keys()]

tagCombinations = set()
for tag in tags:
    tagKeys = list(tag.keys())
    tagKeys.sort()
    if tagKeys:
        tagString = '|'.join(tagKeys)
        
        tagCombinations
        tagCombinations.add(tagString)

# Some tag combinations
[print(comb) for comb in list(tagCombinations)[:10]]

print(dataSchema)