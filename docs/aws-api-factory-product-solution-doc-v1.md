# AWS API Factory — Product & Solution Document (v1)

## 1. Executive summary
**AWS API Factory** is an **open-source, config-driven “factory pattern”** built with the **AWS CDK (Python)** that turns **BYO business logic** into **public-ready APIs** and supporting AWS infrastructure using a small, opinionated set of patterns.

The user picks a deployment **profile**:
- **Minimal**: lower ops overhead, fewer moving parts, sensible defaults that are *somewhat* free-tier friendly.
- **Scalable**: higher resilience/performance defaults, stronger security posture, production observability, and extensibility.

The user picks **API style(s)** and **compute** (both supported):
- **REST API** via **Amazon API Gateway (REST)** → **AWS Lambda** *or* **App Runner**
- **GraphQL** via **AWS AppSync** → Lambda / DynamoDB / Aurora / HTTP (incrementally)

Optional bolt-ons include **Cognito**, **API keys**, **IAM auth**, **DynamoDB**, **S3**, **RDS/Aurora**, **Secrets**, and observability.

> AWS CDK supports Python as a first-class language and deploys CDK apps via CloudFormation.  
> Sources: AWS CDK docs. citeturn0search17turn0search5


---

## 2. Mission & product promise
### Mission
Provide a **simple, repeatable paved road** for developers to deploy APIs on AWS:
- minimal high-level decisions
- safe-by-default security and permissions
- predictable repository conventions
- easy local iteration
- clear escape hatches

### Product promise
With a **single config file** and a **standard project layout**, a user can:
1) attach their business logic,
2) generate wiring/adapter code (optionally via an LLM assistant),
3) deploy a production-ready stack in minutes,
4) operate it with built-in observability (especially in Scalable).

---

## 3. Design principles & guardrails
1. **Opinionated but modular**: a small set of endorsed patterns; add more via modules.
2. **Two profiles only** (Minimal/Scalable) in v1 to avoid “knob explosion”.
3. **Convention over configuration** for code layout and adapter interfaces.
4. **Secure-by-default**: least privilege IAM, secrets never committed, sane public exposure defaults.
5. **No silent code rewrites**: LLM assistant produces a **diff/patch** that the user reviews.
6. **Composable constructs**: teams can adopt constructs without adopting the entire factory.
7. **Deterministic synth**: config → stable CloudFormation output; validation fails fast.

---

## 4. Supported architecture lanes (v1)

### 4.1 REST API lane (Amazon API Gateway REST)
- API Gateway REST APIs are collections of resources and methods integrated with backends like Lambda/HTTP. citeturn0search2turn0search14  
- API Gateway is designed to create, publish, maintain, monitor, and secure REST/HTTP/WebSocket APIs at scale. citeturn0search6

**Compute targets**
- **Lambda** (default)
- **App Runner** (container lane; public web server semantics)

**Auth modes**
- **None**
- **API Keys** (usage plans + required keys on methods) citeturn1search2turn1search14turn1search20
- **IAM auth** (SigV4)
- **Cognito** (JWT authorizer)

### 4.2 GraphQL lane (AWS AppSync)
AWS AppSync provides GraphQL APIs and supports multiple authorization types, including **API keys**, **Lambda**, **IAM**, **OIDC**, and **Cognito User Pools**. citeturn0search11turn0search15turn0search7

**Resolvers / data sources (initial supported set)**
- Lambda resolvers
- DynamoDB data source
- Aurora / RDS (via Lambda or direct integrations later)
- HTTP data source (optional in v1+)

### 4.3 Container lane (AWS App Runner)
- App Runner supports configurable health checks (TCP by default; HTTP optional). citeturn1search0
- App Runner supports automatic scaling configurations (defaults exist; custom configs optional). citeturn1search3

### 4.4 Relational DB lane (Aurora Serverless v2)
Aurora Serverless v2 is an **on-demand, autoscaling configuration** for Aurora that adjusts capacity based on demand. citeturn1search1turn1search4

---

## 5. Minimal vs Scalable defaults (high level)

### 5.1 REST API defaults
**Minimal**
- API Gateway REST API
- Lambda proxy integration for speed
- CloudWatch logs + basic metrics
- No WAF by default
- API keys optional; Cognito optional

**Scalable**
- API Gateway REST API with stronger stage settings (logging/metrics), stricter throttles
- Optional WAF (recommended for public endpoints)
- Structured logging + tracing hooks + alarms
- Domain + TLS patterns (optional module)
- Clear per-route auth configuration

