from pupa.scrape import Scraper
from pupa.scrape import Person

import lxml.html
class MiamidadePersonScraper(Scraper):

    def lxmlize(self, url):
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)
        return doc

    def scrape(self):
        yield from self.get_people()
        #committees can go in here too

    def get_people(self):
        people_base_url = "http://miamidade.gov/wps/portal/Main/government"
        doc = self.lxmlize(people_base_url)
        person_list = doc.xpath("//div[contains(@id,'elected')]//span")
        titles = ["Chairman","Vice Chair"]

        for person in person_list:
            info = person.text_content().strip().split("\r")
            position = info[0].strip()
            name = " ".join(info[1:-1])
            name = name.replace("Website | Contact", "")
            for title in titles:
                name = name.replace(title,"")
            name = name.strip()
            url = person.xpath(".//a[contains(text(),'Website')]/@href")[0]
            image = person.xpath(".//img/@src")[0]
            if position.startswith('District'):
                pers = Person(
                    name=name,
                    image=image,
                    district=f"{position} Commissioner",
                    primary_org='legislature',
                    role="Commissioner",
                )

            else:
                continue
