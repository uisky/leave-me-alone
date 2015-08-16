#!/usr/bin/env bash

# psql -U lma -c "DROP SCHEMA public; CREATE SCHEMA public;"

echo "Сначала пароль для fresh@romakhin.ru, потом от постргесного юзера lma на romakhin.ru"
ssh fresh@romakhin.ru pg_dump -U lma -O -c lma | psql -U lma