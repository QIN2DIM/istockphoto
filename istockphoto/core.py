# -*- coding: utf-8 -*-
# Time       : 2022/8/5 8:45
# Author     : QIN2DIM
# Github     : https://github.com/QIN2DIM
# Description:
from gevent import monkey

monkey.patch_all()
import os.path
import random
from typing import Optional, Union
from urllib.parse import urlparse
from urllib.request import getproxies

import gevent
import requests
import yaml
from bs4 import BeautifulSoup
from gevent.queue import Queue
from .utils import init_log

logger = init_log()

_MediaType = Optional[str]
_OrientationsType = Optional[str]
_NumberOfPeopleType = Optional[str]

_DEFAULT_PAGES = 1
_DEFAULT_DATASET_FLAG = "undefined"
_DEFAULT_PHRASE = "undefined"
_DEFAULT_BACKEND = "istock_dataset"


class MediaType:
    PHOTOS = "photography"
    ILLUSTRATIONS = "illustration"
    VECTORS = "illustration&assetfiletype=eps"
    UNDEFINED = "undefined"

    OPTIONAL = {PHOTOS, ILLUSTRATIONS, VECTORS, UNDEFINED}
    DEFAULT = PHOTOS


class Orientations:
    SQUARE = "square"
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"
    PANORAMIC_VERTICAL = "panoramicvertical"
    PANORAMIC_HORIZONTAL = "panoramichorizontal"
    UNDEFINED = "undefined"

    OPTIONAL = {SQUARE, VERTICAL, HORIZONTAL, PANORAMIC_VERTICAL, PANORAMIC_HORIZONTAL, UNDEFINED}
    DEFAULT = SQUARE


class NumberOfPeople:
    NO_PEOPLE = "none"
    ONE_PERSON = "one"
    TWO_PEOPLE = "two"
    GROUP_OF_PEOPLE = "group"
    UNDEFINED = "undefined"

    OPTIONAL = {NO_PEOPLE, ONE_PERSON, TWO_PEOPLE, GROUP_OF_PEOPLE, UNDEFINED}
    DEFAULT = NO_PEOPLE


class _Memory:
    def __init__(self, flag: str):
        self.istock_database = flag
        self._path_memory = os.path.join(self.istock_database, "_memory.yaml")
        os.makedirs(os.path.dirname(self._path_memory), exist_ok=True)

        self.memory = self._load_memory()

    def dump_memory(self, container=None):
        container = set() if container is None else container
        self.memory = self.memory | container
        with open(self._path_memory, "w", encoding="utf8") as file:
            yaml.dump(self.memory, file, Dumper=yaml.Dumper)

    def _load_memory(self) -> Optional[set]:
        memory = set()
        for fn in os.listdir(self.istock_database):
            if fn.endswith(".jpg"):
                memory.add(fn.replace(".jpg", ""))

        return memory


