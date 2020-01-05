# Qiita notification job with AWS Lambda and Dynamo DB Stream. 
this repository includes two code, which apply to Lambda one by one.

## /qiita_iine_collect/check_new_iine_dev.py
- collect all articles iine by Qiita API v2
- update logs in Dynamo DB to stream differences, which is target of notification

## /qiita_notification/send_new_iine_dev.py
- get stream data of Dynamo DB
- notify via LINE Notify
