DEBUG = False

SQLALCHEMY_DATABASE_URI = 'postgresql://lma:e78z86@localhost:5432/lma'
SQLALCHEMY_ECHO = False

SECRET_KEY = 'IJHk|kl.)&*gphdbaSD7yhj23r4hb^&Gdflaqshb6&'
SECRET_KEY_PASSWORD = 'nYnLmHvghNl&bhTvVk)i8NM:7^%ASbB+g9asd'

WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = 60 * 60 * 24

MAIL_DEFAULT_SENDER = 'no-reply@leave-me-alone.ru'

JSON_AS_ASCII = False