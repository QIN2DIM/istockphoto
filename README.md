# iStockPhoto Downloader

## Introduction

Gracefully download dataset from iStockPhoto.

## Documentation

[Home · QIN2DIM/istockphoto Wiki (github.com)](https://github.com/QIN2DIM/istockphoto/wiki)

## Example

1. **Download PyPi package**

   ```bash
   pip install istockphoto
   ```

2. **Quickstart**

   Retrieve the lizard and use the default parameters to download the image on page 1.

   - Demo: [istock collector mining | cat](https://user-images.githubusercontent.com/62018067/182983671-4d1a3ff8-18f3-480c-9a36-26d6019ec7f5.mp4)
   
   ```python
   from istockphoto import IstockPhotoDownloader
   
   if __name__ == '__main__':
       IstockPhotoDownloader("lizard").mining()
   
   ```

   Search by image based on istockphoto.
   
   - Demo: [more like this content | rabbit](https://user-images.githubusercontent.com/62018067/182983684-78db4364-4c4a-4670-98fd-d3fb136152df.mp4)
   - Demo: [more like this content | cat](https://user-images.githubusercontent.com/62018067/182983561-b958cccb-d042-48a9-82cb-6d4630e293a6.mp4)
   - Demo: [more like this color | lizard](https://user-images.githubusercontent.com/62018067/182984598-8ca7f776-7350-493e-87b8-ccd29d157a9a.mp4)
   
   ```python
   from istockphoto import IstockPhotoDownloader
   
   if __name__ == '__main__':
       IstockPhotoDownloader("lizard").more_like_this(istock_id=1097354054).mining()
   
   ```
   
   

