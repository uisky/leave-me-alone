ENVIRONMENT = 'development'
DEBUG = True

SQLALCHEMY_DATABASE_URI = 'postgresql://lma:e78z86@localhost:5432/lma'
SQLALCHEMY_ECHO = False

# False -> молчать, как рыба об лёд
# True, 'log' -> показывает запросы
# 'analyse', 'analyze' -> пишет запросы и выводит таблицу в конце запроса
FLASK_SA_LOGGER = 'analyze'

# Ключ элемента в flask.g, который будет использоваться для хранения запросов
FLASK_SA_LOGGER_KEY = '_flask_sa_data'


MAIL_SUPPRESS_SEND = True
