Remove-Item -path build/ -recurse
Remove-Item -path dist/ -recurse
pyinstaller --clean --name "saje" --onefile ../main.py