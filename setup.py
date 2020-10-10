import setuptools

with open("README.md", "r") as f:
    readme = f.read()

setuptools.setup(
    # Package
    name="SAJE",
    version="2.0a",
    packages=setuptools.find_packages("src"),
    package_dir={"": "src"},
    python_requires="~=3.9",
    install_requires=[
        "pheres"
    ],
    # Metadata
    author="Quentin Soubeyran",
    license="MIT",
    author_email="45202794+QuentinSoubeyran@users.noreply.github.com",
    description="Search in Arbitrary JSON Engine - dynamic catalog program",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/QuentinSoubeyran/SAJE",
    project_urls={
        "Documentation": r"https://github.com/QuentinSoubeyran/SAJE/wiki",
        "Source": r"https://github.com/QuentinSoubeyran/SAJE",
        "Tracker": r"https://github.com/QuentinSoubeyran/SAJE/issues"
    },
    keywords="json",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.9",
    ],
)