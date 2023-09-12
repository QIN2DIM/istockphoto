# -*- coding: utf-8 -*-
# Time       : 2022/8/5 8:45
# Author     : QIN2DIM
# Github     : https://github.com/QIN2DIM
# Description:
import asyncio
import logging
import os
import sys
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Set
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from httpx import AsyncClient, ConnectTimeout

logging.basicConfig(
    level=logging.INFO, stream=sys.stdout, format="%(asctime)s - %(levelname)s - %(message)s"
)

# fmt: off
UNDEFINED = "undefined"
MediaType = Literal["photography", "illustration", "illustration&assetfiletype=eps", "undefined"]
Orientations = Literal["square", "vertical", "horizontal", "panoramicvertical", "panoramichorizontal", "undefined"]
NumberOfPeople = Literal["none", "one", "two", "group", "undefined"]


# fmt: on


@dataclass(slots=True)
class Istock:
    phrase: str
    """
    Required. Keywords to more_like_this
    """

    mediatype: MediaType = "photography"
    """
    Optional. Default "photography". Choose from `MediaType()`.
    """

    number_of_people: NumberOfPeople = "none"
    """
    Optional. Default "none". Choose from `NumberOfPeople()`.
    """

    orientations: Orientations = "undefined"
    """
    Optional. Default "undefined". Choose from `Orientations()`.
    """

    pages: int = 1
    """
    Default 1. Value interval `pages∈[1, 20]`
    """

    flag: bool = True
    """
    Optional. Default True. File storage path.
    IF True --(*.jpg)--> `./istock_dataset/phrase/`
    ELSE --(*.jpg)--> `./istock_dataset/undefined/`
    """

    tmp_dir: Path = Path("tmp_dir")
    store_dir: Path = field(default=Path)
    """
    Optional. Default `./istock_dataset/`. Image database root directory.
    """

    cases_name: Set[str] = field(default_factory=set)
    work_queue: asyncio.Queue | None = None
    client: AsyncClient | None = None
    api: str = "https://www.istockphoto.com/search/2/image"

    power = 32
    sem = asyncio.Semaphore(power)

    def __post_init__(self):
        logging.debug(f"Container preload - phrase={self.phrase}")

        self.work_queue = asyncio.Queue()

        self.store_dir = self.tmp_dir.joinpath("istock_tmp", self.phrase)
        self.store_dir.mkdir(parents=True, exist_ok=True)

        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.76"
        }
        self.client = AsyncClient(headers=headers)

    @classmethod
    def from_phrase(cls, phrase: str, tmp_dir: Path | None = None, **kwargs):
        tmp_dir = tmp_dir or Path("tmp_dir")
        return cls(phrase=phrase.strip(), tmp_dir=tmp_dir, **kwargs)

    async def preload(self):
        p = urlparse(self.api)
        if p.path == "/search/2/image" and "colorsimilarityassetid" in p.query:
            params = f"&phrase={self.phrase}"
        else:
            params = f"?phrase={self.phrase}"

        # The others query
        if self.mediatype != UNDEFINED:
            params += f"&mediatype={self.mediatype}"
        if self.number_of_people != UNDEFINED:
            params += f"&numberofpeople={self.number_of_people}"
        if self.orientations != UNDEFINED:
            params += f"&orientations={self.orientations}"

        img_index_urls = [f"{self.api}{params}&page={i}" for i in range(1, self.pages + 1)]
        logging.info(f"preload - size={len(img_index_urls)}")

        self.cases_name = set(os.listdir(self.store_dir))

        return img_index_urls

    async def get_image_urls(self, url: str):
        """Get download links for all images in the page"""
        with suppress(ConnectTimeout):
            response = await self.client.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            if gallery := soup.find("div", attrs={"data-testid": "gallery-items-container"}):
                img_tags = gallery.find_all("img")
                for tag in img_tags:
                    url = tag["src"]
                    if not isinstance(url, str) or not url.startswith(
                        "https://media.istockphoto.com/"
                    ):
                        continue
                    istock_id = f"{urlparse(url).path.split('/')[2]}"
                    img_path = self.store_dir.joinpath(f"{istock_id}.jpg")
                    if img_path.name in self.cases_name:
                        continue
                    context = (url, img_path)
                    self.work_queue.put_nowait(context)

    async def download_image(self):
        """Download thumbnail"""
        async with self.sem:
            while not self.work_queue.empty():
                url, img_path = await self.work_queue.get()
                res = await self.client.get(url, timeout=30)
                img_path.write_bytes(res.content)
                self.work_queue.task_done()

    def more_like_this(self, istock_id: str | int):
        if not isinstance(istock_id, str):
            istock_id = str(istock_id)
        istock_id = istock_id.replace(".jpg", "")

        # similar https://www.istockphoto.com/search/more-like-this/889083114?assettype=image&phrase=horse
        similar_match = {
            "content": f"https://www.istockphoto.com/search/more-like-this/{istock_id}",
            "color": f"https://www.istockphoto.com/search/2/image?colorsimilarityassetid={istock_id}",
        }
        self.api = similar_match["content"]
        self.store_dir = self.tmp_dir.joinpath("istock_tmp", f"{self.phrase}_similar_{istock_id}")
        self.store_dir.mkdir(parents=True, exist_ok=True)
        return self

    async def mining(self):
        urls = await self.preload()

        startup_params = {
            "phrase": self.phrase,
            "mediatype": self.mediatype,
            "number_of_people": self.number_of_people,
            "orientations": self.orientations,
            "pages": self.pages,
            "store_dir": str(self.store_dir),
        }

        logging.info(f"{startup_params=}")

        logging.info("matching index")
        await asyncio.gather(*[self.get_image_urls(url) for url in urls])

        tasks = []
        for _ in range(self.power):
            task = asyncio.create_task(self.download_image())
            tasks.append(task)

        logging.info(f"running adaptor - tasks={self.work_queue.qsize()}")
        await self.work_queue.join()

        for t in tasks:
            t.cancel()
