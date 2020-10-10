$HERE=Get-Location | select -ExpandProperty Path
rm -rf build/
rm -rf dist/
cd ..
$VERSION=python3 -c "from src import version; print(version.__version__)"
cd "$HERE"
pyinstaller --clean --name "saje-$VERSION" --onefile ../main.py