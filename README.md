# Qiita notification job with AWS Lambda and Dynamo DB Stream

This repository includes two code, which apply to `AWS Lambda` one by one.

Infrastructure in `AWS` is constructed by `AWS CDK python` and CD (Continuous Deployment) with GitHub Actions.

## Collect Iine from Qiita

at `/qiita_iine_collect/check_new_iine_dev.py`

- collect all articles iine by Qiita API v2 for target user
- update logs in Dynamo DB to stream differences, which is target of notification

## Notificate New Iine via Line Notify

at `/qiita_notification/send_new_iine_dev.py`

- get stream data of Dynamo DB
- notify via LINE Notify
