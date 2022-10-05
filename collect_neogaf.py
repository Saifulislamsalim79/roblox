# -*- coding: utf-8 -*-
import os
import traceback
from urllib import parse

import pandas as pd
from bs4 import BeautifulSoup
from selenium.webdriver.remote.webdriver import WebDriver

from helper import create_browser, logger, wait_for


class Spider:
  def __init__(self, browser: WebDriver):
    self.browser: WebDriver = browser
    self.soup: BeautifulSoup = None
    self.kw: str = None
    self.posts = []
    self.comments = []

  def yield_comment(self, post: dict):
    nodes = self.soup.select("article.message--post")
    for node in nodes:
      comment = dict()
      comment['post_id'] = post["id"]
      comment['post_url'] = post["url"]
      comment['id'] = node.get("id").split("-")[-1]
      comment['author'] = node.select_one(".message-name a.username").get_text().strip()
      comment['jobTitle'] = node.select_one(".userTitle").get_text().strip()
      comment['created_date'] = node.select_one("li.u-concealed time.u-dt").get("datetime")
      comment['content'] = node.select_one("div.bbWrapper").get_text().strip()
      yield comment

  def yield_post(self):
    nodes = self.soup.select("li.block-row")
    for node in nodes:
      post = dict()
      post["url"] = node.select_one("h3.contentRow-title a").get('href')
      post["url"] = parse.urljoin(self.browser.current_url, post["url"])
      post["id"] = post["url"].split("/")[-1].split(".")[-1]
      post["title"] = node.select_one("h3.contentRow-title a").get_text().strip()
      post["snippet"] = node.select_one("div.contentRow-snippet").get_text().strip()
      post['created_date'] = node.select_one(".contentRow-minor time.u-dt").get("datetime")
      yield post

  def __get(self, url, wait) -> bool:
    logger.info(f"visit {url}")
    try:
      self.browser.get(url)
      if wait:
        wait()
      self.soup = BeautifulSoup(self.browser.page_source, 'lxml')
      return True
    except:
      logger.error(f"访问 {url} 异常")
      traceback.print_exc()
      return False

  def find_posts(self):
    def parse_and_next(url: str):
      if not self.__get(url, lambda: wait_for(self.browser, "div.block-container")):
        return
      for post in self.yield_post():
        self.posts.append(post)
      next = self.browser.find_elements_by_css_selector("a.pageNavSimple-el--next")
      if next and len(next) > 0:
        next_url = parse.urljoin(self.browser.current_url, next[0].get_attribute('href'))
        parse_and_next(next_url)

    url = f"https://www.neogaf.com/search/3364483/?q={self.kw}&o=relevance"
    parse_and_next(url)

  def find_comments(self, post: dict):
    url = post["url"]
    if not self.__get(url, lambda: wait_for(self.browser, "article.message")):
      return
    for comment in self.yield_comment(post):
      self.comments.append(comment)

  def clear(self):
    self.posts.clear()
    self.comments.clear()

  def search_by_keyword(self, kw: str):
    self.kw = kw
    self.clear()
    self.find_posts()
    for post in self.posts:
      self.find_comments(post)

  def save(self, outdir: str):
    if not os.path.exists(outdir):
      os.makedirs(outdir)
    df_posts = pd.DataFrame(self.posts)
    df_posts.to_csv(f"{outdir}/{self.kw}.csv", index=False)
    logger.info(f"Save {len(df_posts)}'s posts")
    df_comments = pd.DataFrame(self.comments)
    df_comments.to_csv(f"{outdir}/{self.kw}-comments.csv", index=False)
    logger.info(f"Save {len(df_comments)}'s comments")


if __name__ == '__main__':
  browser = create_browser()
  spider = Spider(browser)
  try:
    spider.search_by_keyword("roblox")
  except:
    traceback.print_exc()
  finally:
    spider.save("neogaf_data")
    browser.close()