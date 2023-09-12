# -*- coding: utf-8 -*-
# Time       : 2023/9/12 11:12
# Author     : QIN2DIM
# GitHub     : https://github.com/QIN2DIM
# Description:
import asyncio

from istockphoto import Istock

if __name__ == "__main__":
    istock = Istock.from_phrase("dog")
    asyncio.run(istock.mining())
