from os import path as os_path
from setuptools import setup, find_packages

import istockphoto

this_directory = os_path.abspath(os_path.dirname(__file__))

# python setup.py sdist bdist_wheel && python -m twine upload dist/*
setup(
    name="istockphoto",
    version=istockphoto.__version__,
    keywords=["istockphoto", "downloader", "spider", "istock"],
    packages=find_packages(include=["istockphoto", "LICENSE", "istockphoto.*"]),
    url="https://github.com/QIN2DIM/istock_downloader",
    license="GNU General Public License v3.0",
    author="QIN2DIM",
    author_email="qinse.top@foxmail.com",
    description="Gracefully download dataset from istockphoto",
    long_description=open(os_path.join(this_directory, "README.md"), encoding="utf8").read(),
    long_description_content_type="text/markdown",
    install_requires=[
        "gevent~=21.12.0",
        "requests~=2.27.1",
        "pyyaml~=6.0",
        "bs4~=0.0.1",
        "beautifulsoup4~=4.11.1",
        "loguru~=0.6.0",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
    ],
)
