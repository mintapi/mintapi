# new version to pypi => python setup.py sdist upload
import os
from setuptools import setup

try:
    from pypandoc import convert
    read_md = lambda f: convert(f, 'rst')
except ImportError:
    print("warning: pypandoc module not found, could not convert Markdown to RST")
    read_md = lambda f: open(f, 'r').read()

setup(
    name='mintapi',
    description='a screen-scraping API for Mint.com',
    long_description=read_md(os.path.join(os.path.dirname(__file__), 'README.md')),
    version='1.3.1',
    packages=['mintapi'],
    scripts=['bin/mintapi'],
    license='The MIT License',
    author='Michael Rooney',
    author_email='mrooney.mintapi@rowk.com',
    url='https://github.com/mrooney/mintapi',
    install_requires=['requests'],
)
