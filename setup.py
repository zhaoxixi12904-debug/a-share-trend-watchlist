from setuptools import find_packages, setup


setup(
    name="a-share-watchlist",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages("src"),
    install_requires=[
        "pandas>=2.0.0",
        "openpyxl>=3.1.0",
    ],
    entry_points={
        "console_scripts": [
            "a-share-watchlist=a_share_watchlist.cli:main",
        ],
    },
)
