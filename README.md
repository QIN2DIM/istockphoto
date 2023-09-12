# iStockPhoto Downloader

## Introduction

Gracefully download dataset from iStockPhoto.

## Quickstart

1. **Download PyPI package**

   ```bash
   pip install -U istockphoto
   ```

2. **Examples**

   - Download images about `panda` phrase. 

   ```python
   import asyncio
   
   from istockphoto import Istock
   
   if __name__ == "__main__":
       istock = Istock.from_phrase("panda")
       asyncio.run(istock.mining())
   ```

   - Similar mode
   
   ```python
   import asyncio
   
   from istockphoto import Istock
   
   # phrase, image_id
   name2similar = [
       ("horse", "1280951754"),
       ("panda", "91781059"),
       ("cat", "1325997570")
   ]
   
   if __name__ == "__main__":
       for name, similar in name2similar:
           istock = Istock.from_phrase(name)
           istock.more_like_this(similar)
           asyncio.run(istock.mining())
   ```
   

## What's more

[Home · QIN2DIM/istockphoto Wiki (github.com)](https://github.com/QIN2DIM/istockphoto/wiki)
