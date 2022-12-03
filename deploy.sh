#!/usr/bin/env bash
set -ex
rm -rf dist && python3 setup.py sdist
python3 -m twine upload dist/*
