
from setuptools import setup, find_packages

setup(name="ChatCloud",
      packages=find_packages(),
      install_requires=[
        "tornado",
        "redis", 
      ],
)
