#!/usr/bin/env bash

ssh fresh@romakhin.ru pg_dump -U lma -O -c lma | psql -U lma