### 5.2 AppSync defaults
**Minimal**
- AppSync GraphQL API
- API key auth *or* Cognito (user choice)
- Lambda resolvers first
- DynamoDB optional

**Scalable**
- Cognito/IAM preferred for production posture
- Resolver structure aligned to domain boundaries
- Alarms + dashboards + tracing hooks

### 5.3 Compute defaults
**Lambda (Minimal)**
- Small memory defaults + short timeout
- Concurrency unmanaged (pay-per-use)
- Shared “middleware” layer for logging/errors

**Lambda (Scalable)**
- Optional reserved/provisioned concurrency per service
- More aggressive timeouts/memory guidance
- Enhanced observability + alarms

**App Runner (Minimal)**
- Default autoscaling
- Default health check (TCP)
- Secrets optional

**App Runner (Scalable)**
- Custom autoscaling config
- HTTP health checks + app endpoint standard
- Secrets Manager integration
- Optional fronting posture modules

### 5.4 Data defaults
**Minimal**
- DynamoDB (simple table), S3 bucket, SSM parameters

**Scalable**
- DynamoDB (point-in-time recovery + alarms) and/or Aurora Serverless v2
- Secrets Manager for secrets
- Backups + retention guidance

---

## 6. How users attach business logic (the “adapter contract”)

### 6.1 Recommended internal structure
Keep domain logic portable:
- `src/<project>/domain/` for pure logic
- thin adapters for AWS integrations

### 6.2 Lambda adapter contract
User provides one of:
- **Single handler**: `def handler(event, context) -> dict`
- **Factory contract**: `def create_handler(factory_context) -> Callable` (advanced)

Factory provides:
- request/response helpers
- error mapping (exceptions → HTTP responses)
- correlation IDs + structured logging middleware

### 6.3 App Runner adapter contract
User provides:
- `app.py` exporting an ASGI app (e.g., FastAPI `app`), or a WSGI app
- Dockerfile (factory can template this)

Factory provides:
- env var + secrets injection patterns
- health check endpoint conventions (e.g., `/healthz`)

---

## 7. LLM “Compatibility Assistant” (scoped & safe)
You want LLM help **limited to generating adapters + config**. The recommended shape:

### 7.1 What it does
- Generates missing `handler.py` / `app.py` adapters that match factory conventions
- Suggests `factory.yaml` routes/resolvers based on detected functions/paths
- Adds minimal pydantic request/response models (optional)
- Produces a **unified diff patch** (never silently edits)

### 7.2 Safety & UX constraints
- Opt-in command: `factory compat`
- User selects scope: folders/files to include (default: `src/services/**` adapters only)
- Redaction filters for secrets and large files
- Output is a patch + a short “why” report
- No deployment actions performed by the assistant

### 7.3 OpenAI integration
- Use OpenAI **Responses API** as the default for new integrations. citeturn0search12turn0search0
- Authenticate via **Bearer API key**, loaded from environment/secret manager. citeturn0search4

---

## 8. Configuration design (`factory.yaml`)

### 8.1 Core schema (conceptual)
```yaml
project:
  name: my-api
  envs: [dev, prod]

profile: minimal | scalable

apis:
  rest:
    enabled: true
    routes:
      - path: /orders
        methods: [GET, POST]
        service: orders
        auth: none | api_key | iam | cognito
  graphql:
    enabled: true
    schema_path: src/graphql/schema.graphql
    auth: api_key | iam | cognito
    resolvers:
      - type: Query
        field: getOrder
        service: orders
        resolver: get_order

compute:
  lambda:
    enabled: true
    services:
      orders:
        entry: src/services/orders/handler.py:handler
        memory_mb: auto
        timeout_s: auto
  apprunner:
    enabled: true
    services:
      public_api:
        dockerfile: src/services/public_api/Dockerfile
        port: 8000
        healthcheck_path: /healthz

data:
  dynamodb:
    enabled: true
    tables:
      - name: orders
        pk: order_id
        sk: created_at
  aurora:
    enabled: false
    engine: postgres
    mode: serverless_v2
    min_acu: 0.5
    max_acu: 8
  s3:
    enabled: true
    buckets:
      - name: uploads

secrets:
  provider: ssm | secrets_manager

observability:
  level: basic | enhanced
```

### 8.2 Validation & docs
- Validate config with pydantic + JSON schema export.
- `factory validate` prints actionable errors and suggestions.
- `factory explain` prints the resolved defaults (Minimal vs Scalable) and the planned resources.

---

## 9. Repository & packaging structure (installable library + starter template)

