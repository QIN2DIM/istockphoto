# -*- coding: utf-8 -*-
# Time       : 2023/9/12 11:12
# Author     : QIN2DIM
# GitHub     : https://github.com/QIN2DIM
# Description:
import asyncio

from istockphoto import Istock

# phrase, image_id
name2similar = [("horse", "1280951754"), ("panda", "91781059"), ("cat", "1325997570")]

if __name__ == "__main__":
    for name, similar in name2similar:
        istock = Istock.from_phrase(name)
        istock.more_like_this(similar)
        asyncio.run(istock.mining())
