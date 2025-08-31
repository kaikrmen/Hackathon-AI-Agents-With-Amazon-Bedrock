from __future__ import annotations
from aws_cdk import (
    Stack, Duration, CfnOutput,
    aws_s3 as s3, aws_dynamodb as ddb,
    aws_iam as iam, aws_kms as kms,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
)
from constructs import Construct
from aws_cdk.aws_lambda_python_alpha import PythonFunction, PythonLayerVersion


class CoreStack(Stack):
    def __init__(self, scope: Construct, _id: str, **kwargs):
        super().__init__(scope, _id, **kwargs)

        key = kms.Key(self, "KktMainKey", enable_key_rotation=True)

        uploads = s3.Bucket(self, "Uploads",
            encryption=s3.BucketEncryption.KMS, encryption_key=key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL, enforce_ssl=True,
            versioned=True, auto_delete_objects=False)
        assets = s3.Bucket(self, "Assets",
            encryption=s3.BucketEncryption.KMS, encryption_key=key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL, enforce_ssl=True,
            versioned=True)
        public = s3.Bucket(self, "Public",
            public_read_access=False, website_index_document="index.html")

        products = ddb.Table(self, "Products",
            partition_key=ddb.Attribute(name="product_id", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True)
        listings = ddb.Table(self, "Listings",
            partition_key=ddb.Attribute(name="listing_id", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True)
        users = ddb.Table(self, "Users",
            partition_key=ddb.Attribute(name="user_id", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST)
        jobs = ddb.Table(self, "Jobs",
            partition_key=ddb.Attribute(name="job_id", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST)
        conversations = ddb.Table(self, "Conversations",
            partition_key=ddb.Attribute(name="conversation_id", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True)
        messages = ddb.Table(self, "Messages",
            partition_key=ddb.Attribute(name="conversation_id", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="created_at", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True)


        managed = iam.ManagedPolicy(self, "LambdaBedrockS3DdbPolicy",
            statements=[
                iam.PolicyStatement(actions=[
                    "bedrock:InvokeModel","bedrock:InvokeModelWithResponseStream"
                ], resources=["*"]),
                iam.PolicyStatement(actions=["dynamodb:*"], resources=[
                    products.table_arn, listings.table_arn, users.table_arn, jobs.table_arn,
                    conversations.table_arn, messages.table_arn
                ]),
                iam.PolicyStatement(actions=["s3:*Object","s3:ListBucket"], resources=[
                    uploads.bucket_arn, f"{uploads.bucket_arn}/*",
                    assets.bucket_arn, f"{assets.bucket_arn}/*",
                    public.bucket_arn, f"{public.bucket_arn}/*",
                ]),
                iam.PolicyStatement(actions=[
                    "kms:Encrypt","kms:Decrypt","kms:GenerateDataKey","kms:DescribeKey"
                ], resources=[key.key_arn]),
            ])

        role = iam.Role(self, "KaiKashiLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                managed
            ])

        app_layer = PythonLayerVersion(
            self, "AppCommonLayer",
            entry="layers/app_common",
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_11]
        )

        env = {
            "DDB_PRODUCTS": products.table_name,
            "DDB_LISTINGS": listings.table_name,
            "DDB_USERS": users.table_name,
            "DDB_JOBS": jobs.table_name,
            "DDB_CONVERSATIONS": conversations.table_name,
            "DDB_MESSAGES": messages.table_name,
            "S3_UPLOADS": uploads.bucket_name,
            "S3_ASSETS": assets.bucket_name,
            "S3_PUBLIC": public.bucket_name,
            "BEDROCK_TEXT_MODEL_ID": "us.anthropic.claude-sonnet-4-20250514-v1:0",
            "BEDROCK_TEXT_FALLBACK_IDS": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            "LLM_TEMPERATURE": "0.3",   
            "LLM_TOP_P": "0.8",        
            "LLM_STREAMING": "true",   
            "LLM_CACHE_PROMPT": "",     
            "BEDROCK_IMAGE_MODEL_ID": "amazon.titan-image-generator-v2:0",
            "STAGE": "dev",
            "AUTH_BYPASS": "true",     
        }

        fn_interpret = PythonFunction(self, "InterpretFn",
            entry="lambdas/interpret", index="index.py", handler="handler",
            runtime=_lambda.Runtime.PYTHON_3_11, memory_size=512, timeout=Duration.seconds(30),
            environment=env, role=role, layers=[app_layer])

        fn_design = PythonFunction(self, "DesignFn",
            entry="lambdas/design", index="index.py", handler="handler",
            runtime=_lambda.Runtime.PYTHON_3_11, memory_size=1024, timeout=Duration.seconds(60),
            environment=env, role=role, layers=[app_layer])

        fn_listing = PythonFunction(self, "ListingFn",
            entry="lambdas/listing", index="index.py", handler="handler",
            runtime=_lambda.Runtime.PYTHON_3_11, memory_size=512, timeout=Duration.seconds(30),
            environment=env, role=role, layers=[app_layer])
        
        fn_create = PythonFunction(
            self, "CreateFn",
            entry="lambdas/create", index="index.py", handler="handler",
            runtime=_lambda.Runtime.PYTHON_3_11, memory_size=1024, timeout=Duration.seconds(60),
            environment=env, role=role, layers=[app_layer])

        products.grant_read_write_data(fn_interpret); products.grant_read_write_data(fn_design); products.grant_read_data(fn_listing)
        listings.grant_read_write_data(fn_listing)
        uploads.grant_read_write(fn_design); assets.grant_read_write(fn_design); assets.grant_read(fn_listing)
        key.grant_encrypt_decrypt(fn_interpret); key.grant_encrypt_decrypt(fn_design); key.grant_encrypt_decrypt(fn_listing)
        conversations.grant_read_write_data(fn_interpret); conversations.grant_read_write_data(fn_design); conversations.grant_read_write_data(fn_create)
        messages.grant_read_write_data(fn_interpret); messages.grant_read_write_data(fn_design); messages.grant_read_write_data(fn_create)

        api = apigw.RestApi(self, "KaiKashiApi",
            rest_api_name="KaiKashi Dream API",
            deploy_options=apigw.StageOptions(stage_name="prod"))

        api.root.add_resource("interpret").add_method("POST", apigw.LambdaIntegration(fn_interpret))
        api.root.add_resource("design").add_method("POST", apigw.LambdaIntegration(fn_design))
        api.root.add_resource("products").add_method("GET", apigw.LambdaIntegration(fn_listing))
        api.root.add_resource("create").add_method("POST", apigw.LambdaIntegration(fn_create))
        CfnOutput(self, "ApiUrl", value=api.url)
