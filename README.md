Search in Arbitrary JSON Engine
===============================

This project allows to make a graphical application to search on arbitrary data using JSON format. The JSON files containes both the data (a list of arbitrary JSON objects) and how to search on them. The graphic interface is automatically built to allow the search options to be provided values.

See the `example_data.json` for examples and the wiki on how to write the json files.

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