### 9.1 Monorepo layout (recommended)
```
aws-api-factory/
  README.md
  LICENSE
  pyproject.toml

  src/
    aws_api_factory/              # installable library
      cli/
      config/
      constructs/
        rest_api/
        appsync/
        compute_lambda/
        compute_apprunner/
        auth/
        data/
        observability/
      templates/                  # scaffold templates for services
      llm_assistant/              # optional OpenAI integration
      utils/

  starter/                        # small starter template users copy
    factory.yaml
    infra/
      app.py
      stacks/
        factory_stack.py
    src/
      services/
        hello/
          handler.py
        public_api/
          app.py
          Dockerfile
      graphql/
        schema.graphql
    tests/

  docs/
    concepts/
    modules/
    examples/
```

### 9.2 Installation + usage
- Install library: `pip install aws-api-factory` (future) or editable for contributors.
- Starter workflow: copy `starter/` (or `factory init` scaffolds it).

---

## 10. CLI experience (v1)
- `factory init` — scaffold starter project (or copy from `starter/`)
- `factory validate` — validate config + show resolved defaults
- `factory synth` — CDK synth with standard context
- `factory deploy <env>` — deploy selected env
- `factory destroy <env>` — destroy env (with safe prompts)
- `factory compat` — generate adapter + config patch via LLM (opt-in)

---

## 11. Internal architecture of the library (how to implement)
### 11.1 Core packages
- `aws_api_factory.config`: pydantic models, defaults resolution, schema export
- `aws_api_factory.constructs`: CDK constructs per module
- `aws_api_factory.cli`: CLI orchestration, validation, synth/deploy wrappers
- `aws_api_factory.templates`: code templates + scaffolding
- `aws_api_factory.llm_assistant`: OpenAI client wrapper + patch generation

### 11.2 Module/construct boundaries
Each module exposes:
- `Config` model (validated)
- `Defaults` resolver for Minimal/Scalable
- `Construct` that can be composed into the main `FactoryStack`
- `Outputs` contract (URLs, ARNs, IDs) used by other modules

### 11.3 Escape hatches
- `custom_iam_statements` per service
- `extra_cdk_props` dictionaries where safe
- Ability to import an existing VPC / Hosted Zone / ACM cert

---

## 12. Example user flows

### Flow A — Minimal REST + Lambda
1. `factory init`
2. Add handler in `src/services/orders/handler.py`
3. Update `factory.yaml` routes
4. `factory validate`
5. `factory deploy dev`
6. Use output REST endpoint

### Flow B — Scalable REST + App Runner + Cognito
1. Add `src/services/public_api/app.py` + Dockerfile
2. Set `compute.apprunner.enabled: true`
3. Set `auth: cognito` on routes
4. `factory deploy prod`

### Flow C — AppSync GraphQL + DynamoDB
1. Define GraphQL schema in `src/graphql/schema.graphql`
2. Add resolver functions under `src/services/<svc>/resolvers.py`
3. Enable AppSync + DynamoDB module
4. Deploy and test GraphQL endpoint

### Flow D — Add Aurora Serverless v2
1. Enable `data.aurora`
2. Choose engine (postgres/mysql) and ACU range
3. Factory provisions cluster and injects connection info via secrets
4. Services consume secrets at runtime

---

## 13. Security & operational posture (minimum bar)
- Least privilege IAM per service
- Secrets never committed; environment variables injected via SSM/Secrets Manager
- Auth per route (REST) and per API/resolver strategy (AppSync)
- Basic logging always; enhanced alarms/tracing in Scalable
- Documentation includes “when to choose Lambda vs App Runner” and “when to choose DynamoDB vs Aurora”

---

## 14. v1 delivery roadmap (suggested)
### Phase 1 — Core framework
- Config models + defaults engine
- CLI: init/validate/synth/deploy
- Base stack + tagging + outputs

### Phase 2 — REST lane
- API Gateway REST + Lambda integration (per-route mapping)
- Auth: none + IAM + API keys + Cognito

### Phase 3 — App Runner lane
- Docker asset build + App Runner service
- Health checks + autoscaling defaults

### Phase 4 — AppSync lane
- GraphQL schema deployment
- Lambda resolvers + API key/IAM/Cognito auth options

### Phase 5 — Data lane
- DynamoDB + S3 modules
- Aurora Serverless v2 module + secrets integration

### Phase 6 — LLM compatibility assistant
- Patch generation, redaction, deterministic prompts
- “explain changes” report + guardrails

---

## 15. Success metrics (practical)
- A new user can deploy a working REST API in < 15 minutes
- Minimal config required for “hello world”
- Clear module boundaries and escape hatches
- Zero-secrets-in-repo checks by default
- CI passes on first clone: lint + tests + synth
