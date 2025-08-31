# KaiKashi DreamForge — Backend Starter

Local-first starter para **FastAPI + Strands Agents + AWS (Bedrock, DynamoDB, S3, KMS)**.
Despliegue a producción con **AWS CDK (Python)**.

> **Qué hace:** toma una idea del usuario (“hazme un póster de X”), la interpreta, genera assets (imagen/pdf/… si aplica), crea un **producto** y una **listing** y los deja listables con URLs prefirmadas.

## Tabla de contenidos
* [Arquitectura](#arquitectura)
* [Stack técnico](#stack-técnico)
* [Estructura del repo](#estructura-del-repo)
* [Preparación local](#preparación-local)
* [Variables de entorno](#variables-de-entorno)
* [Ejecutar la API local](#ejecutar-la-api-local)
* [Endpoints (formas y ejemplos)](#endpoints-formas-y-ejemplos)
* [Infraestructura AWS (CDK)](#infraestructura-aws-cdk)
* [Modelo de datos](#modelo-de-datos)
* [Permisos/IAM](#permisosiam)
* [Buenas prácticas y seguridad](#buenas-prácticas-y-seguridad)
* [Aws ecosistema](#aws-ecosistema)
* [Postman](#postman)
* [Licencia](#licencia)

## Arquitectura
* **API** (local con FastAPI / prod con API Gateway + Lambda).
* **Agentes** (Strands) orquestan: *interpretar idea* → *generar diseño/assets* → *publicar listing*.
* **Almacenamiento**
  * **DynamoDB**: `products`, `listings`, `users`, `jobs`, `conversations`, `messages`.
  * **S3**: `uploads`, `assets`, `public`. Buckets con cifrado **KMS**.
* **Bedrock**: modelo de texto para interpretación y (opcional) imagen para generación.
* **KMS**: una clave para cifrar S3.
* **CDK**: define todo lo anterior y los roles/policies de Lambda.

## Stack técnico
* **Python 3.10+**
* **FastAPI + Uvicorn** (modo local)
* **AWS CDK v2** (Python)
* **boto3** (S3, DynamoDB, STS…)
* **Strands Agents** (LLM orchestration)
* **Amazon Bedrock** (texto / imagen)
* **DynamoDB (PAY\_PER\_REQUEST)**, **S3 (KMS)**, **API Gateway + Lambda**



## Preparación local
1. **Python 3.10+**
2. Crear venv e instalar dependencias:
   ```bash
   python -m venv .venv
   # Linux/Mac
   source .venv/bin/activate
   # Windows
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Copiar `.env.example` a `.env` y rellenar valores (ver abajo).
4. (Opcional) Crear tablas/buckets locales/remotos si aún no existen.

## Variables de entorno
Copia `.env.example` → `.env`. Campos destacados:
```env
# AWS
AWS_REGION=us-west-2
AWS_ACCOUNT_ID=xxxxxxxxxxxx
STAGE=dev

# Bedrock
BEDROCK_TEXT_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
BEDROCK_TEXT_FALLBACK_IDS=us.anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_IMAGE_MODEL_ID=amazon.titan-image-generator-v2:0

LLM_TEMPERATURE=0.3
LLM_TOP_P=0.8
LLM_STREAMING=true
LLM_CACHE_PROMPT=false

# S3 (nombres creados por CDK)
S3_BUCKET_UPLOADS=kkt-uploads-dev
S3_BUCKET_ASSETS=kkt-assets-dev
S3_BUCKET_PUBLIC=kkt-public-dev

# DynamoDB (nombres creados por CDK)
DDB_TABLE_PRODUCTS=kkt_products_dev
DDB_TABLE_LISTINGS=kkt_listings_dev
DDB_TABLE_USERS=kkt_users_dev
DDB_TABLE_JOBS=kkt_jobs_dev
DDB_TABLE_CONVERSATIONS=kkt_conversations_dev
DDB_TABLE_MESSAGES=kkt_messages_dev

# Auth (modo dev)
AUTH_BYPASS=true
```

## Ejecutar la API local
```bash
uvicorn api.main:app --reload --port 9000
```

* Salud:
  ```bash
  curl http://localhost:9000/ping
  ```
> **Nota:** la API local usa los mismos helpers (`shared/*`) que producción; si apuntas a AWS reales, estarás usando tus recursos en la nube.



## Endpoints (formas y ejemplos)

> A continuación se documentan **formas de los endpoints**. **No** exponemos aquí el dominio real del API Gateway. Usa `https://{API_URL}/prod/...` y coloca el tuyo cuando compartas por correo.

### 1) Crear producto/asset desde idea

**POST** `/prod/create`
Crea conversación, interpreta idea, genera assets y crea producto + listing.

```bash
curl --location 'https://{API_URL}/prod/create' \
  --header 'Content-Type: application/json' \
  --data '{
    "q": "Hazme una imagen de Colombia",
    "user_id": "user_dev_001",
    "price_cents": 1500
  }'
```

**Respuesta (resumen):**

```json
{
  "conversation_id": "conv_xxxxxxxx",
  "brief": { "...": "..." },
  "design": {
    "media_keys": ["assets/user_dev_001/generated/poster_xxx.png"],
    "package": { "design_prompt": "...", "brief": { ... } }
  },
  "ids": { "product_id": "prd_...", "listing_id": "lst_..." },
  "price_cents": 1500,
  "currency": "USD",
  "user_id": "user_dev_001",
  "user_id_defaulted": false
}
```

> Si **no** envías `user_id`, la función responde indicando que usó el **usuario de pruebas** por defecto.

### 2) Listar productos del usuario (con URLs prefirmadas)

**GET** `/prod/products?owner={user_id}&limit=20[&page_token=...]`

```bash
curl --location 'https://{API_URL}/prod/products?owner=user_dev_001&limit=20'
```

**Respuesta (recorte):**

```json
{
  "items": [
    {
      "product": {
        "product_id": "prd_...",
        "title": "...",
        "status": "draft",
        "media": [
          {
            "key": "assets/user_dev_001/generated/poster_xxx.png",
            "url": "https://...X-Amz-Algorithm=AWS4-HMAC-SHA256&...",
            "type": "image"
          }
        ]
      },
      "listing": { "status": "active", "price_cents": 1500, "currency": "USD" }
    }
  ],
  "count": 1,
  "has_more": false,
  "next_page_token": null,
  "applied_filters": { "owner": "user_dev_001", "status": null, "limit": 20 }
}
```

* **owner / user\_id obligatorio**: si falta, retorna `400` con `{"error":"missing owner/user_id"}`.
* **URLs prefirmadas**: válidas pocos minutos; se devuelven con **Signature V4** y `Content-Disposition: inline` para abrir en el navegador.
* **Paginación**: usa `next_page_token` (base64) si `has_more=true`.

---

## Infraestructura AWS (CDK)

El stack crea:

* **KMS Key** (rotación activada).
* **S3 Buckets**:

  * `Uploads` (privado, KMS, SSL, versionado).
  * `Assets` (privado, KMS, SSL, versionado).
  * `Public` (hosting estático opcional).
* **DynamoDB (PAY\_PER\_REQUEST)**:

  * `Products`, `Listings`, `Users`, `Jobs`, `Conversations`, `Messages`.
  * Índices de ejemplo en Conversations/Messages si aplica.
* **IAM**:

  * Rol de Lambda con políticas para: `bedrock:InvokeModel`, `dynamodb:*` sobre tablas del stack, `s3:*Object` en los buckets, `kms:Encrypt/Decrypt/...` en la key.
* **Lambda Layers**:

  * `AppCommonLayer` con `layers/app_common/python` (agents + shared).
* **Lambdas**:

  * `CreateFn` (`/create`), `ListingFn` (`/products`), y las auxiliares (`interpret`, `design`) si las publicas.
* **API Gateway REST**:

  * Stage `prod`.
  * Rutas: `/create`, `/products`, (y/o `/interpret`, `/design`).

Despliegue:

```bash
cd infra/cdk
# (usa el mismo venv)
cdk synth
cdk deploy
```

> Si el **Layer** pesa mucho, recuerda que Lambda impone **límite de 250 MB descomprimido**. Mantén el layer ligero.

---

## Modelo de datos

**Products**

```json
{
  "product_id": "prd_xxx",
  "owner_id": "user_dev_001",
  "title": "...",
  "description": "...",
  "status": "draft|active",
  "media_keys": ["assets/.../file.png"]
}
```

**Listings**

```json
{
  "listing_id": "lst_xxx",
  "product_id": "prd_xxx",
  "price_cents": 1500,
  "currency": "USD",
  "status": "active|inactive",
  "metadata": { "stage": "dev" }
}
```

**Conversations / Messages**
Se almacenan mensajes de la interacción (`user` / `assistant`) y referencias a `media_keys` generados.

---

## Permisos/IAM

El rol de Lambda incluye:

* **Bedrock**: `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`.
* **DynamoDB**: CRUD sobre las tablas del stack.
* **S3**: `s3:GetObject`, `s3:PutObject`, `s3:ListBucket` en `uploads`, `assets`, `public`.
* **KMS**: `Encrypt/Decrypt/GenerateDataKey/DescribeKey` sobre la Key creada.

---

## Buenas prácticas y seguridad

* **Signature V4 obligatorio** con S3+KMS para URLs prefirmadas. El helper `shared/aws.py` fuerza `signature_version="s3v4"`.
* **Response headers** en prefirmadas: `Content-Disposition=inline` y `ResponseContentType` deducido por extensión.
* Evita incluir secretos en el repo. Usa `.env` y **AWS Secrets Manager** si subes a producción real.
* **Least privilege**: limita tablas/buckets a los ARNs del stack (ya lo hace el CDK).

## Aws ecosistema
![alt text](assets/image.png)
![alt text](assets/image-3.png)
![alt text](assets/image-4.png)
![alt text](assets/image-5.png)
![alt text](assets/image-6.png)

## Postman
![alt text](assets/image-1.png)
![alt text](assets/image-2.png)


## Licencia
Privado para el hackatón. Revisa las **políticas del Hackathon** y términos de uso de Bedrock/LLMs.
