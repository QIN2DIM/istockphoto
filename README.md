# iStockPhoto Downloader

## Introduction

Gracefully download dataset from iStockPhoto.

## Documentation

[Home · QIN2DIM/istock_downloader Wiki (github.com)](https://github.com/QIN2DIM/istock_downloader/wiki)

## Example

1. **Download PyPi package**

   ```bash
   pip install istockphoto
   ```

2. **Quickstart**

   Retrieve the lizard and use the default parameters to download the image on page 1.

   ```python
   from istockphoto import IstockPhotoDownloader
   
   if __name__ == '__main__':
       IstockPhotoDownloader("lizard").mining()
   
   ```

   Search by image based on istockphoto.

   ```python
   from istockphoto import IstockPhotoDownloader
   
   if __name__ == '__main__':
       IstockPhotoDownloader("lizard").more_like_this(istock_id=1097354054).mining()
   
   ```

   

