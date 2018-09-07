SECRET_KEY = 'roverdotcom'

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'tests',
    'tests.test_app_1',
    'tests.test_app_2',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}
