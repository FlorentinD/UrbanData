from owslib.wfs import WebFeatureService


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
boundingbox = wfs.contents[contentName].boundingBox

# returns gml file
response = wfs.getfeature(typename='cls:L83')

out = open('out/{}.gml'.format(wfs.identification.title), 'wb')
out.write(bytes(response.read(), 'UTF-8'))
out.close()
