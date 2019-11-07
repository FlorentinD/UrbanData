from owslib.wfs import WebFeatureService
from osgeo import ogr

def getWfsDescription(service: WebFeatureService) -> str:
    if service:
        id = service.identification.title
        contents = [name for name in service.contents.keys()]
        provider = service.provider.url
        return """ Service Description:
                    name: {}
                    provider: {}
                    contents: {}""".format(id, provider, contents)
    else:
        return "No service found"


wfs = WebFeatureService(
    url='https://kommisdd.dresden.de/net3/public/ogc.ashx?NodeId=120&Service=WFS', version='2.0.0')

print(getWfsDescription(wfs))

contentName = next(iter(wfs.contents.keys()))

# returns gml file
for content in wfs.contents.keys():
    response = wfs.getfeature(typename=content)
    out = open('out/data/{}_{}.gml'.format(wfs.identification.title, content.replace(':','_')), 'wb')
    out.write(bytes(response.read(), 'UTF-8'))
    out.close()

    #test = ogr.CreateGeometryFromGML(bytes(response.getvalue))
    # TODO: find working converter for gml to geojson