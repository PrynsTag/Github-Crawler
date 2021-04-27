from datetime import datetime

import pandas as pd
import scrapy
from dateutil import tz
from scrapy import FormRequest
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


def str_format_delta(td, fmt):
    d = {"days": td.days}
    d["hours"], rem_seconds = divmod(td.seconds, 3600)
    d["minutes"], d["seconds"] = divmod(rem_seconds, 60)
    return fmt.format(**d)


def write_to_md(df_proj, filename):
    with open(filename, 'w') as file:
        for row in df_proj.itertuples(index=False):
            title, desc, dt_updated, language, link = row

            dt = (datetime.now(tz.gettz("Asia/Manila")) - datetime.strptime(dt_updated, '%Y-%m-%dT%H:%M:%S%z'))
            fmt = "{days} day(s) {hours} hour(s) and {minutes} minute(s) ago"
            date_updated = str_format_delta(dt, fmt)

            file.write(f"# [{title}]({link})\n")
            file.write(f"###### Language: {language}\n")
            file.write(f"###### Updated: {date_updated}\n")
            file.write(f"### {desc}\n")


class GithubCrawlSpider(scrapy.Spider):
    name = 'github-crawl'
    allowed_domains = ["github.com"]
    start_urls = ["https://www.github.com/login"]

    def __init__(self, username, password, *args, **kwargs):
        super(GithubCrawlSpider, self).__init__(*args, **kwargs)
        self.username = username
        self.password = password
        self.repo_list = []

    def parse(self, response, **kwargs):
        token = response.xpath("//input[@name=\"authenticity_token\"]/@value").get()
        yield FormRequest.from_response(response, formdata={
            "authenticity_token": token,
            "login": self.username,
            "password": self.password
        }, callback=self.after_login)

    def after_login(self, response):
        yield response.follow(response.url + f"/{self.username}?tab=repositories&type=source", callback=self.parse_repo)

    def parse_repo(self, response):
        repo_details = response.css("#user-repositories-list > ul > li > div.col-10.col-lg-9.d-inline-block")
        for repo in repo_details:
            title = repo.css("div.d-inline-block.mb-1 > h3 > a::text").get().strip()

            desc = repo.css("p[itemprop=description]::text").get()
            desc = "No Description" if desc is None else desc.strip()

            dt = repo.css("div.f6.color-text-secondary.mt-2 > relative-time::attr(datetime)").get()

            language = repo.css(
                "div.f6.color-text-secondary.mt-2 > span > span[itemprop=programmingLanguage]::text").get()

            url = "https://github.com" + repo.css("div.d-inline-block.mb-1 > h3 > a::attr(href)").get()

            self.repo_list.append([title, desc, dt, language, url])

        pagination = response.css(
            "#user-repositories-list > div.paginate-container > div[data-test-selector=pagination] > a")
        if pagination.css("::text").get() == "Next":
            yield response.follow(pagination.css("::attr(href)").get(), callback=self.parse_repo)
        else:
            self.start_writing_files()

    def start_writing_files(self):
        column_header = ["Title", "Description", "Updated", "Language", "Link"]
        df_repo = pd.DataFrame(self.repo_list, columns=column_header)
        df_repo = df_repo.sort_values(by=["Language", "Updated"], ascending=False, ignore_index=True)

        df_repo.to_csv("Github-Repo.csv", index=False, header=column_header)

        py_df = df_repo[(df_repo["Language"] == "Python") | (df_repo["Language"] == "Jupyter Notebook")]
        kt_df = df_repo[df_repo["Language"] == "Kotlin"]
        php_df = df_repo[df_repo["Language"] == "PHP"]
        front_end_df = df_repo[(df_repo["Language"] == "HTML") |
                               (df_repo["Language"] == "CSS") |
                               (df_repo["Language"] == "Javascript")]

        write_to_md(py_df, "Python-Projects.md")
        write_to_md(kt_df, "Kotlin-Projects.md")
        write_to_md(php_df, "PHP-Projects.md")
        write_to_md(front_end_df, "Front-End-Projects.md")


if __name__ == "__main__":
    username = input("Enter your Github Username: ")
    password = input("Enter your Github Password: ")
    process = CrawlerProcess(settings=get_project_settings())
    process.crawl(GithubCrawlSpider, username, password)
    process.start()
