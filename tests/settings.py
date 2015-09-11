DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.spatialite',
        'NAME': ':memory:',
        'TEST_NAME': ':memory:',
    },
}

SECRET_KEY = 'fake-key'

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    
    'mutant',
    'mutant.contrib.boolean',
    'mutant.contrib.file',
    'mutant.contrib.geo',
    'mutant.contrib.numeric',
    'mutant.contrib.related',
    'mutant.contrib.temporal',
    'mutant.contrib.text',
    'mutant.contrib.web',
    
    'south',
    
    'userlayers',
    
    'tests',
]

ROOT_URLCONF = 'userlayers.urls'
