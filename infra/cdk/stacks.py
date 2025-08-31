from __future__ import annotations
from aws_cdk import (
    Stack, aws_s3 as s3, aws_dynamodb as ddb, RemovalPolicy,
    aws_iam as iam, aws_kms as kms
)
from constructs import Construct

class CoreStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        key = kms.Key(self, "KktMainKey", enable_key_rotation=True)
        # Buckets
        self.uploads = s3.Bucket(self, "Uploads",
            bucket_name=None,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=key,
            auto_delete_objects=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
        )
        self.assets = s3.Bucket(self, "Assets",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
        )
        self.public = s3.Bucket(self, "Public",
            public_read_access=False,
            website_index_document="index.html",
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # DynamoDB Tables
        self.products = ddb.Table(self, "Products",
            partition_key=ddb.Attribute(name="product_id", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery=True,
            encryption=ddb.TableEncryption.AWS_MANAGED
        )
        self.listings = ddb.Table(self, "Listings",
            partition_key=ddb.Attribute(name="listing_id", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery=True,
            encryption=ddb.TableEncryption.AWS_MANAGED
        )
        self.users = ddb.Table(self, "Users",
            partition_key=ddb.Attribute(name="user_id", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery=True,
            encryption=ddb.TableEncryption.AWS_MANAGED
        )
        self.jobs = ddb.Table(self, "Jobs",
            partition_key=ddb.Attribute(name="job_id", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery=True,
            encryption=ddb.TableEncryption.AWS_MANAGED
        )
        # IAM Policy for Lambdas calling Bedrock + S3/Dynamo
        self.lambda_policy = iam.ManagedPolicy(self, "LambdaBedrockS3DdbPolicy",
            statements=[
                iam.PolicyStatement(
                    actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                    resources=["*"]
                ),
                iam.PolicyStatement(
                    actions=["dynamodb:*"],
                    resources=[self.products.table_arn, self.listings.table_arn, self.users.table_arn, self.jobs.table_arn]
                ),
                iam.PolicyStatement(
                    actions=["s3:*Object", "s3:ListBucket"],
                    resources=[self.uploads.bucket_arn, f"{self.uploads.bucket_arn}/*", self.assets.bucket_arn, f"{self.assets.bucket_arn}/*", self.public.bucket_arn, f"{self.public.bucket_arn}/*"]
                ),
                iam.PolicyStatement(
                    actions=["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"],
                    resources=[key.key_arn]
                ),
                iam.PolicyStatement(
                    actions=["transcribe:*"],
                    resources=["*"]
                ),
            ]
        )
