# data.biodiversity.aq Portal

- [Installation instructions](#installation-instructions)
- [Start the development server](#start-the-development-server)
- [Setting up Geoserver](#geoserver)
- [Asynchronous downloads with Celery and Redis](#asynchronous-downloads-with-celery-and-redis)
- [Using Django debug toolbar](#using-django-debug-toolbar)
- [Configuring email for development](#configuring-email-for-development)
- [App user guide](./docs/app_user_guide.md)

## Installation instructions

- create virtual environment

```
conda create -n antabif python=3.8
```

You can also opt for [virtualenv](https://virtualenv.pypa.io/en/stable/) to create a virtual environment.

- activate the environment

```
source activate antabif 
```

- install requirements:

```
pip install -r requirements.txt
```

- create database and user:

    - edit `setup_database.sql` as you see fit
    - run `psql < setup_database.sql`

- create table for grid:
    - run `psql -U antabifapp -d data_biodiversity_aq -f LOAD_GRID.sql`

- create `data_biodiversity_aq/settings_local.py` and add something like:

```
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'myproject',
        'USER': 'myprojectuser',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '',
    }
}
```

- run `DJANGO_SETTINGS_MODULE="data_biodiversity_aq.settings.development" python manage.py migrate` to create all the tables in your database
- run `DJANGO_SETTINGS_MODULE="data_biodiversity_aq.settings.development" python manage.py createsuperuser` to create a superuser
- run `DJANGO_SETTINGS_MODULE="data_biodiversity_aq.settings.development" python manage.py createcachetable` to create cache table in database

### Working with the geospatial types

Django can work with geospatial types but you will need to make sure your database
can store them. I will only document this process for Postgres, since that is
our database of choice, but know that this can work with other databases as well.

Postgres has a `PostGIS` extension that needs to be installed. The installation
of this extension depends on your operating system.

#### Mac OSX

The recommended way is to install the Postgres.app. This includes the PostGIS
extension. The [django documentation on installing
PostGIS](https://docs.djangoproject.com/en/1.10/ref/contrib/gis/install/#postgresapp)
says you will also need some other dependencies to be installed using homebrew,
but I'm not sure whether that is really needed.

#### Ubuntu (dev and prd servers)

According to [the documentation](https://docs.djangoproject.com/en/1.10/ref/contrib/gis/install/postgis/):

```
On Debian/Ubuntu, you are advised to install the following packages:
postgresql-x.x, postgresql-x.x-postgis, postgresql-server-dev-x.x, python-psycopg2
(x.x matching the PostgreSQL version you want to install)
```

#### Create the extension in the database

I updated the [setup_database](./setup_database.sql) script. It now creates the
postgis extension on the antabif database.

Also note that the `django.contrib.gis` is in our `settings.INSTALLED_APPS` and
our models are now subclasses of `from django.contrib.gis.db import models`.

Finally, when you configure a database in your settings, make sure to use
`django.contrib.gis.db.backends.postgis` as the database engine.

### Using Postgres full text search

To enable postgres full text search feature, `django.contrib.postgres` needs to be added 
into `settings.INSTALLED_APPS`.


## Start the development server

- run `DJANGO_SETTINGS_MODULE="data_biodiversity_aq.settings.development" python manage.py runserver` and browse to [localhost:8000/admin](localhost:8000/admin)


## GeoServer

### Version and requirements

- GeoServer version 2.11.1 (Platform Independent Binary)
- Extension: WPS version 1.0.0
- SLD style for heatmap

Dynamic mapping was plotted on GeoServer and retrieved via web map service (WMS) using 
javascript `static/js/dataviz.js`

### Setup

See [the geoserver setup guide](./docs/geoserver_setup.md)

## Asynchronous downloads with Celery and Redis

The dataportal supports asynchronous downloads with Celery and Redis. In order to use it,
a running Redis database and at least one Celery worker is needed. For Mac, the following
steps should be executed:

### Install Redis on Mac

1. Install Redis: `brew install redis`
1. Start the Redis instance for local development: `redis-server /usr/local/etc/redis.conf`

> You can also configure Redis to always start on login with `brew services start redis` but
I'm not doing that.

To stop Redis, run `brew services stop redis`.

### Install Redis on Linux

Sorry, you'll have to figure this out ;)

### Using django-celery-results backend

[django-celery-results](https://django-celery-results.readthedocs.io/en/latest/) can be used to store celery task results. Typo in migration commands on [documentation page](https://docs.celeryproject.org/en/latest/django/first-steps-with-django.html#django-celery-results-using-the-django-orm-cache-as-a-result-backend), 
it should be :

```
python manage.py migrate django_celery_results
```

### Start the Celery worker

In production, the Celery worker should run in a daemon. For now, you can start
the Celery worker by running in the root folder of our project.

```
DJANGO_SETTINGS_MODULE="data_biodiversity_aq.settings.development" celery -A data_biodiversity_aq worker -l info -Ofair
``` 

`-Ofair` option enables the worker to only write to processes that are available for work, disabling prefetch behavior.



### Start the Celery beat

This app contains a background task that will run every hour. That task will remove
old download files, to free up disk space. The task is configured as a celery beat
task in [`settings.base`](./data_biodiversity_aq/settings/base.py). For it to run
you also need to start a Celery beat process. In development, you can start a Celery
worker and a beat process together: `celery -A data_biodiversity_aq worker -l info -B`.
This is discouraged in production however. The production setup still needs to be
examined.


## Using Django debug toolbar

To use [Django Debug Toolbar](https://django-debug-toolbar.readthedocs.io/en/stable/), you may add the following
variables to your settings (e.g. `development.py`). Further customizations are explained in the documentation.
```
INSTALLED_APPS += ['debug_toolbar',]

MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware',]

INTERNAL_IPS = '127.0.0.1'
```

## Configuring email for development

To validate email without actually sending email during development, one option is to print the email to console.

First, add these settings into your settings file `development.py` or `settings_local.py`:

```
EMAIL_USE_TLS = False
EMAIL_HOST = 'localhost' 
EMAIL_PORT = 1025
```

Run the following command in your terminal:

```
python -m smtpd -n -c DebuggingServer localhost:1025
```

This command will start a simple SMTP server listening on port 1025 of localhost. 
This server simply prints to standard output all email headers and the email body.

## Inspect before deploying 

You can use [ngrok](https://ngrok.com) to inspect the HTTP traffics, requests etc. Read more at 
[ngrok's documentation](https://ngrok.com/docs).
