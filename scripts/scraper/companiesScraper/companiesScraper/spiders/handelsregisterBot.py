# -*- coding: utf-8 -*-
import scrapy
import re
from companiesScraper.items import CompanyLoader
from extruct.w3cmicrodata import MicrodataExtractor

class HandelsregisterbotSpider(scrapy.Spider):
    name = 'handelsregisterBot'
    #allowed_domains = ['https://www.online-handelsregister.de/handelsregisterauszug/sn/Dresden']
    start_urls = ['https://www.online-handelsregister.de/handelsregisterauszug/sn/Dresden/']
    mde = MicrodataExtractor()
 
    def parse(self, response):
        letterSections = response.css(".btn.btn-lg.btn-default::attr(href)").extract()
        
        # TODO: remove if working
        for relLink in letterSections:
            full_url = response.urljoin(relLink)
            yield scrapy.Request(full_url, callback=self.parse_letterSection)


    def parse_letterSection(self, response):
        companyPages = response.css(".col-md-8").css(".list-group-item::attr(href)").extract()
        
        # last item is the next button
        paginationHTML = response.css(".pagination").css("li").extract()
        if paginationHTML:
            nextHTML = paginationHTML[-1]
            nextPageMatch = re.match(r'.*href="(.*/list\?page=\d+)"', nextHTML)
            if nextPageMatch:
                link = nextPageMatch.group(1)
                yield scrapy.Request(link, callback=self.parse_letterSection)            

        for relLink in companyPages:
            full_url = response.urljoin(relLink)
            yield scrapy.Request(full_url, callback=self.parse_companyPage)
    
    def parse_companyPage(self, response):
        # only save active companies
        activeRegExp = re.compile(".*Status:.*aktiv", re.DOTALL)
        companyText = response.css(".col-md-8").extract()[0]
        metaData = self.mde.extract(companyText)

        if activeRegExp.search(companyText) and metaData:
            companyDetails = metaData[0]
            if companyDetails["type"] == 'http://schema.org/LocalBusiness':
                companyProperties = companyDetails["properties"]
                yield CompanyLoader().createCompany(companyProperties)   
            else:
                raise ValueError("company details page did not contain localBusiness but {}".format(metaData))


# startPoint: css class "btn btn-lg btn-default" , href for list of companies starting with same letter

# then css class "col-md-8" contains a list 
#       css class list-group-item , href for direkt link to company info page
#       (rel="next") for containing links to additional pages with the same start letter
#           <a href="https://www.online-handelsregister.de/handelsregisterauszug/sn/Dresden/A/list?page=2" rel="next"> 


# company info page:
#   class "col-md-8" contains info 
#       span itemprop "name" | "address" | "streetAddress" | "postalCode" | "addressLocality"
#       <span style="font-weight: bold; color: #00AA00;">aktiv</span> -- only add aktiv companies?! (probably filter via color)

