from __future__ import annotations
import boto3
from .config import settings

def s3_client():
    return boto3.client("s3", region_name=settings.aws_region)

def dynamodb_client():
    return boto3.client("dynamodb", region_name=settings.aws_region)

def dynamodb_resource():
    return boto3.resource("dynamodb", region_name=settings.aws_region)

def bedrock_runtime():
    return boto3.client("bedrock-runtime", region_name=settings.aws_region)

def transcribe_client():
    return boto3.client("transcribe", region_name=settings.aws_region)

def mediaconvert_client():
    return boto3.client("mediaconvert", region_name=settings.aws_region)
