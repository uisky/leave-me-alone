ENVIRONMENT = 'production'
DEBUG = False

SQLALCHEMY_DATABASE_URI = 'postgresql://lma:e78z86@localhost:5432/lma'
SQLALCHEMY_ECHO = False
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ENGINE_OPTIONS = {'connect_args': {'options': '-c timezone=utc-3'}}

SECRET_KEY = 'IJHk|kl.)&*gphdbaSD7yhj23r4hb^&Gdflaqshb6&'
SECRET_KEY_PASSWORD = 'nYnLmHvghNl&bhTvVk)i8NM:7^%ASbB+g9asd'

WTF_CSRF_ENABLED = False
WTF_CSRF_TIME_LIMIT = 60 * 60 * 24

MAIL_DEFAULT_SENDER = 'no-reply@leave-me-alone.ru'

JSON_AS_ASCII = False

ASSET_STORAGE_ROOT = '/srv/leave-me-alone.ru/var/assets'
ASSET_URL_ROOT = '/assets'
