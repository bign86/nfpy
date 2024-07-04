from setuptools import setup, find_packages
from Cython.Build import cythonize

setup(
    name='nfpy',
    version='0.49',
    url='',
    license='',
    author='bign86',
    author_email='',
    description='',

    install_requires=[
        'beautifulsoup4 == 4.11.1',
        'html5lib >= 1.1',
        'ibapi >= 9.81.1',
        'Jinja2 == 3.1.2',
        'matplotlib >= 3.5.2',
        'pandas >= 1.4.2',
        'requests >= 2.27.1',
        'scipy >= 1.8.0',
        'tabulate >= 0.8.9',
        'urllib3 >= 1.26.9',
    ],
    packages=find_packages(where='nfpy'),
    package_dir={"": "nfpy"},
    package_data={"": ["*.p", "*.json", "*.ini"]},

    ext_modules=cythonize(['ctools.pyx'])
)
