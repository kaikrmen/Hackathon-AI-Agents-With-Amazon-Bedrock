# KaiKashi Tech — DreamForge (Backend Starter)
Local-first starter with FastAPI + Strands Agents + AWS SDK (boto3). Production deploy via AWS CDK (Python).

## Quickstart (Local)
1) Python 3.10+
2) `python -m venv .venv && source .venv/bin/activate` (Windows: `.venv\Scripts\activate`)
3) `pip install -r requirements.txt`
4) Copy `.env.example` to `.env` and set values.
5) Run API: `uvicorn api.main:app --reload --port 9000`

## Layout
- `api/` FastAPI local API for testing pipeline.
- `agents/` Strands Agents factory + pipelines (interpret → design → listing).
- `lambdas/` Lambda handlers for Step Functions (production).
- `shared/` Reusable AWS utilities (S3, DynamoDB, config, cache).
- `infra/` AWS CDK app + IAM policies + (Optionally) Step Functions definition.

## Notes
- Uses Strands Agents (`strands`) as LLM orchestrator over Bedrock.
- Multimodal: text, images, pdf, audio. Audio can be transcribed with Amazon Transcribe.
- Image generation stubbed via Bedrock Titan Image (if enabled in your region/account).
- Caching: Strands cache + DynamoDB content-addressable cache (SHA256 of prompt bundle).

# Products
aws dynamodb create-table `
  --table-name kkt_products_dev `
  --attribute-definitions AttributeName=product_id,AttributeType=S `
  --key-schema AttributeName=product_id,KeyType=HASH `
  --billing-mode PAY_PER_REQUEST `
  --region us-west-2

# Listings
aws dynamodb create-table `
  --table-name kkt_listings_dev `
  --attribute-definitions AttributeName=listing_id,AttributeType=S `
  --key-schema AttributeName=listing_id,KeyType=HASH `
  --billing-mode PAY_PER_REQUEST `
  --region us-west-2

# Users
aws dynamodb create-table `
  --table-name kkt_users_dev `
  --attribute-definitions AttributeName=user_id,AttributeType=S `
  --key-schema AttributeName=user_id,KeyType=HASH `
  --billing-mode PAY_PER_REQUEST `
  --region us-west-2

# Jobs
aws dynamodb create-table `
  --table-name kkt_jobs_dev `
  --attribute-definitions AttributeName=job_id,AttributeType=S `
  --key-schema AttributeName=job_id,KeyType=HASH `
  --billing-mode PAY_PER_REQUEST `
  --region us-west-2

aws dynamodb create-table `
  --table-name kkt_messages_dev `
  --attribute-definitions AttributeName=job_id,AttributeType=S `
  --key-schema AttributeName=job_id,KeyType=HASH `
  --billing-mode PAY_PER_REQUEST `
  --region us-west-2

  aws dynamodb create-table `
  --table-name kkt_conversations_dev `
  --attribute-definitions AttributeName=job_id,AttributeType=S `
  --key-schema AttributeName=job_id,KeyType=HASH `
  --billing-mode PAY_PER_REQUEST `
  --region us-west-2


## S3, DynamoDB, Lambda
![alt text](assets/image.png)
![alt text](assets/image-3.png)
![alt text](assets/image-4.png)
![alt text](assets/image-5.png)
![alt text](assets/image-6.png)

## Imagen Generada
<img src="https://kaikashicorestack-assets9a31d427-kmuvg2razskb.s3.us-west-2.amazonaws.com/assets/user_dev_001/generated/poster_crear%20imagen%20representativa%20de%20Colombia.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAS3HWOHB54DTGINBK%2F20250831%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20250831T231950Z&X-Amz-Expires=300&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEKD%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLXdlc3QtMiJIMEYCIQCtpEmZZlSXH%2Bnwi72ps%2FGtVc%2BZfvYo0SVjmhUytzCzDAIhAKd%2BjpambmdS9s5SJodeMRNVTOuLDqNSgHhaRPcn2hSNKuQCCPj%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEQABoMMTk1OTM3ODQzMzIzIgy%2BOXTAigKTCib8xDIquALsCg%2BJr5KB3I2QjtJugeH0q0xPBUpmn%2FGA%2B3a9jfizyj5a3GfzuRM9AzVuRCK2HgmkPUlw%2BQlgQ5Rz3SfOWa7sZ3WRLR61FKx%2F%2FkDF93BvLfDz5aMvI6X9CQhg7vUETNoMICFw643j86z85HggVRMMQdTgdZJAwtC%2FwjouSi6yNxnZSlNOUJGn9t503%2F18gUXVN4g1WvB6THteIa2SUbgLP3sBVAWQixdXmrFKfeF8KJG3iZrThUyez8yWxuNe2%2BuMRnvBqWVrQ0R0Ti729JIcMwnKqBF8f0JpAThbcgAXbeZPTPfjEpaLyFivJYHH3TVHlERT3fVyWfsCLa9gAgxW9NVCi3YXwkcMLkS%2F7jWhG1DO3SfFiZI3V10YsikGdD65qt5qM1wk84q3rB1GK70gNyFpfPMeUVowk9rRxQY6rALxu1UkBTlOTXFR6LFyFr2LRKfC2weAgrKmMGqRLKkoVQWnmiS29OuN%2Bfj97LnExpoIByAjkr1aJh60K8yOBTGqjpnpdHEx34RS3DQqr45auLVNQQZMuyt9UAT5TSWHm6HckRBIHgqnMJR6EqIWInI4ulfjpAwo4YC2KP7CD24N9VsbwySnx9Z1ov38S4CDCSRUtj9PIgfkNEVI8eQF%2BdF4FQ3M7Fazojlg8A1o%2B%2BpYfPbS3PEO90M4ZDeN%2F8ID0oNcHoXM53phIRHMf9ZwYcLojDBxbV1yHZtY4iN5bSz2RRZLAuXUp75t6p%2BQQAzEA64zttzr6O8zohiv69wfyyNL2UD5k1ekIiVdVqOxunlnX2jnpvYajT%2F4EF6zRIoby5C2KqGGZd%2FX83RaA4A%3D&X-Amz-Signature=8d14c3b53185452df7182cef7893564b04c1b3dd09d777c60496c785cd451ad5&X-Amz-SignedHeaders=host&response-content-disposition=inline">

## Postman
![alt text](assets/image-1.png)
![alt text](assets/image-2.png)