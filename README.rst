Pushmanager
===========

Pushmanager is a tornado web application we use to manage deployments
at Yelp. It helps pushmasters to conduct the deployment by bringing
together push requests from engineers and information gathered from
reviews, test builds and issue tracking system.


Quick Start
-----------

- ``python setup.py install``
- Create a config.yaml somewhere, e.g. as /etc/pushmanager/config.yaml. Use config.yaml.example as template. You need to change at least these settings:

    - main_app.servername
    - db_uri (use a local sqlite file, e.g. sqlite:////var/lib/pushmanager/sqlite.db)
    - username (effective user of service, either your own username or something like www-data)
    - log_path (this path must exist)
    - ssl_certfile and ssl_keyfile (see below)

- You need a SSL certificate. If you don't have one lying around, you can create it:

    ``openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 3650 -nodes``

- You also need to configure either SAML or LDAP for user authentication (see the example file).

- Point to your configuration file: ``export SERVICE_ENV_CONFIG_PATH=/etc/pushmanager/config.yaml``

- Now start Pushmanager: ``pushmanager.sh start``. You should be able to point your webbrowser to
  ``https://main_app.servername:main_app.port`` and see a login screen.

TODO:
   README update
   Changelog
