import re
from datetime import datetime

import scrapy

from gazette.items import Gazette
from gazette.spiders.base import BaseGazetteSpider


class BaseAdiariosV3Spider(BaseGazetteSpider):
    """
    This base class deals with 'Layout 3' gazette pages, usually requested
    from https://{city_website}/diariolista.php
    """

    def start_requests(self):
        start_date = self.start_date.strftime("%d/%m/%Y")
        end_date = self.end_date.strftime("%d/%m/%Y")

        request = scrapy.Request(
            f"{self.BASE_URL}/diariolista.php?dtini={start_date}&dtfim={end_date}",
            callback=self.parse_pagination,
        )

        yield request

    def parse_pagination(self, response):
        last_page_number = self.get_last_page_number(response)

        for page_number in range(0, last_page_number):
            yield scrapy.Request(
                f"{response.url}&pagina={page_number}", callback=self.parse_page
            )

        yield from self.parse_page(response)

    def parse_page(self, response):
        links = response.xpath('//a[has-class("list-group-item")]/@href').getall()

        texts = response.xpath(
            '//h4[has-class("list-group-item-heading")]//text()'
        ).getall()

        dates = response.xpath(
            '//a[has-class("list-group-item")]//span/text()'
        ).getall()

        for link, text, raw_date in zip(links, texts, dates):
            date = datetime.strptime(raw_date.strip(), "%d/%m/%Y").date()
            edition_number, is_extra_edition = self.get_edition_info(text)
            file_url = response.urljoin(link)
            power = "executive"

            gazette = Gazette(
                date=date,
                edition_number=edition_number,
                is_extra_edition=is_extra_edition,
                power=power,
                file_urls=[file_url],
            )

            yield gazette

    def get_last_page_number(self, response):
        page_pagination = response.css(".pagination li a span::text").getall()
        last_page_index = max([int(i) for i in page_pagination])

        return last_page_index

    def get_edition_info(self, text):
        try:
            # Edtion number with extraordinary edition or ordinary edition
            edition_number = re.search(r":\s*(\d+\.\d|\d+).*/", text).group(1)
        except AttributeError:
            edition_number = ""

        # Edition number with a subedition number is a extra edition
        is_extra_edition = bool(re.search(r"\d+\.\d", edition_number))

        return edition_number, is_extra_edition
