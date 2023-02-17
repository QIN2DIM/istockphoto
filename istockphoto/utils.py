# -*- coding: utf-8 -*-
# Time       : 2022/8/5 8:44
# Author     : QIN2DIM
# Github     : https://github.com/QIN2DIM
# Description:
import os.path
import sys
import typing
from urllib.request import getproxies

import requests
from bs4 import BeautifulSoup
from loguru import logger


def init_log(**sink_path):
    """Initialize loguru log information"""
    event_logger_format = (
        "<g>{time:YYYY-MM-DD HH:mm:ss}</g> | "
        "<lvl>{level}</lvl> - "
        # "<c><u>{name}</u></c> | "
        "{message}"
    )
    logger.remove()
    logger.add(
        sink=sys.stdout, colorize=True, level="DEBUG", format=event_logger_format, diagnose=False
    )
    if sink_path.get("error"):
        logger.add(
            sink=sink_path.get("error"),
            level="ERROR",
            rotation="1 week",
            encoding="utf8",
            diagnose=False,
        )
    if sink_path.get("runtime"):
        logger.add(
            sink=sink_path.get("runtime"),
            level="DEBUG",
            rotation="20 MB",
            retention="20 days",
            encoding="utf8",
            diagnose=False,
        )
    return logger


def load_memory(istock_database: str):
    memory = set()
    for fn in os.listdir(istock_database):
        if fn.endswith(".jpg"):
            memory.add(fn.replace(".jpg", ""))
    return memory


def parse_html_and_get_image_urls(response: requests.Response):
    container_img_urls = []

    soup = BeautifulSoup(response.text, "html.parser")
    gallery = soup.find("div", attrs={"data-testid": "gallery-items-container"})

    if not gallery:
        return container_img_urls
    img_tags = gallery.find_all("img")
    for tag in img_tags:
        container_img_urls.append(tag["src"])

    return container_img_urls


def handle_html(url: str, session: requests.Session) -> typing.Optional[requests.Response]:
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
        " Chrome/103.0.5060.134 Safari/537.36 Edg/103.0.1264.77"
    }
    proxies = getproxies()

    try:
        response = session.get(url, proxies=proxies, headers=headers)
    except requests.ConnectionError as err:
        logger.error(f"ConnectionError[HtmlHandler] - url={url} err={err}")
        return None
    else:
        if response.status_code != 200:
            logger.warning(f"Unexpected response status - code={response.status_code}")
            return None
        return response


def make_session() -> requests.Session:
    logger.debug(f"Init workers session")
    return requests.session()
