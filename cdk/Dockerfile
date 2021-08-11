ARG CDK_VERSION=1.100

FROM tokusumi/aws-cdk-python:cdk1.100-py3.7
LABEL maintainer="Tomoro Tokusumi"

WORKDIR /root

ADD ./app/requirements.txt /app/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /app/requirements.txt

CMD ["/bin/bash"]