#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup
#from distutils.core import setup

version = '1.6a'

setup(name='johnny-cache',
      version=version,
      description="Django caching framework that automatically caches all "
                  "read queries.",
      long_description=open('README.rst').read(),
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python',
          'Operating System :: OS Independent',
          'Framework :: Django',
          'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
          'Topic :: Software Development :: Libraries',
          'Topic :: Software Development :: Libraries :: Python Modules',],
      keywords='django johnny cache',
      author='Jason Moiron',
      author_email='jmoiron@jmoiron.net',
      url='http://github.com/jmoiron/johnny-cache',
      license='MIT',
      packages=['johnny', 'johnny.backends'],
      scripts=[],
      # setuptools specific
      zip_safe=False,
)
