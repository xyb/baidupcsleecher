FROM python:3

ENV \
  PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PIP_NO_CACHE_DIR=1 \
  PIP_DISABLE_PIP_VERSION_CHECK=1 \
  PIP_DEFAULT_TIMEOUT=100

WORKDIR /app
COPY ./requirements.txt /app/
RUN pip install -r requirements.txt
ADD . /app
EXPOSE 8000
CMD /app/entrypoint.sh
