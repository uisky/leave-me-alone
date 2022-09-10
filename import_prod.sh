#!/usr/bin/env bash

# psql -U lma -c "DROP SCHEMA public; CREATE SCHEMA public;"

echo "Пароль от постргесного юзера lma на romakhin.ru"
ssh romakhin@romakhin.ru "pg_dump -U lma -O -c lma"  | psql -U lma
