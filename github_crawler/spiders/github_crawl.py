import csv
import os
from datetime import datetime, timezone, timedelta
from time import gmtime, strftime

import scrapy
from scrapy import FormRequest
from scrapy.crawler import CrawlerProcess

from info import *


def write_to_csv(filename, column_header, data):
    file_exists = os.path.exists(f"{filename}.csv")

    with open(f"{filename}.csv", 'a') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(column_header)

        writer.writerow(data)


def write_to_md(filename, data):
    title, desc, updated, language, link = data

    with open(f"{filename}.md", 'a') as file:
        file.write(f"# [{title}]({link})\n")
        file.write(f"###### Language: {language}\n")
        file.write(f"###### Updated: {updated}\n")
        file.write(f"### {desc.strip()}\n")


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
        filename = f"[{strftime('%Y-%m-%d', gmtime())}] github_repo"
        column_header = ["Title", "Description", "Updated", "Language", "Link"]

        repo_details = response.css("#user-repositories-list > ul > li > div.col-10.col-lg-9.d-inline-block")
        for repo in repo_details:
            title = repo.css("div.d-inline-block.mb-1 > h3 > a::text").get().strip()
            desc = repo.css("p[itemprop=description]::text").get()

            date = repo.css("div.f6.color-text-secondary.mt-2 > relative-time::attr(datetime)").get()
            PST = timezone(timedelta(hours=8))
            updated = datetime.now(tz=PST) - (datetime.strptime(date, '%Y-%m-%dT%H:%M:%S%z'))

            language = repo.css(
                "div.f6.color-text-secondary.mt-2 > span > span[itemprop=programmingLanguage]::text").get()

            url = "https://github.com" + repo.css("div.d-inline-block.mb-1 > h3 > a::attr(href)").get()

            if desc is not None:
                write_to_csv(filename, column_header, [title, desc.strip(), updated, language, url])
                write_to_md(filename, [title, desc.strip(), updated, language, url])
            else:
                write_to_csv(filename, column_header, [title, "No Description", updated, language, url])
                write_to_md(filename, [title, "No Description", updated, language, url])

        pagination = response.css(
            "#user-repositories-list > div.paginate-container > div[data-test-selector=pagination] > a")

        if pagination.css("::text").get() == "Next":
            yield response.follow(pagination.css("::attr(href)").get(), callback=self.parse_repo)


if __name__ == "__main__":
    process = CrawlerProcess()
    process.crawl(GithubCrawlSpider)
    process.start()
