from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    aws_region: str = os.getenv("AWS_REGION", "us-west-2")
    account_id: str = os.getenv("AWS_ACCOUNT_ID", "")
    stage: str = os.getenv("STAGE", "dev")

    # Bedrock
    bedrock_text_model_id: str = os.getenv("BEDROCK_TEXT_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0")
    bedrock_image_model_id: str = os.getenv("BEDROCK_IMAGE_MODEL_ID", "us.amazon.titan-image-generator-v2:0")
    bedrock_text_fallback_ids:  str = os.getenv("BEDROCK_TEXT_FALLBACK_IDS", "us.anthropic.claude-3-5-sonnet-20241022-v2:0")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    llm_top_p: float = float(os.getenv("LLM_TOP_P", "0.8"))
    llm_streaming: bool = os.getenv("LLM_STREAMING", "true").lower() == "true"
    llm_cache_prompt: bool = os.getenv("LLM_CACHE_PROMPT", "false").lower() == "true"
    
    # S3
    s3_bucket_uploads: str = os.getenv("S3_BUCKET_UPLOADS", "kkt-uploads-dev")
    s3_bucket_assets: str = os.getenv("S3_BUCKET_ASSETS", "kkt-assets-dev")
    s3_bucket_public: str = os.getenv("S3_BUCKET_PUBLIC", "kkt-public-dev")

    # DynamoDB
    ddb_products: str = os.getenv("DDB_TABLE_PRODUCTS", "kkt_products_dev")
    ddb_listings: str = os.getenv("DDB_TABLE_LISTINGS", "kkt_listings_dev")
    ddb_users: str = os.getenv("DDB_TABLE_USERS", "kkt_users_dev")
    ddb_jobs: str = os.getenv("DDB_TABLE_JOBS", "kkt_jobs_dev")
    ddb_conversations: str = os.getenv("DDB_TABLE_CONVERSATIONS", "kkt_conversations_dev")
    ddb_messages: str = os.getenv("DDB_TABLE_MESSAGES", "kkt_messages_dev")

    # Auth
    auth_bypass: bool = os.getenv("AUTH_BYPASS", "true").lower() == "true"
    cognito_user_pool_id: str = os.getenv("COGNITO_USER_POOL_ID", "")
    cognito_client_id: str = os.getenv("COGNITO_CLIENT_ID", "")

settings = Settings()
