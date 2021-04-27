import re

from setuptools import setup, find_packages

classifiers = [
    "Development Status :: 3 - Alpha",
    "Operating System :: POSIX",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.7",
    "License :: OSI Approved :: MIT",
    "Intended Audience :: Science/Research",
]

keywords = [
    "dataflow", "workflow", "asyncio"
]


def get_version():
    with open("flowsaber/__init__.py") as f:
        for line in f.readlines():
            m = re.match("__version__ = '([^']+)'", line)
            if m:
                return m.group(1)
        raise IOError("Version information can not found.")


def get_long_description():
    return "A dataflow based workflow framework."


def get_install_requires():
    requirements = []
    with open('requirements.txt') as f:
        for line in f:
            requirements.append(line.strip())
    return requirements


setup(
    name='flowsaber',
    author='bakezq',
    author_email='zhongquan789@gmail.com',
    version=get_version(),
    license='GPLv3',
    description=get_long_description(),
    long_description=get_long_description(),
    keywords=keywords,
    url='https://github.com/zhqu1148980644/flowsaber',
    packages=find_packages(),
    # scripts=[],
    include_package_data=True,
    zip_safe=False,
    classifiers=classifiers,
    install_requires=[
        'makefun',
        'cloudpickle',
        'dask',
        'distributed',
        'psutil',
        'aiohttp',
        'pydantic',
        'fire'
    ],
    extras_require={
        'test': [
            'pytest',
            'pytest-cov',
            'httpimport',
            'autodocsumm',
            'pysam',
            'matplotlib'
        ],
        'server': [
            "graphql-core",
            'ariadne',
            'uvicorn',
            'starlette',
            'motor'
        ]
    },
    python_requires='>=3.7, <4',
)
