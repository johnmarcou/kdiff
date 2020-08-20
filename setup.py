
import sys
import re
from setuptools import setup


setup(
    name="kdiff",
    license="BSD",
    author="John Marcou",
    install_requires=[
        "oyaml",
        "click",
        "colorama",
        "prettytable",
    ],
    entry_points={
        'console_scripts': ['kdiff=kdiff.cli:cli']
        }
)
