# baidupcsleecher
Asynchronous downloader for sharing files via Baidu Cloud Drive based on [BaiduPCS-Py](https://github.com/PeterDing/BaiduPCS-Py).

## Features

- download shared files via Baidu Cloud Drive (百度云盘)
- drive via restful API
- pre-download sampling of files to determine file type or mime type
- optional callback to notify task status changes

## API

### Create leech task

First, you must register the `shared_link` of shared files to trigger the download process:
```sh
$ curl -X POST -d "shared_link=https://pan.baidu.com/s/123abc" localhost:8000/task/
```

If the shared files protected, you should provide the `shared_password`:
```sh
$ curl -X POST -d "shared_link=https://pan.baidu.com/s/123abc&shared_password=def" localhost:8000/task/
```

Or provide a `shared_link` that includes the password:
```sh
$ curl -X POST -d "shared_link=https://pan.baidu.com/s/123abc?pwd=def" localhost:8000/task/
```

The creation API will return the task object:
```json
{
  "id": 1,
  "path": "123abc.def",
  "sample_path": "123abc.def.sample",
  "shared_id": "123abc",
  "shared_link": "https://pan.baidu.com/s/123abc",
  "shared_password": "def",
  "status": "Inited",
  "callback": null,
  "created_at": "2023-05-21T07:26:15.767096Z",
  "started_at": null,
  "finished_at": null,
  "transfer_completed_at": null,
  "file_listed_at": null,
  "sample_downloaded_at": null,
  "full_downloaded_at": null,
  "full_download_now": false,
  "failed": false,
  "message": "",
  "captcha_required": false,
  "captcha_url": "",
  "captcha": ""
}
```

When the leech task is created, the backgroud processes will start:
- save the shared files to your own cloud drive
- fetch the list of files
- pre-download samples (first 10KB) of all files
- download full files, if you set the environment `FULL_DOWNLOAD_IMMEDIATELY=1` (default: 0, disabled), or set `full_download_now`.

### Callback

If you wish to inform another service when the task's processing status changes,
you can provide a callback URL while creating the task:
```sh
$ curl -X POST -d "shared_link=https://pan.baidu.com/s/123abc&callback=http://host/notify/url" localhost:8000/task/
```
The body of callback request is the task object in json format.

### Permit to download entire files

By default, automatic downloading of full files is disabled by `FULL_DOWNLOAD_IMMEDIATELY=0`
to avoid accidentally filling up the disk.

So, you need to allow the leecher to start downloading full files manully by:
```sh
$ curl -X POST -d "full_download_now=true" localhost:8000/task/${task_id}/full_download_now/
```

## Configuration

You should customize your configuration to suit your requirements. All configurations can be set via environment variables. The following are the configured default values:
```python
# the directory store downloaded files
DATA_DIR = "/tmp"
# the directory on your Baidu Cloud Drive to save shared files
REMOTE_LEECHER_DIR = "/leecher"
# trigger leech every few seconds
RUNNER_SLEEP_SECONDS = 5
# whether to download full files, disabled by default
FULL_DOWNLOAD_IMMEDIATELY = 0
# shared link transfer policy: always, if_not_present (default)
TRANSFER_POLICY = "if_not_present"
# For PAN_BAIDU_BDUSS and PAN_BAIDU_COOKIES, please check the documentation of BaiduPCS-Py
PAN_BAIDU_BDUSS = ""
PAN_BAIDU_COOKIES = ""

## django settings
# 0: production, 1: devlopment
DJANGO_DEBUG = 1
# specify hosts seperated by commas
DJANGO_ALLOWED_HOSTS = '*'
# specify hosts separeated by commas
CORS_ALLOWED_ORIGINS = ''
# 1: accept any remote host
CORS_ALLOW_ALL_ORIGINS = 0
# the database to store tasks, see Django documentation
DB_ENGINE = 'django.db.backends.sqlite3'
DB_NAME = BASE_DIR / 'db.sqlite3'
DB_USER = 'postgres'
DB_PASSWORD = ''
DB_HOST = ''
DB_PORT = ''
```
