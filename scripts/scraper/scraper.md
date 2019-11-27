# Scrapping data

* yellow pages
  * many entries without useable address (f.i. street is missing) 
  * classification of companies by branch
   
* handelsregister (umfangreicher)
  * https://www.online-handelsregister.de/handelsregisterauszug/sn/Dresden
  * well structured and complete data (uses standarised localbusiness schema)


## Execution

* scrapy crawl \<Botname> -o \<outFile>.csv [--loglevel=ERROR]
* use `localizeCompanies.py` to get coordinates for every company scraped (extra method and not at scraping time, as each individual task takes quite a time already)
