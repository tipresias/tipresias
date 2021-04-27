"""Setup the sqlalchemy-fauna package."""

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="sqlalchemy-fauna",
    version="0.1.0",
    author="Craig Franklin",
    author_email="craigjfranklin@gmail.com",
    description="Fauna dialect for SQLAlchemy",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="",
    packages=setuptools.find_packages(),
    entry_points={
        "sqlalchemy.dialects": [
            "fauna = sqlalchemy_fauna.dialect:FaunaDialect",
        ]
    },
    install_requires=[
        "faunadb==4.1.0",
        "sqlparse==0.4.1",
        "mypy>=0.70,<1.0",
        "sqlalchemy>=1.4.0,<1.5.0",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)