class IstockPhotoDownloader:
    API = "https://www.istockphoto.com/search/2/image"
    MAX_PAGES = 20

    def __init__(
        self,
        phrase: str,
        mediatype: _MediaType = MediaType.DEFAULT,
        number_of_people: _NumberOfPeopleType = NumberOfPeople.DEFAULT,
        orientations: _OrientationsType = Orientations.DEFAULT,
        pages: int = _DEFAULT_PAGES,
        flag: bool = True,
        backend: str = _DEFAULT_BACKEND,
    ):
        """
        istock dataset scraping

        :param phrase: Required. Keywords to more_like_this
        :param mediatype: Optional. Default "photography". Choose from `MediaType()`.
        :param number_of_people: Optional. Default "none". Choose from `NumberOfPeople()`.
        :param orientations: Optional. Default "square". Choose from `Orientations()`.
        :param pages: Optional. Default 1. Value interval `pages∈[1, 20]`
        :param flag: Optional. Default True. File storage path.
            IF True --(*.jpg)--> `./istock_dataset/phrase/`
            ELSE --(*.jpg)--> `./istock_dataset/undefined/`
        :param backend: Optional. Default `./istock_dataset/`. Image database root directory.
        """
        self.pages = pages
        if not isinstance(pages, int) or not (1 <= pages <= self.MAX_PAGES):
            logger.warning(
                f"InvalidParameterPages.Automatically calibrate to default values. "
                f"- pages∈[1, {self.MAX_PAGES}]"
            )
            self.pages = _DEFAULT_PAGES

        self.phrase = phrase
        if not isinstance(self.phrase, str) or not self.phrase.strip():
            logger.critical(f"Invalid phrase - phrase=(`{self.phrase}`)")
            self.phrase = ""
            self.pages = 0

        self.mediatype = MediaType.DEFAULT if mediatype not in MediaType.OPTIONAL else mediatype
        self.number_of_people = (
            Orientations.DEFAULT
            if number_of_people not in NumberOfPeople.OPTIONAL
            else number_of_people
        )
        self.orientations = (
            Orientations.DEFAULT if orientations not in Orientations.OPTIONAL else orientations
        )

        self._raw_pointer_count = 0
        self._handled_pointer_count = 0

        self._pending_image_count = 0
        self._downloaded_image_count = 0

        _bad_code = {"\\", "/", ":", "*", "?", '"', "<", ">", "|", " ", "."}
        _inner_backend = _DEFAULT_DATASET_FLAG if not flag else self.phrase
        for i in _bad_code:
            _inner_backend.replace(i, "_")
        if backend == _DEFAULT_BACKEND:
            self._dir_local = os.path.join(backend, _inner_backend)
        else:
            self._dir_local = os.path.join(backend, _DEFAULT_BACKEND, _inner_backend)
        os.makedirs(self._dir_local, exist_ok=True)

        self.workers = Queue()
        self.delay_queue = Queue()

        self.session = self._make_session()

        self.cache = _Memory(self._dir_local)
        self.memory = self.cache.memory

    def __del__(self):
        self._offload()

    @staticmethod
    def _parse_html_and_get_image_urls(response: requests.Response):
        container_img_urls = []

        soup = BeautifulSoup(response.text, "html.parser")
        gallery = soup.find("div", attrs={"data-testid": "gallery-items-container"})

        if not gallery:
            return container_img_urls
        img_tags = gallery.find_all("img")
        for tag in img_tags:
            container_img_urls.append(tag["src"])

        return container_img_urls

    @staticmethod
    def _handle_html(url: str, session: requests.Session) -> Optional[requests.Response]:
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

    @staticmethod
    def _make_session() -> requests.Session:
        logger.debug(f"Init workers session")
        return requests.session()

    def _preload(self):
        if not self.pages:
            return

        self.phrase = self.phrase.strip()
        logger.debug(f"Container preload - phrase={self.phrase}")

        parser_ = urlparse(self.API)
        if parser_.path == "/search/2/image" and "colorsimilarityassetid" in parser_.query:
            params = f"{self.API}&phrase={self.phrase}"
        else:
            params = f"{self.API}?phrase={self.phrase}"

        # The others query
        if self.mediatype != MediaType.UNDEFINED:
            params += f"&mediatype={self.mediatype}"
        if self.number_of_people != NumberOfPeople.UNDEFINED:
            params += f"&numberofpeople={self.number_of_people}"
        if self.orientations != Orientations.UNDEFINED:
            params += f"&orientations={self.orientations}"

        for i in range(1, self.pages + 1):
            self.workers.put(f"{params}&page={i}")
            self._raw_pointer_count += 1

    def _offload(self):
        while not self.delay_queue.empty():
            self.memory.add(self.delay_queue.get())
        self.cache.dump_memory(self.memory)

    def _adaptor(self):
        while not self.workers.empty():
            url = self.workers.get()
            if not url or not isinstance(url, str):
                logger.warning(f"Drop url - context={url}")
            elif url.startswith("https://media.istockphoto.com/"):
                self.download_image(url)
            elif url.startswith(self.API):
                self.get_image_urls(url)
            elif self._downloaded_image_count % 60 == 0:
                self._offload()

    def download_image(self, url: str) -> Optional[bool]:
        """Download thumbnail"""
        self._downloaded_image_count += 1

        istock_id = f"{urlparse(url).path.split('id')[-1]}"
        fp = os.path.join(self._dir_local, f"{istock_id}.jpg")

        # Avoid downloading duplicate images
        if istock_id in self.memory:
            return

        # Download image
        try:
            resp = self.session.get(url)
        except requests.ConnectionError as err:
            logger.error(f"ConnectionError[ImageDownloader] - url={url} err={err}")
        else:
            with open(fp, "wb") as file:
                file.write(resp.content)
            self.delay_queue.put(istock_id)
            logger.debug(
                f"Download image -"
                f" progress=[{self._downloaded_image_count}/{self._pending_image_count}]"
                f" istock_id={istock_id}"
            )
            gevent.sleep(random.uniform(0.02, 0.05))
            return True

    def get_image_urls(self, url: str) -> Optional[bool]:
        """Get download links for all images in the page"""
        response = self._handle_html(url, self.session)
        if not response:
            return

        urls = self._parse_html_and_get_image_urls(response)
        for url_ in urls:
            self.workers.put(url_)
            self._pending_image_count += 1

        self._handled_pointer_count += 1
        logger.debug(
            f"Get image url -"
            f" progress=[{self._handled_pointer_count}/{self._raw_pointer_count}]"
            f" src={url}"
        )
        gevent.sleep(random.uniform(0.02, 0.3))
        return True

    def mining(self, concurrent_power: int = None):
        # Parameter check
        self._preload()

        # Reset concurrent power of collector
        concurrent_power = (
            16
            if not isinstance(concurrent_power, int) or not 1 <= concurrent_power <= 16
            else concurrent_power
        )
        concurrent_power = self.pages if concurrent_power >= self.pages else concurrent_power

        # Setup collector
        logger.debug(f"Setup [iStock] - power={concurrent_power} pages={self.pages}")
        task_list = []
        for _ in range(concurrent_power):
            task = gevent.spawn(self._adaptor)
            task_list.append(task)
        gevent.joinall(task_list)
        logger.success(f"Task complete - offload={os.path.abspath(self._dir_local)}")

    @staticmethod
    def _parse_file_count(response: requests.Response) -> Optional[str]:
        soup = BeautifulSoup(response.text, "html.parser")
        file_count = soup.find("span", class_="DesktopMediaFilter-module__fileCount___M2uwu")
        if not file_count:
            return
        return file_count.text

    def more_like_this(self, istock_id: Union[str, int], similar: str = "content"):
        """
        Similar content

        :param istock_id:
        :param similar: content | color
        :return:
        """
        similar_match = {
            "content": f"https://www.istockphoto.com/search/more-like-this/{istock_id}",
            "color": f"https://www.istockphoto.com/search/2/image?colorsimilarityassetid={istock_id}",
        }
        self.API = similar_match[similar]

        response = self._handle_html(self.API, self.session)
        if not response:
            return logger.error(
                f"Could not find source image in istock by the istock_id({istock_id})"
            )
        logger.success(f"Search - file_count={self._parse_file_count(response)}")

        return self
