#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from setuptools import setup
#from distutils.core import setup

version = '0.1'

path = os.path.dirname(__file__)
if not path: path = '.'
readme = open(os.path.join(path, 'README.rst'), 'r').read()

setup(name='johnny-cache',
      version=version,
      description=readme.split('\n')[0],
      long_description=readme,
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python',
          'Operating System :: OS Independent',
          'Framework :: Django',
          'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
          'Topic :: Software Development :: Libraries',],
      keywords='django johnny cache',
      author='Jason Moiron',
      author_email='jmoiron@jmoiron.net',
      url='http://dev.jmoiron.net/hg/johnny-cache/',
      license='MIT',
      packages=['johnny'],
      scripts=[],
      # setuptools specific
      zip_safe=False,
      install_requires=['django',],
)


