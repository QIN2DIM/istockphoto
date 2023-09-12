# -*- coding: utf-8 -*-
# Time       : 2022/9/18 22:30
# Author     : QIN2DIM
# Github     : https://github.com/QIN2DIM
# Description:
import asyncio

import pytest

from istockphoto.istock import Istock


@pytest.mark.parametrize("phrase", ["dog", "panda"])
@pytest.mark.parametrize("pages", [1, 2])
def test_pages(phrase: str, pages: int):
    istock = Istock.from_phrase(phrase)

    # pages: 60 images per page, default upto 1.
    istock.pages = min(5, pages)

    asyncio.run(istock.mining())
