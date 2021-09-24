# new version to pypi (pip install twine):
# rm -rf dist && python setup.py sdist && python -m twine upload dist/*
import os
import setuptools

readme = os.path.join(os.path.dirname(__file__), 'README.md')
with open(readme, 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='mintapi',
    description='a screen-scraping API for Mint.com',
    long_description="https://github.com/mintapi/mintapi/",
    version='1.53',
    packages=['mintapi'],
    license='The MIT License',
    author='Michael Rooney',
    author_email='mrooney.mintapi@rowk.com',
    url='https://github.com/mintapi/mintapi',
    install_requires=['future', 'mock', 'requests', 'selenium-requests>=1.3.3', 'xmltodict', 'pandas>=1.0', 'selenium', 'oathtool'],
    entry_points=dict(
        console_scripts=[
            'mintapi = mintapi.api:main',
        ],
    ),
)
