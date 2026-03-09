# Shelfie Catalog Digitization — Server

This folder contains a FastAPI API server plus a background worker.

- **API**: uploads/queues video processing jobs and serves the generated catalog
- **Worker**: consumes SQS messages, downloads videos from S3, extracts barcodes, and persists results

## Prerequisites

- Python **3.10+**
- An S3 bucket + SQS queue (or LocalStack; see env notes below)
- A database:
	- Local dev: SQLite (recommended)
	- Production: Postgres (RDS, etc.)

## Configuration (.env)

Create `server/.env` from the example:

```bash
cp server/.env.example server/.env
```

Minimum variables for local dev:

- `DEBUG=true`
- `SQLITE_DB_PATH=./dev.db`
- `AWS_REGION`
- `AWS_S3_BUCKET`
- `AWS_SQS_QUEUE_URL`

Optional (useful for local AWS emulation):

- `AWS_ENDPOINT_URL` (supported by the code for S3/SQS clients)

Notes:

- `DEBUG=true` forces SQLite using `SQLITE_DB_PATH` (default `./dev.db`) and does not require `DATABASE_URL`.
- `DEBUG=false` requires a valid `DATABASE_URL` (intended for production).

- The API process loads `server/.env` automatically (see `python-dotenv` usage in `main.py`).
- The worker also loads `server/.env` automatically (see the `worker` package).

Email notifications:

- The API accepts an optional `notify_email` when creating a job.
	- `POST /api/v1/jobs/upload` (multipart): add form field `notify_email`
	- `POST /api/v1/jobs/generate-upload-url` (json): include `{"notify_email": "you@example.com"}`
- The worker will send Brevo template `4` to that address (best-effort). If `notify_email` is omitted, no email is sent.

### Environment variables (full list)

For the authoritative, up-to-date list (with comments and defaults), see:

- [server/.env.example](server/.env.example)

Quick reference:

- **Core**: `DEBUG`, `PORT`, `DEFAULT_STORE_ID`
- **Database**: `SQLITE_DB_PATH`, `DATABASE_URL`, `DB_CONNECT_TIMEOUT_SECONDS`, `DB_FALLBACK_TO_SQLITE`, `DOCKER`
- **AWS**: `AWS_REGION`, `AWS_S3_BUCKET`, `AWS_SQS_QUEUE_URL`, `AWS_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`
- **Worker tuning**: `FRAME_SAMPLE_FPS`, `SQS_VISIBILITY_TIMEOUT_SECONDS`, `WORKER_IDLE_SLEEP_SECONDS`
- **Quality gate**: `QUALITY_GATE_SAMPLE_FPS`, `QUALITY_MIN_MEAN_BRIGHTNESS`, `QUALITY_MIN_LAPLACIAN_VARIANCE`, `BREVO_API_KEY`
- **LLM**: `ENABLE_LLM`, `BEDROCK_MODEL_ID`, `BEDROCK_REGION`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, `LLM_MAX_VIDEO_MB`, `LLM_VIDEO_MIME_TYPE`
- **Opt-in integration tests**:
	- AWS: `RUN_AWS_INTEGRATION_TESTS`, `AWS_TEST_PREFIX`, `AWS_IT_CONNECT_TIMEOUT`, `AWS_IT_READ_TIMEOUT`, `AWS_IT_HTTP_TIMEOUT`, `AWS_IT_MAX_ATTEMPTS`
	- OpenFoodFacts: `RUN_OPENFOODFACTS_INTEGRATION_TESTS`, `OFF_TEST_BARCODES`
- **Barcode test**: `BARCODE_TEST_SAMPLE_FPS`

## Run without Docker (local)

### 1) Set up a virtualenv + install deps

From the repo root:

```bash
python -m venv .venv
source .venv/bin/activate

pip install -r server/requirements.txt
```

If you plan to run the **worker** locally, you also need the system dependency for barcode decoding:

```bash
sudo apt-get update
sudo apt-get install -y libzbar0
```

### 2) Start the API

```bash
cd server

# Dev mode (auto-reload)
uvicorn main:app --reload --host 0.0.0.0 --port ${PORT:-8000}
```

OpenAPI docs:

- http://localhost:8000/docs

### 3) Start the worker (separate terminal)

```bash
cd server
python -m worker
```

## Run with Docker (Docker Compose)

### 1) Create `server/.env`

```bash
cp server/.env.example server/.env
```

Fill in `DATABASE_URL`, `AWS_S3_BUCKET`, `AWS_SQS_QUEUE_URL`, etc.

### 2) Start the stack

From the repo root:

```bash
docker compose up --build
```

This starts:

- `api` on port `8000` (FastAPI)
- `worker` (background SQS consumer)

OpenAPI docs:

- http://localhost:8000/docs

To run only the API:

```bash
docker compose up --build api
```

To stop everything:

```bash
docker compose down
```

## Running tests

The test suite uses an isolated SQLite DB per test and stubs S3/SQS, so it runs offline.

```bash
python -m venv .venv
source .venv/bin/activate

pip install -r server/requirements.txt -r server/requirements-dev.txt
pytest -q server/tests
```

### AWS integration tests (real S3/SQS)

