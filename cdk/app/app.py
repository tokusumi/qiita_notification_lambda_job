from pathlib import Path
from aws_cdk import (
    core,
    aws_dynamodb as ddb,
    aws_lambda as _lambda,
    aws_events as events,
    aws_events_targets as targets,
)
from aws_cdk.aws_lambda_event_sources import DynamoEventSource, SqsDlq

import os

BASEDIR = Path(__file__).absolute().parent


class QiitaIineNotifier(core.Stack):
    def __init__(self, scope: core.App, name: str, **kwargs) -> None:
        super().__init__(scope, name, **kwargs)
        db = self.log_db()
        self.qiita_iine_collector_lambda(db)
        self.qiita_notifier_lambda(db)

    def log_db(self):
        table = ddb.Table(
            self,
            "IineLogTable",
            partition_key=ddb.Attribute(name="ids", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PROVISIONED,
            read_capacity=2,
            write_capacity=2,
            removal_policy=core.RemovalPolicy.DESTROY,
            stream=ddb.StreamViewType.NEW_AND_OLD_IMAGES,
        )
        core.CfnOutput(self, "TableName", value=table.table_name)
        return table

    def qiita_iine_collector_lambda(self, table: ddb.Table):
        # Set lambda function
        handler = _lambda.Function(
            self,
            "QiitaIineCollectorLambdaHandler",
            runtime=_lambda.Runtime.PYTHON_3_6,
            handler="check_new_iine_dev.main",
            code=_lambda.Code.from_asset(
                str(BASEDIR.parent / "lambda" / "qiita_iine_collect")
            ),
            memory_size=128,
            timeout=core.Duration.seconds(20),
            dead_letter_queue_enabled=True,
            environment={
                "TABLE_NAME": table.table_name,
                "QIITA_TOKEN": os.environ["QIITA_TOKEN"],
                "QIITA_URL": os.environ["QIITA_URL"],
                "PER_PAGE": os.environ["PER_PAGE"],
            },
        )

        # Grant permissions for DDB
        table.grant_write_data(handler)

        core.CfnOutput(self, "CollectorFunctionName", value=handler.function_name)

        # Set cloudwatch as event trigger.
        trigger = events.Rule(
            self,
            "QiitaIineCollectorTriggerRule",
            schedule=events.Schedule.cron(minute="0/15", hour="0-16"),
        )
        trigger.add_target(targets.LambdaFunction(handler))

    def qiita_notifier_lambda(self, table: ddb.Table):
        # Set lambda function
        handler = _lambda.Function(
            self,
            "QiitaNotifierLambdaHandler",
            runtime=_lambda.Runtime.PYTHON_3_6,
            handler="send_new_iine_dev.lambda_handler",
            code=_lambda.Code.from_asset(
                str(BASEDIR.parent / "lambda" / "qiita_notification")
            ),
            memory_size=128,
            timeout=core.Duration.seconds(20),
            dead_letter_queue_enabled=True,
            environment={
                "TABLE_NAME": table.table_name,
                "QIITA_TOKEN": os.environ["QIITA_TOKEN"],
                "LINE_TOKEN": os.environ["LINE_TOKEN"],
            },
        )

        core.CfnOutput(self, "NotifierFunctionName", value=handler.function_name)

        # Set DynamoDB stream as event trigger.
        # Grant permissions for DDB
        table.grant_stream_read(handler)

        handler.add_event_source(
            DynamoEventSource(
                table=table,
                starting_position=_lambda.StartingPosition.LATEST,
                batch_size=100,
                retry_attempts=10000,
            )
        )


app = core.App()
QiitaIineNotifier(
    app,
    "QiitaIineNotifier",
    env={
        "region": os.environ["CDK_DEFAULT_REGION"],
        "account": os.environ["CDK_DEFAULT_ACCOUNT"],
    },
)
app.synth()
