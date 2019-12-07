# -*- coding: utf-8 -*-
import scrapy
from companiesScraper.items import Company

# scrapy crawl yellowPagesBot -o yellowPages_Dresden.csv --loglevel=ERROR
# some companies only have a telefon number but no address incl. Buergerbueros
class YellowpagesbotSpider(scrapy.Spider):
    name = 'yellowPagesBot'
    #allowed_domains = ['https://www.gelbeseiten.de/branchenbuch/staedte/sachsen/kreisfrei/Dresden/unternehmen/%23?page=1']
    start_urls = ['https://www.gelbeseiten.de/branchenbuch/staedte/sachsen/kreisfrei/Dresden/unternehmen/%23?page=1/']

    def parse(self, response):
        letterSections = response.css(".alphabetfilter__btn::attr(href)").extract()
        # as start_url already is a letterPage
        self.parseLetterPage(response.url)

        for relLink in letterSections:
            full_url = response.urljoin(relLink)
            yield scrapy.Request(full_url, callback=self.parseLetterPage)

    def parseLetterPage(self, response):
        nextPage = response.css(".pagination__arrow.pagination__arrow--next").css("a::attr(href)").extract()
        
        if nextPage:
            nextPageUrl = response.urljoin(nextPage[0]) 
            # on last page next points to current page
            if not (nextPageUrl == response.url):
                yield scrapy.Request(nextPageUrl, callback=self.parseLetterPage)

        companyPages = response.css(".link::attr(href)").extract()

        for companyPage in companyPages:
            # only for safety as these should be absolute links
            companyPage = response.urljoin(companyPage)
            yield scrapy.Request(companyPage, callback=self.parseCompanyPage)

    def parseCompanyPage(self, response):
        branchAndDetailBox = response.css(".mod-TeilnehmerKopf__teilnehmerdaten-wrapper")
        detailBox = branchAndDetailBox.css(".mod-TeilnehmerKopf__teilnehmerdaten")
        streetAndPostalCode = detailBox.css(".mod-TeilnehmerKopf__adresse-daten::text").extract()
        city = detailBox.css(".mod-TeilnehmerKopf__teilnehmerdaten").css(".mod-TeilnehmerKopf__adresse-daten--noborder::text").extract()
        name = detailBox.css(".mod-TeilnehmerKopf__name::text").extract()
        company = Company()
        company["branch"] = ";".join(branchAndDetailBox.css(".mod-TeilnehmerKopf__branchen").css(".list-unstyled").css("li::text").extract())

        # city not needed, if street and postalcode are given
        if len(streetAndPostalCode) == 2 and name:
            company["name"] = name[0]
            company["street"] = streetAndPostalCode[0]
            company["postalCode"] = streetAndPostalCode[1]
            if(city):
                company["area"] = city
            else:
                company["area"] = ""
            yield company
        else:
            self.logger.error("Missing address information name: {}, {}, city: {} .. url: {}".format(name, streetAndPostalCode, city, response.url))
        

# ! start_url already contains links
# <a class="alphabetfilter__btn" href="%23?page=1" data-char="#">#</a> single letter buttons
#   <a class="link" title="A.A.S. mobiler Schlossdienst in Dresden" for single companies pages
# <div class="pagination__arrow pagination__arrow--next"><a rel="next" href="a?page=2" class="gs-btn gs-btn--icon gs-btn--icon-r gs-btn--s gs-btn--bordered">

# single company pages (name, address, typ, website)
        
