import os
import sys

from setuptools import setup, find_packages

setup(

    # Vitals
    name='pergola_projects',
    license='BSD',
    url='https://github.com/kbeckmann/pergola_projects',
    author='Konrad Beckmann',
    author_email='konrad.beckmann@gmail.com',
    description='Pergola projects',

    # Imports / exports / requirements.
    platforms='any',
    packages=find_packages(),
    include_package_data=True,
    python_requires="~=3.8",
    install_requires=['nmigen'],
    setup_requires=['setuptools'],

)
