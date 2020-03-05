Search in Arbitrary JSON Engine
===============================
**DISCLAIMER**: this project is in alpha § feedback is welcome !


This project allows to make a graphical application for searching simple data, using only JSON files. The JSON file provides the data to search on, and how to build the UI. See the wiki and examples files for details !

# Installing a local copy
To run the application, you can either download the source code and execute it using python, or use the provided builds (not yet available, this is WIP).

## Using python
Download the .zip from github or use `git` to clone the project on your local machine.

You will need **python 3** to run this project. It is recommended to use **python 3.7** as this is the python version this project is developped on.
Then, install dependencies using `pip` and the `requirements.txt` file provided:

```bash
$ pip install -r requirements.txt
```

On windows, pip might not be in your path, in which case you might have to use
```batch
$ python -m pip install requirements.txt
```

To run the search engine, simply run `main.py`

```bash
$ python main.py
```

> **NOTE**:
>
> On unix system (linux and MacOS), your system is likely to use python 2 as the default version and to keep python 3 separate. In which case, you should replace the command `pip` with `pip3` and `python` with `python 3`. If you are unsure, try:
> ```bash
> $ python --version 
> ```
> If the printed version is "Python 2.x.x", try with `python3` and `pip3`

## Using a build
Builds are not yet availables, you will have to run with your own python for now.

# Contributing
If you need new functionalities, have found a bug or would like to help improve the search engine, feel free to open an *issue* or to open a *pull request*.