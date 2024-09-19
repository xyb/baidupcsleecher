# baidupcsleecher
Asynchronous downloader for sharing files via Baidu Cloud Drive based on [BaiduPCS-Py](https://github.com/PeterDing/BaiduPCS-Py).

[![test](https://github.com/xyb/baidupcsleecher/actions/workflows/test.yml/badge.svg)](https://github.com/xyb/baidupcsleecher/actions/workflows/test.yml)
[![Test Coverage](https://api.codeclimate.com/v1/badges/4635fe04eff92eb05cf3/test_coverage)](https://codeclimate.com/github/xyb/baidupcsleecher/test_coverage)
[![Maintainability](https://api.codeclimate.com/v1/badges/4635fe04eff92eb05cf3/maintainability)](https://codeclimate.com/github/xyb/baidupcsleecher/maintainability)

## Features

- [x] download shared files via Baidu Cloud Drive (百度云盘)
- [x] drive via restful API
- [x] pre-download sampling of files to determine file type or mime type
- [x] optional callback to notify task status changes
- [ ] a simple ui that works directly with your browser

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
  "total_files": 0,
  "total_size": 0,
  "largest_file": null,
  "largest_file_size": null,
  "is_downloading": False,
  "sample_download_percent": 0.0,
  "sample_downloaded_files": 0,
  "download_percent": 0.0,
  "downloaded_size": 0,
  "current_progessing_stage": "waiting_assign",
  "done": false,
  "failed": false,
  "recoverable": false,
  "retry_times": 0,
  "message": "",
  "captcha_required": false,
  "captcha_url": "",
  "captcha": ""
}
```

When the leech task is created, the background processes will start:
- save the shared files to your own cloud drive
    - then the value of `transfer_completed_at` is no longer null
- fetch the list of files
    - `file_listed_at` will be set
- pre-download first 10KB or `SAMPLE_SIZE` bytes of all files as samples
    - `sample_downloaded_at` will be set
- download full files, if you set the environment `FULL_DOWNLOAD_IMMEDIATELY=1` (default: 0, disabled), or set `full_download_now`
    - `full_downloaded_at` and `finished_at` will be set

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

So, you need to allow the leecher to start downloading full files manually by:
```sh
$ curl -X POST -d "full_download_now=true" localhost:8000/task/${task_id}/full_download_now/
```

### List remote files

When the `file_listed_at` of task be set, you could retrieve the list of remote files by:
```sh
$ curl localhost:8000/task/${task_id}/files/
```

The response will be like:
```json
[
  {
    "path": "dir1",
    "is_dir": true,
    "is_file": false,
    "size": 0,
    "md5": null
  },
  {
    "path": "dir1/my.doc",
    "is_dir": false,
    "is_file": true,
    "size": 9518361,
    "md5": "ad5bea8001e9db88f8cd8145aaf8ccef"
  }
]
```

### List local files

You can call the `local_files` to list files that were downloaded:
```sh
curl localhost:8000/task/${task_id}/local_files/
```

It will return the name and size of files:
```json
[
  {
    "file": "dir1/my.doc",
    "size": 9518361
  }
]
```

### Captcha

Sometimes the Baidu Cloud Disk requires a CAPTCHA to process the request, then the task will show as `captcha_required=True`.
In this case, you should view the `captcha` image via API:
```sh
$ curl localhost:8000/task/${task_id}/captcha/ > captcha.png
$ open captcha.png
```
Then set `captcha_code` to continuous the download process:
```sh
$ curl -X POST -d "code=${code}" http://localhost:8031/task/${task_id}/captcha_code/
```

### Error and restart

When the download process completes successfully, `finished_at` will be set and `failed` will be `False`.
However, if there are any other unexpected errors, `failed` will be `True` and the error will be logged in `message`.

When you think the error has been fixed or you want to retry the download process, you should call the restart API:
```sh
$ curl -X POST localhost:8000/task/${task_id}/restart/
```
It will return:
```json
{"status": "Inited"}
```
Which means that the entire download process will start all over.

Or you can call:
```sh
$ curl -X POST localhost:8000/task/${task_id}/restart_downloading/
```
This simply restarts the download process for samples and full files, but skips the steps of saving and retrieving the file list.

### purge files of deleted leecher tasks

After a long run, there will be a large number of files of deleted leecher tasks. You may want to delete files that you no longer need, you can call the purge api to delete them:
```sh
$ curl -X POST localhost:8000/task/purge/
```
By default, deleted files are moved to the trash folder: `baidupcsleecher_trash`, you have to delete them manually. If you want to delete the file completely, set the parameter `move_to_trash=false`:
```sh
$ curl -X POST -d "move_to_trash=false" localhost:8000/task/purge/
```

## simple ui
You can also directly use the browser to access the simple web interface that comes with the service, submit download tasks, and view the task list.

The url should be like: http://localhost:8000/ui/

## Configuration

You should customize your configuration to suit your requirements. All configurations can be set via environment variables. The following are the configured default values:
```python
# the directory store downloaded files
DATA_DIR = "/tmp"
# the directory on your Baidu Cloud Drive to save shared files
REMOTE_LEECHER_DIR = "/leecher"
# trigger leech every few seconds
RUNNER_SLEEP_SECONDS = 5
# download the first block of file as sample
SAMPLE_SIZE = 10240
# whether to download full files immediately, or must trigger `full_download_now` manually. disabled by default
FULL_DOWNLOAD_IMMEDIATELY = 0
# if the download process is interrupted, it will be retried until the limit is reached
RETRY_TIMES_LIMIT = 5
# shared link transfer policy: always, if_not_present (default)
TRANSFER_POLICY = "if_not_present"
# For PAN_BAIDU_BDUSS and PAN_BAIDU_COOKIES, please check the documentation of BaiduPCS-Py
PAN_BAIDU_BDUSS = ""
PAN_BAIDU_COOKIES = ""
# do not download file if path matches these regex
IGNORE_PATH_RE = ".*__MACOSX.*|.*spam.*"

## django settings
# 0: production, 1: development
DJANGO_DEBUG = 1
# specify hosts separated by commas
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
# prefix of url to access static files
DJANGO_STATIC_URL = 'static/'
```
