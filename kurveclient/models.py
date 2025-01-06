#!/usr/bin/env python
from pydantic import BaseModel, Field


class LocalPayload(BaseModel):
    provider: str = Field(default='local')
    path: str
    # Options: csv, parquet, excel, json
    fmt: str


class RestCatalogPayload(BaseModel):
    provider: str = Field(default='catalog')
    # This is also the warehouse
    catalog_name: str
    catalog_type: str = 'rest'
    catalog_uri: str
    catalog_namespaces: str
    catalog_credential: str
    catalog_scope: str = 'all'


class S3Payload(BaseModel):
    provider: str = Field(default='s3')
    s3_bucket: str
    s3_prefix: str
    aws_key: str
    aws_secret: str
    # Options: csv, parquet, excel, json
    s3_format: str
    s3_partitioned: bool
