from importlib.metadata import entry_points
from setuptools import setup, find_packages

setup(
    name='propergitblame',
    version='0.0.0',
    packages=find_packages(),
    install_requires=[
        'click',
        'matplotlib',
        'numpy',
        'numba'
    ],
    entry_points='''
    [console_scripts]
    propergitblame=propergitblame:propergitblame
    '''
)