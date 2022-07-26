from setuptools import setup
from Cython.Build import cythonize

setup(
    name='nfpy',
    version='0.32',
    packages=['nfpy', 'nfpy.DB', 'nfpy.IO', 'nfpy.Var', 'nfpy.Var.EvolutionModels', 'nfpy.Math', 'nfpy.Tools',
              'nfpy.Assets', 'nfpy.Trading', 'nfpy.Trading.Indicators', 'nfpy.Trading.Strategies', 'nfpy.Financial',
              'nfpy.Financial.Portfolio', 'nfpy.Financial.Portfolio.Optimizer', 'nfpy.Financial.EquityValuation',
              'nfpy.Reporting', 'nfpy.Reporting.Reports', 'nfpy.Downloader'],
    url='',
    license='',
    author='bign86',
    author_email='',
    description='',
    ext_modules=cythonize(['ctools.pyx'])
)
