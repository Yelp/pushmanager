# -*- coding: utf-8 -*-
import logging
import sys
import yaml

from core.util import dict_copy_keys

configuration_file = "config.yaml"
example_configuration_file = "config.yaml.example"

Settings = {}

try:
    with open(configuration_file) as settings_yaml:
        Settings = yaml.safe_load(settings_yaml)
except:
    logging.warning("Can not load configuration from '%s'." % configuration_file)
    logging.warning("Will try loading defaults from '%s'." % example_configuration_file)
    try:
        with open(example_configuration_file) as settings_yaml:
            Settings = yaml.safe_load(settings_yaml)
    except:
        logging.error("Can not load configuration from '%s'." % example_configuration_file)
        sys.exit(1)


# JS files in static/js need to know some of the configuration options
# too, but we do not have to export everything, just what's
# needed. This is what's needed. We're only setting up/defining keys
# here and will copy values from Settings.
JSSettings = {
    'main_app': {
        'servername': None,
        'port': None,
    },
    'buildbot': {
        'servername': None,
    },
    'reviewboard': {
        'servername': None,
    },
    'trac': {
        'servername': None,
    },
    'git': {
        'main_repository': None,
    },
    'check_sites_bookmarklet': None,
}

dict_copy_keys(to_dict=JSSettings, from_dict=Settings)

__all__ = ['Settings', 'JSSettings']
