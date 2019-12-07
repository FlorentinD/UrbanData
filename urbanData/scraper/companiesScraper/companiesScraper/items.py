# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class Company(scrapy.Item):
    name = scrapy.Field()
    street = scrapy.Field()
    postalCode = scrapy.Field()
    # simliar to city f.i. Dresden-Pieschen but could also be just Dresden
    area = scrapy.Field()
    branch = scrapy.Field()
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass

class CompanyLoader():
    def createCompanyFromLocalBusiness(self, properties):
        company = Company()
        company["name"] = properties["name"]
        company["branch"] = properties.get("branch", "")

        address = properties["address"]
        if isinstance(address, str):
            if address == ",  ":
                company["address"] = ""
        elif isinstance(address, dict) and address["type"] == 'http://schema.org/PostalAddress':
            address = address["properties"]
            company["street"] = address["streetAddress"]
            company["postalCode"] = address["postalCode"]
            company["area"] = address["addressLocality"]
        else:
            company = None
    
        return company


# [{'type': 'http://schema.org/LocalBusiness',
#             'properties': {'name': 'A & A Gastronomie GmbH',
#                             'address': {'type': 'http://schema.org/PostalAddress',
#                             'properties': {'streetAddress': 'Wilischstr. 22',
#                             'postalCode': '01279',
#                             'addressLocality': 'Dresden'}}}}