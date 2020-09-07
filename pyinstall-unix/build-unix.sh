#!/usr/bin/env bash
rm -rf build/
rm -rf dist/
pyinstaller --clean --name "saje" --onefile ../main.py