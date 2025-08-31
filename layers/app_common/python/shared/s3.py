from __future__ import annotations
import mimetypes
from typing import Optional
from .aws import s3_client

def put_object(bucket: str, key: str, data: bytes, content_type: Optional[str] = None):
    ct = content_type or (mimetypes.guess_type(key)[0] or "application/octet-stream")
    s3_client().put_object(Bucket=bucket, Key=key, Body=data, ContentType=ct)

def presign_get(bucket: str, key: str, expires: int = 300, inline: bool = True) -> str:
    params = {"Bucket": bucket, "Key": key}
    if inline:
        params["ResponseContentDisposition"] = "inline"
    ct = mimetypes.guess_type(key)[0]
    if ct:
        params["ResponseContentType"] = ct
    return s3_client().generate_presigned_url(
        "get_object",
        Params=params,
        ExpiresIn=expires,
        HttpMethod="GET",
    )

def copy_object(src_bucket: str, src_key: str, dst_bucket: str, dst_key: str):
    s3_client().copy_object(
        Bucket=dst_bucket,
        Key=dst_key,
        CopySource={"Bucket": src_bucket, "Key": src_key},
        MetadataDirective="REPLACE",
    )