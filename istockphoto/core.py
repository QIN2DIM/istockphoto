# -*- coding: utf-8 -*-
# Time       : 2022/8/5 8:45
# Author     : QIN2DIM
# Github     : https://github.com/QIN2DIM
# Description:
from gevent import monkey

monkey.patch_all()
import os.path
import typing
from urllib.parse import urlparse

import gevent
import requests
from bs4 import BeautifulSoup
from gevent.queue import Queue
from .utils import init_log, make_session, parse_html_and_get_image_urls, handle_html, load_memory

logger = init_log()

_MediaType = typing.Optional[str]
_OrientationsType = typing.Optional[str]
_NumberOfPeopleType = typing.Optional[str]

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
    DEFAULT = UNDEFINED


class NumberOfPeople:
    NO_PEOPLE = "none"
    ONE_PERSON = "one"
    TWO_PEOPLE = "two"
    GROUP_OF_PEOPLE = "group"
    UNDEFINED = "undefined"

    OPTIONAL = {NO_PEOPLE, ONE_PERSON, TWO_PEOPLE, GROUP_OF_PEOPLE, UNDEFINED}
    DEFAULT = NO_PEOPLE


class IstockPhotoDownloader:
    API = "https://www.istockphoto.com/search/2/image"
    MAX_PAGES = 20

    SIMILAR_COLOR = "color"
    SIMILAR_CONTENT = "content"

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
        self.memory = load_memory(istock_database=self._dir_local)
        self.session = make_session()

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

    def _adaptor(self):
        while not self.workers.empty():
            url = self.workers.get()
            if not url or not isinstance(url, str):
                logger.warning(f"Drop url - context={url}")
            elif url.startswith("https://media.istockphoto.com/"):
                self.download_image(url)
            elif url.startswith(self.API):
                self._get_image_urls(url)

    def _get_image_urls(self, url: str) -> typing.Optional[bool]:
        """Get download links for all images in the page"""
        response = handle_html(url, self.session)
        if not response:
            return

        urls = parse_html_and_get_image_urls(response)
        for url_ in urls:
            self.workers.put(url_)
            self._pending_image_count += 1

        self._handled_pointer_count += 1
        logger.debug(
            f"Get image url -"
            f" progress=[{self._handled_pointer_count}/{self._raw_pointer_count}]"
            f" src={url}"
        )
        return True

    def download_image(self, url: str) -> typing.Optional[bool]:
        """Download thumbnail"""
        self._downloaded_image_count += 1

        istock_id = f"{urlparse(url).path.split('/')[2]}"
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
            logger.debug(
                f"Download image -"
                f" progress=[{self._downloaded_image_count}/{self._pending_image_count}]"
                f" istock_id={istock_id}"
            )
            return True

    def more_like_this(
        self, istock_id: typing.Union[str, int], similar: typing.Literal["content", "color"] = None
    ):
        """
        Similar content

        :param istock_id:
        :param similar: "content" | "color"
        :exception KeyError
        :return:
        """

        def parse_file_count(res: requests.Response) -> typing.Optional[str]:
            soup = BeautifulSoup(res.text, "html.parser")
            file_count = soup.find("span", class_="DesktopMediaFilter-module__fileCount___M2uwu")
            if not file_count:
                return
            return file_count.text

        similar_match = {
            "content": f"https://www.istockphoto.com/search/more-like-this/{istock_id}",
            "color": f"https://www.istockphoto.com/search/2/image?colorsimilarityassetid={istock_id}",
        }
        similar = (
            self.SIMILAR_CONTENT
            if similar not in [self.SIMILAR_CONTENT, self.SIMILAR_COLOR]
            else similar
        )
        self.API = similar_match[similar]

        response = handle_html(self.API, self.session)
        if not response:
            logger.error(f"Could not find source image in istock by the istock_id({istock_id})")
            raise
        logger.success(f"Search - file_count={parse_file_count(response)}")

        return self

    def mining(self):
        # Parameter check
        self._preload()

        # Setup collector
        workers = 32
        task_list = []
        logger.debug(f"Setup [iStock] - phrase={self.phrase} power={workers} pages={self.pages}")
        for _ in range(workers):
            task = gevent.spawn(self._adaptor)
            task_list.append(task)
        gevent.joinall(task_list)
        logger.success(
            f"Task complete - phrase={self.phrase} offload={os.path.abspath(self._dir_local)}"
        )
