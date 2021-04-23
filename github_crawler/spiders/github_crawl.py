import csv
import os
from datetime import datetime
from time import gmtime, strftime

import scrapy
from scrapy import FormRequest
from scrapy.crawler import CrawlerProcess

from info import *


class GithubCrawlSpider(scrapy.Spider):
    name = 'github-crawl'
    start_urls = ["https://github.com/login"]

    def parse(self, response, **kwargs):
        token = response.css(
            "#login > div.auth-form-body.mt-3 > form > input[type=hidden]:nth-child(1)::attr(value)").get()

        yield FormRequest.from_response(response, formdata={
            "authenticity_token": token,
            "login": login,
            "password": password
        }, callback=self.after_login)

    def after_login(self, response):
        yield response.follow(response.url + f"/{login}?tab=repositories&type=source", callback=self.parse_repo)

    def parse_repo(self, response):
        filename = f"[{strftime('%Y-%m-%d', gmtime())}] github_repo.csv"
        file_exists = os.path.exists(filename)

        with open(filename, 'a+') as file:
            writer = csv.writer(file)

            if not file_exists:
                writer.writerow(["Name", "Description", "Updated", "Link"])

            repo_details = response.css("#user-repositories-list > ul > li > div.col-10.col-lg-9.d-inline-block")
            for repo in repo_details:
                title = repo.css("div.d-inline-block.mb-1 > h3 > a::text").get().strip()
                desc = repo.css("p[itemprop=description]::text").get()

                date = repo.css("div.f6.color-text-secondary.mt-2 > relative-time::attr(datetime)").get()
                updated = datetime.now() - datetime.strptime(date, '%Y-%m-%dT%H:%M:%SZ')

                url = "https://github.com" + repo.css("div.d-inline-block.mb-1 > h3 > a::attr(href)").get()

                if desc is not None:
                    writer.writerow([title, desc.strip(), updated, url])
                else:
                    writer.writerow([title, 'No description', updated, url])

        pagination = response.css(
            "#user-repositories-list > div.paginate-container > div[data-test-selector=pagination] > a")

        if pagination.css("::text").get() == "Next":
            yield response.follow(pagination.css("::attr(href)").get(), callback=self.parse_repo)


if __name__ == "__main__":
    process = CrawlerProcess()
    process.crawl(GithubCrawlSpider)
    process.start()
