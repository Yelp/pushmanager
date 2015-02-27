#!/usr/bin/env python

from pushmanager.core.settings import Settings
import copy
import sys


sys.path.append(".")
sys.path.append("..")


MockedSettings = copy.deepcopy(Settings)
