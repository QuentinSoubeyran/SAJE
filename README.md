Search in Arbitrary JSON Engine
===============================
**DISCLAIMER**: this project is in alpha -- feedback is welcome !

SAJE is a dynamic catalog, built with JSON.

What this means is that SAJE loads JSON configuration files that specify search fields, GUI elements and the database to search in. It saves you from coding your own UI and searching system. This is most useful for catalogs.

See the [wiki](https://github.com/QuentinSoubeyran/SAJE/wiki) for more details.

> **NOTE** a version 2 is underway, that should have a better file format and
> code

# Running SAJE
## Using the freezed builds
Frozen executables are available under [releases](https://github.com/QuentinSoubeyran/SAJE/releases) on github

*NOTE*: the frozen executables are created with PyInstaller. Some antivirus do not like that and flag them as a threat. If you don't trust the executables because of this, run the code from source.

## Running from sources
You will need **python 3.9** to run SAJE from sources. Then, follow the steps below.

+ **Download** a copy of the sources. Either download a zip file from github, or use git:
```
git clone https://github.com/QuentinSoubeyran/SAJE.git
```

+ **Install the dependencies**
Navigate to the unzipped folder / to the cloned directory, and use `pip` to install the dependencies in a command-line:
```
pip install pillow
pip install -r requirements.txt
```
> **NOTE**
> 
> There is a bug in `tk-html-widgets` that is only fixed
> by installing Pillow before tk-html-widgets, as shown
> above

> **NOTE**: Windows
>
> On the windows plateform, `pip` might not be in your PATH
> and the command won't be recognize. If so, use `python -m pip` instead

+ **Run** the file `main.py` with python 3.9

# Building frozen executables
Follow all the steps above to download the sources and install the dependenices. Remember you need python **3.9**.
Then, install PyInstaller:
```
pip install pyinstaller
```

Then, navigate to the directory for your plateform, `pyinstall-unix` on Linux/Max or `pyinstall-win` on windows. The the file `build-unix.sh` or `build-win.ps1` **from that folder**. This is important, the scripts are not smart at all.

# Notes
> **NOTE**:
>
> On unix system (linux and MacOS), your system is likely to use python 2 as the default version and keep python 3 separate. In which case, you should replace the command `pip` with `pip3` and `python` with `python3`. If you are unsure, try:
> ```bash
> $ python --version 
> ```
> If the printed version is "Python 2.x.x", try with `python3` and `pip3`

# Contributing
If you need new functionalities, have found a bug or would like to help improve the search engine, feel free to open an *issue* or to open a *pull request*.