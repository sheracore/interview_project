import logging

from proj.settings import *

LOGGING = {}
logging.disable(logging.CRITICAL)

DATABASES['default'] = {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': os.path.join(BASE_DIR, 'test_db.sqlite3'),
}

REST_CAPTCHA['MASTER_CAPTCHA'] = {
    'TEST': 'PASSED'
}