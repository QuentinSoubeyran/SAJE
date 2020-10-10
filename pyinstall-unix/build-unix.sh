#!/usr/bin/env bash
HERE=$(pwd)
cd ..
VERSION=$(python3 -c "from src import version; print(version.__version__)")
cd "$HERE"
rm -rf build/
rm -rf dist/
pyinstaller --clean --name "saje-linux-$VERSION" --onefile ../main.py