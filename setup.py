#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

import pushmanager

setup(
    name='pushmanager',
    version=pushmanager.__version__,
    provides=['pushmanager'],
    author='Yelp',
    author_email='yelplabs@yelp.com',
    url='https://github.com/Yelp/pushmanager',
    description='Deployment managing system',
    classifiers=[
        "Programming Language :: Python",
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        "Operating System :: OS Independent",
        "License :: OSI Approved :: Apache Software License",
        "Development Status :: 4 - Beta",
        "Topic :: Software Development :: Build Tools",
    ],
    license='Copyright Yelp 2013',
    packages=find_packages(exclude=["tests"]),
    include_package_data=True,
    scripts=['bin/pushmanager'],
    setup_requires=['setuptools'],
    install_requires=[
        'lxml == 2.2.4',
        'mysql-python == 1.2.4',
        'python-daemon == 1.5.2',
        'python-ldap == 2.4.13',
        'tornado == 2.4.1',
        'xmpppy == 0.5.0rc1',
    ],
    long_description="""Pushmanager is a tornado web application we use to manage deployments at Yelp. It helps pushmasters to conduct the deployment by bringing together push requests from engineers and information gathered from reviews, test builds and issue tracking system.""",
)
