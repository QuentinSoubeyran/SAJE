$HERE=Get-Location | select -ExpandProperty Path
cd ..
Write-Host "VERSION: " -NoNewLine
python -c "from src import version; print(version.__version__)" | Tee-Object -Variable VERSION
cd "$HERE"
Remove-Item -path build/ -recurse
Remove-Item -path dist/ -recurse
pyinstaller --clean --name "saje-$VERSION" --onefile ../main.py