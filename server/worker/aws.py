import os

import boto3


def make_boto3_client(service: str):
    region = os.getenv("AWS_REGION")
    endpoint_url = os.getenv("AWS_ENDPOINT_URL")
    if region and endpoint_url:
        return boto3.client(service, region_name=region, endpoint_url=endpoint_url)
    if region:
        return boto3.client(service, region_name=region)
    if endpoint_url:
        return boto3.client(service, endpoint_url=endpoint_url)
    return boto3.client(service)
