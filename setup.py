# Podflow/setup.py
# coding: utf-8

from setuptools import setup, find_packages

setup(
    name="podflow",
    version="20250318",
    author="gruel_zxz",
    author_email="zhuxizhouzxz@gmail.com",
    description="A podcast server that includes YouTube and BiliBili",
    long_description=open('README.md', 'r', encoding='utf-8').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/gruel-zxz/podflow",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'Podflow=Podflow.main:main',
            'podflow=Podflow.main:main',
            'PodFlow=Podflow.main:main',
            'PODFLOW=Podflow.main:main',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "astral>=3.2", 
        "bottle>=0.13.2",
        "yt-dlp>=2025.2.19",
        "chardet>=5.2.0",
        "cherrypy>=18.10.0",
        "pyqrcode>=1.2.1",
        "requests>=2.32.3",
        "pycryptodome>=3.21.0",
        "ffmpeg-python>=0.2.0",
        "BeautifulSoup4>=4.13.3",
    ],
)
