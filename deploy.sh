#!/usr/bin/env bash
set -ex
rm -rf dist && python setup.py sdist
python -m twine upload dist/*
