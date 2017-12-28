#!/bin/bash

Xvfb :0 -ac -screen 0 1024x768x24 &
export DISPLAY=:0.0

/home/appuser/.local/bin/mintapi $*
