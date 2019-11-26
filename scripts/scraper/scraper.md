# Scrapping data

* yellow pages
    
* handelsregister (umfangreicher)
  * https://www.online-handelsregister.de/handelsregisterauszug/sn/Dresden


## Execution

* scrapy crawl \<Botname> -o \<outFile>.csv [--loglevel=ERROR]
* use `localizeCompanies.py` to get coordinates for every company scraped (extra method and not at scraping time, as each individual task takes quite a time already)