# -*- coding: utf-8 -*-
import scrapy


class YellowpagesbotSpider(scrapy.Spider):
    name = 'yellowPagesBot'
    allowed_domains = ['https://www.gelbeseiten.de/branchenbuch/staedte/sachsen/kreisfrei/Dresden/unternehmen/%23?page=1']
    start_urls = ['http://https://www.gelbeseiten.de/branchenbuch/staedte/sachsen/kreisfrei/Dresden/unternehmen/%23?page=1/']

    def parse(self, response):
		letterSections = response.css(".alphabetfilter__btn::attr(href)").extract()

		# as start_url is a letterPage
		self.parseLetterPage(response.url)

		for relLink in letterSections:
			full_url = response.urljoin(relLink)
			yield scrapy.Request(full_url, callback=parseLetterPage) 
        
	def parseLetterPage(self, response):
		nextPage = response.css(".pagination__arrow.pagination__arrow--next").css("a::attr(href)").extract()
		nextPageUrl = response.urljoin(nextPage) 
		
		# on last page next points to current page
		if not (nextPageUrl == response.url):
			yield scrapy.Request(nextPageUrl, callback=parseLetterPage)

		companyPages = response.css(".link::attr(href)").extract()

		for companyPage in companyPages:
			# only for safety as these should be absolute links
			companyPage = response.urljoin(companyPage)
			yield scrapy.Request(companyPage, parseCompanyPage)

	def parseCompanyPage(self, response):
		# TODO: find branch and co
		pass


# ! start_url already contains links
# <a class="alphabetfilter__btn" href="%23?page=1" data-char="#">#</a> single letter buttons
#   <a class="link" title="A.A.S. mobiler Schlossdienst in Dresden" for single companies pages
# <div class="pagination__arrow pagination__arrow--next"><a rel="next" href="a?page=2" class="gs-btn gs-btn--icon gs-btn--icon-r gs-btn--s gs-btn--bordered">

# single company pages (name, address, typ, website)
#   <li class="mod-Kontaktdaten__list-item">
			# 	<i class="icon-name"></i>
			# 	<address>
			# 		<strong>0-24 Schulze Schlüsseldienst Pieschen Trachau</strong>
			# 		<p>Alaunstr. 84</p>
			# 		<p>01099 Dresden-Äußere Neustadt</p>
			# 	</address>
			# </li>
    # <section id="branchen_und_stichworte">
	# 		<h2>Branche</h2>
	# 	<div class="mod mod-BranchenUndStichworte">
	# 		Schlüsseldienste
	# 	</div>
	# 		<h2>Stichworte</h2>
        
    # <a href="http://www.schulze-schluesseldienst-01099.de" target="_blank" title="http://www.schulze-schluesseldienst-01099.de" data-wipe="{"listener":"click", "name":"Detailseite Aktionsleiste Webadresse", "id":"1120091185890"}">
	# <div class="button">
	# 				<i class="icon-homepage"></i>
	# 				<span>Website</span>
	# 			</div>
	# 		</a>