from __future__ import annotations
import boto3
from .config import settings
from botocore.config import Config

_s3 = None

def s3_client():
    global _s3
    if _s3 is None:
        _s3 = boto3.client(
            "s3",
            region_name=settings.aws_region,           
            config=Config(
                signature_version="s3v4",              
                s3={"addressing_style": "virtual"},  
            ),
        )
    return _s3

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
