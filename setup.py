# new version to pypi => python setup.py sdist upload
from setuptools import setup

setup(
    name='mintapi',
    description='a screen-scraping API for Mint.com',
    version='1.2',
    packages=['mintapi'],
    scripts=['bin/mintapi'],
    license='The MIT License',
    author='Michael Rooney',
    author_email='mrooney.mintapi@rowk.com',
    url='https://github.com/mrooney/mintapi',
    install_requires=['requests'],
)
