#!/bin/bash

python manage.py migrate
python manage.py collectstatic --noinput

python manage.py runserver 0.0.0.0:8000 &

sleep 1
echo

python manage.py runtransfer &
python manage.py runsamplingdownloader &
python manage.py runleecher &
echo

wait -n

exit $?