There are opt-in integration tests that actually call AWS.

They are skipped unless you explicitly enable them:

```bash
conda activate skua

export RUN_AWS_INTEGRATION_TESTS=1
pytest -q -m integration server/tests
```

Recommendations before running:

- Use a **dedicated** S3 bucket and SQS queue for testing to avoid impacting production.
- (Optional) Set `AWS_TEST_PREFIX=integration-tests` to make cleanup easier.
- Prefer IAM roles (EC2 instance profile / ECS task role) over long-lived keys.

## Deployment guidance (handling credentials safely)

### Don’t deploy by copying `.env` into the image

Treat `server/.env` as **local development** only. For production, inject configuration via your platform’s environment variables / secrets mechanism.

### Fastest on AWS: EC2 VM + Docker Compose (manual `.env` + certs)

If you want the quickest deployment with the least AWS service setup, run it on a single EC2 VM.

High-level idea:

- You **do** create `server/.env` on the VM (it is not checked into git; `server/.env` is ignored).
- If your Postgres requires a CA bundle, you **do** copy that bundle into `server/certs/` on the VM.
- You **don’t** bake secrets into the Docker image.
- You **should** use an EC2 Instance Profile (IAM role) so you don’t store AWS keys in `.env`.

Steps (Ubuntu example):

- 1) Launch an EC2 instance
	- Security group inbound: allow `80/443` (recommended) or temporarily `8000` for testing.
	- Attach an **IAM role (Instance Profile)** with S3 + SQS permissions.
- 2) Install Docker + Compose

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin
```

- 3) Copy the repo to the VM
	- Option A: `git clone` on the VM
	- Option B: `scp`/`rsync` the folder

- 4) Create your production env file on the VM

```bash
cd shelfie-catalog-digitization
cp server/.env.example server/.env
```

Edit `server/.env` and set at least:

- `DEBUG=False`
- `DATABASE_URL=...` (your RDS Postgres URL)
- `AWS_REGION=...`
- `AWS_S3_BUCKET=...`
- `AWS_SQS_QUEUE_URL=...`

AWS credentials:

- Recommended: leave `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` empty and rely on the EC2 role.
- Only use static keys if you cannot attach an instance role.

- 5) (If needed) Copy your DB CA bundle into `server/certs/`

If your `DATABASE_URL` uses `sslmode=verify-full` or `sslmode=verify-ca` and sets `sslrootcert=...`, make sure that file exists on the VM.

Example (copy a local bundle to the VM):

```bash
scp global-bundle.pem ubuntu@<EC2_PUBLIC_IP>:/home/ubuntu/shelfie-catalog-digitization/server/certs/global-bundle.pem
```

Then set `DATABASE_URL` to include (example):

- `?sslmode=verify-full&sslrootcert=/certs/global-bundle.pem`

(`docker-compose.yml` mounts `server/certs` into the containers at `/certs`.)

- 6) Start API + worker

```bash
docker compose up --build -d
```

- 7) Verify
	- API docs: `http://<EC2_PUBLIC_IP>:8000/docs` (if you opened 8000)

For a real deployment, put the API behind HTTPS (ALB recommended) and only expose `80/443` publicly.

### Prefer IAM roles over long-lived AWS keys

The code uses `boto3`, which supports the standard AWS credential chain.

- **Best practice**: give your runtime an IAM role (no `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` in env)
	- ECS/Fargate: Task Role
	- EC2: Instance Profile
	- EKS: IRSA
- Use static keys only for local testing or if you have no better option.

Minimum IAM permissions (conceptually):

- S3: `s3:PutObject` (uploads), `s3:GetObject` (worker downloads)
- SQS: `sqs:SendMessage` (API), `sqs:ReceiveMessage` + `sqs:DeleteMessage` (worker)

### Deploying as two processes

You need **two** running processes in production:

- API container (runs `uvicorn main:app ...`)
- Worker container (runs `python worker.py`)

On container platforms (ECS/K8s), this is typically two services/deployments using the **same** image with different commands.

### Database in production

- Use a managed Postgres (RDS, etc.) and set `DATABASE_URL` via a secret store (AWS Secrets Manager, SSM Parameter Store, Kubernetes Secret, etc.).
- If you require TLS verification, include `sslmode=verify-full` or `sslmode=verify-ca` and provide `sslrootcert`.
	- Local dev: point `sslrootcert` at a file in `server/certs/`
	- Containers: mount the CA bundle (for example to `/certs/...`) and set `sslrootcert=/certs/<bundle>.pem`

### Suggested deployment shape (AWS example)

- Build the image from `server/Dockerfile` and push to ECR
- Run API behind an ALB (terminate HTTPS at the load balancer)
- Run the worker as a separate ECS service (no public ingress)
- Store `DATABASE_URL`, `AWS_S3_BUCKET`, `AWS_SQS_QUEUE_URL` as task env/secrets
- Attach an IAM Task Role with the S3/SQS permissions above

### Note about migrations

The API currently runs `SQLAlchemy Base.metadata.create_all()` on startup. This is convenient for hackathon/dev use. For a stricter production setup, consider managing schema changes with Alembic migrations.
