# Phase 2 Component Breakdown: GraphQL, Data Services & AI Assistant

## Phase Overview

**Objective**: Add GraphQL capabilities, data layer options (DynamoDB, Aurora, S3), enhanced observability for Scalable profile, and the LLM compatibility assistant for adapter generation.

**Deliverables**: 
- AppSync GraphQL API construct with schema deployment
- GraphQL resolver integrations (Lambda, DynamoDB)
- Complete data layer modules (DynamoDB, Aurora Serverless v2, S3)
- Secrets management abstraction (SSM vs Secrets Manager)
- Enhanced observability module (alarms, dashboards, tracing)
- LLM compatibility assistant for generating adapter code
- Comprehensive examples and production deployment guide

**Dependencies**: 
- Phase 1 must be complete and all acceptance criteria met
- All Phase 1 constructs and infrastructure working
- Configuration system extensible for Phase 2 modules
- CDK base stack architecture supports new constructs
- OpenAI API key available for LLM assistant testing (Human prerequisite)

## Phase Goals

- Users can deploy AppSync GraphQL APIs with Lambda resolvers
- Users can create DynamoDB tables with proper IAM permissions
- Users can provision Aurora Serverless v2 clusters with connection secrets
- Users can create S3 buckets with appropriate policies
- Secrets abstraction works across SSM and Secrets Manager
- Enhanced observability (alarms, dashboards) functional in Scalable profile
- LLM assistant generates valid adapter code from user business logic
- All Phase 1 functionality continues to work (no regressions)
- Production deployment guide enables enterprise adoption

---

## Components

### Component 2.1: AppSync GraphQL Construct with Schema Deployment

**Phase**: Phase 2 - GraphQL, Data Services & AI Assistant

**Priority**: Must-have

**Estimated Effort**: 7-8 hours

**Owner**: AI Agent

**Dependencies**:
- Phase 1 complete (CDK base stack, configuration system)
- Component 1.2: Configuration system must support GraphQL config

**Features**:
- AppSync GraphQL API creation and deployment (AI Agent)
- GraphQL schema file loading and validation (AI Agent)
- API key, IAM, and Cognito authorization modes (AI Agent)
- CloudWatch logging configuration (AI Agent)
- API endpoint output registration (AI Agent)

**Description**:
Implement the AppSync GraphQL construct that creates AWS AppSync APIs, deploys GraphQL schemas from files, and configures authorization modes (API key, IAM, Cognito). Support profile-based defaults for logging and observability, enable CloudWatch logs, and register API endpoints as stack outputs.

**Acceptance Criteria**:
- [ ] AppSync GraphQL API created with custom name from config
- [ ] GraphQL schema loaded from file path in config
- [ ] API key authorization mode works with usage limits
- [ ] IAM authorization mode works with SigV4
- [ ] Cognito authorization mode works with User Pool
- [ ] CloudWatch logs enabled for GraphQL queries/mutations
- [ ] API endpoint URL registered as output
- [ ] Profile defaults applied (Minimal vs Scalable logging)
- [ ] Integration test: deploy GraphQL API and execute test query
- [ ] Unit tests for construct creation and configuration

**Technical Details**:
- **Files to Create/Modify**:
  - `src/aws_api_factory/constructs/appsync/__init__.py`
  - `src/aws_api_factory/constructs/appsync/api.py`
  - `src/aws_api_factory/constructs/appsync/schema.py`
  - `starter/src/graphql/schema.graphql`
  - `tests/constructs/test_appsync.py`
  - `tests/integration/test_graphql_e2e.py`
- **Key Functions/Classes**:
  - `AppSyncConstruct(BaseConstruct)` - creates AppSync API
  - `load_graphql_schema(path)` - reads and validates schema file
  - `configure_auth_mode()` - sets up authorization
  - `create_cloudwatch_role()` - IAM for AppSync logging
- **Human/AI Agent**: All implementation by AI Agent
- **Database Changes**: N/A
- **API Endpoints**: GraphQL endpoint at configured path
- **Dependencies**: `aws-cdk-lib` (appsync, iam, logs modules)

**Detailed Implementation Requirements**:
- **File: `src/aws_api_factory/constructs/appsync/api.py`**: Implement `AppSyncConstruct` that: 1) creates AppSync GraphQL API with name from config, 2) loads schema from file path using schema loader, 3) configures authorization based on config (api_key, iam, cognito), 4) enables CloudWatch logging with IAM role, 5) applies profile defaults (Minimal: basic logging; Scalable: field-level logging, X-Ray tracing), 6) registers GraphQL endpoint as output, 7) handles multiple authorization modes if configured. Support additional authorization modes beyond primary. Set up WAF integration if Scalable profile and configured.
- **File: `src/aws_api_factory/constructs/appsync/schema.py`**: Implement schema utilities: `load_graphql_schema(path)` reads GraphQL schema file and validates syntax, `validate_schema_resolvers(schema, resolvers_config)` ensures configured resolvers match schema types/fields, `merge_schema_files(paths)` combines multiple schema files if needed. Use graphql-core or similar for validation. Handle missing files gracefully with clear errors.
- **File: `starter/src/graphql/schema.graphql`**: Create example GraphQL schema: type Query with simple queries (getItem, listItems), type Mutation with basic mutations (createItem, updateItem, deleteItem), type Item with id, name, description fields, proper scalar types. Include comments explaining schema structure. Keep production-ready and extensible.
- **File: `tests/constructs/test_appsync.py`**: Unit tests for AppSyncConstruct: verify API created with correct name, schema loaded successfully, authorization modes configured correctly, CloudWatch logging enabled, IAM role has correct permissions, profile-specific settings applied (Minimal vs Scalable), multiple auth modes supported. Use CDK assertions to verify CloudFormation properties. Mock schema file loading.
- **File: `tests/integration/test_graphql_e2e.py`**: Integration test that: 1) creates factory.yaml with GraphQL API config, 2) synthesizes stack, 3) validates CloudFormation includes AppSync API and schema, 4) optionally deploys to test AWS account, 5) executes test GraphQL query, 6) verifies response structure, 7) cleans up resources. Mark as integration/slow test.

**Test Requirements**:
- [ ] Unit tests for AppSync construct with various auth modes
- [ ] Unit tests for schema loading and validation
- [ ] Integration test: synthesize stack with GraphQL API
- [ ] Integration test: deploy and execute GraphQL query (optional, slow)
- [ ] Manual test: deploy GraphQL API and test with GraphQL client
- [ ] Verify CloudWatch logs appear for GraphQL operations
- [ ] Test multiple authorization modes work correctly

**Definition of Done**:
- [ ] AppSync construct implemented and tested
- [ ] Schema loading and validation working
- [ ] All authorization modes functional
- [ ] CloudWatch logging enabled
- [ ] Profile defaults applied correctly
- [ ] All unit tests passing
- [ ] Integration test synthesizes valid CloudFormation
- [ ] Example schema works end-to-end
- [ ] Component Overview documentation created
- [ ] Phase Component Overview documentation created
- [ ] User documentation: GraphQL guide created

**Notes**:
- AppSync supports multiple authorization modes; document when to use each
- Schema-first approach requires resolvers to match schema exactly
- Consider adding schema introspection endpoint for development
- Document GraphQL best practices in user guide
- AppSync has built-in caching; document configuration options

---

### Component 2.2: GraphQL Resolver Integrations (Lambda, DynamoDB)

**Phase**: Phase 2 - GraphQL, Data Services & AI Assistant

**Priority**: Must-have

**Estimated Effort**: 8 hours

**Owner**: AI Agent

**Dependencies**:
- Component 2.1: AppSync construct must exist
- Component 1.6: Lambda construct must exist
- Component 2.3: DynamoDB module (can develop in parallel, integration after)

**Features**:
- Lambda resolver creation and attachment (AI Agent)
- DynamoDB direct resolver configuration (AI Agent)
- VTL (Velocity Template Language) templates for DynamoDB (AI Agent)
- Request/response mapping templates (AI Agent)
- IAM permissions for resolver access (AI Agent)

**Description**:
Implement GraphQL resolver integrations that connect AppSync schema fields to Lambda functions or DynamoDB tables. Support Lambda resolvers for complex business logic and direct DynamoDB resolvers for simple CRUD operations. Generate VTL templates for DynamoDB operations and handle IAM permissions.

**Acceptance Criteria**:
- [ ] Lambda resolvers created and attached to schema fields
- [ ] DynamoDB direct resolvers configured with VTL templates
- [ ] Request mapping templates transform GraphQL input correctly
- [ ] Response mapping templates format data for GraphQL output
- [ ] IAM permissions grant AppSync access to Lambda/DynamoDB
- [ ] Pipeline resolvers supported for complex queries
- [ ] Batch operations supported for list queries
- [ ] Integration test: invoke Lambda resolver successfully
- [ ] Integration test: query DynamoDB directly via AppSync
- [ ] Unit tests for resolver configuration

**Technical Details**:
- **Files to Create/Modify**:
  - `src/aws_api_factory/constructs/appsync/resolvers.py`
  - `src/aws_api_factory/constructs/appsync/lambda_resolver.py`
  - `src/aws_api_factory/constructs/appsync/dynamodb_resolver.py`
  - `src/aws_api_factory/constructs/appsync/vtl_templates.py`
  - `starter/src/services/graphql/resolvers.py`
  - `tests/constructs/test_appsync_resolvers.py`
  - `tests/integration/test_graphql_resolvers_e2e.py`
- **Key Functions/Classes**:
  - `LambdaResolverConstruct` - creates Lambda data source and resolver
  - `DynamoDbResolverConstruct` - creates DynamoDB data source and resolver
  - `generate_vtl_template()` - creates VTL for DynamoDB operations
  - `attach_resolver_to_field()` - connects resolver to schema field
- **Human/AI Agent**: All implementation by AI Agent
- **Database Changes**: N/A (uses constructs from other components)
- **API Endpoints**: GraphQL fields resolved by Lambda/DynamoDB
- **Dependencies**: `aws-cdk-lib` (appsync, lambda, dynamodb, iam modules)

**Detailed Implementation Requirements**:
- **File: `src/aws_api_factory/constructs/appsync/lambda_resolver.py`**: Implement `LambdaResolverConstruct` that: 1) creates Lambda data source for AppSync API, 2) creates resolver attached to schema type/field from config, 3) sets up IAM role allowing AppSync to invoke Lambda, 4) configures request/response mapping templates if needed, 5) supports pipeline resolvers with multiple functions, 6) handles error mapping and retry logic. Allow custom mapping templates via config escape hatch.
- **File: `src/aws_api_factory/constructs/appsync/dynamodb_resolver.py`**: Implement `DynamoDbResolverConstruct` that: 1) creates DynamoDB data source for AppSync API, 2) generates VTL templates for CRUD operations (GetItem, Query, PutItem, UpdateItem, DeleteItem), 3) creates resolver with VTL templates, 4) sets up IAM role allowing AppSync to access DynamoDB, 5) supports batch operations (BatchGetItem), 6) handles pagination for list queries. Provide sensible VTL defaults but allow customization.
- **File: `src/aws_api_factory/constructs/appsync/vtl_templates.py`**: Implement VTL template generators: `generate_get_item_template(key_schema)` for single item queries, `generate_query_template(key_schema, index)` for list queries, `generate_put_item_template()` for creates, `generate_update_item_template()` for updates, `generate_delete_item_template(key_schema)` for deletes. Templates should handle GraphQL input correctly and format DynamoDB responses for GraphQL output. Include error handling in templates.
- **File: `src/aws_api_factory/constructs/appsync/resolvers.py`**: Implement resolver orchestration: `create_resolvers_from_config(api, schema, config)` iterates resolver config and creates appropriate resolver type (Lambda or DynamoDB), `validate_resolver_config(schema, resolvers)` ensures resolvers match schema, `attach_resolver_to_field(api, type_name, field_name, data_source, templates)` connects resolver to schema field. Support caching configuration per resolver.
- **File: `starter/src/services/graphql/resolvers.py`**: Create example Lambda resolver functions: `def resolve_get_item(event, context): return {"id": event["arguments"]["id"], "name": "Example Item"}`, `def resolve_list_items(event, context): return [{"id": "1", "name": "Item 1"}]`, `def resolve_create_item(event, context): # handle create logic`. Show proper event structure handling and error responses. Include docstrings explaining AppSync event format.
- **File: `tests/constructs/test_appsync_resolvers.py`**: Unit tests for resolvers: verify Lambda resolver created with correct configuration, verify DynamoDB resolver with VTL templates, verify IAM permissions correct, verify pipeline resolvers configured, test VTL template generation for each CRUD operation, verify error handling in templates. Use CDK assertions for CloudFormation verification.
- **File: `tests/integration/test_graphql_resolvers_e2e.py`**: Integration tests: 1) deploy GraphQL API with Lambda resolver, execute query via GraphQL endpoint, verify Lambda invoked and response correct, 2) deploy GraphQL API with DynamoDB resolver, execute mutation to create item, query item back, verify DynamoDB operations. Mark as integration/slow tests.

**Test Requirements**:
- [ ] Unit tests for Lambda resolver creation
- [ ] Unit tests for DynamoDB resolver with VTL templates
- [ ] Unit tests for VTL template generation (all CRUD operations)
- [ ] Integration test: Lambda resolver invoked via GraphQL
- [ ] Integration test: DynamoDB resolver CRUD operations
- [ ] Manual test: execute various GraphQL queries/mutations
- [ ] Verify IAM permissions are least-privilege
- [ ] Test error handling in resolvers

**Definition of Done**:
- [ ] Lambda resolver integration implemented and tested
- [ ] DynamoDB resolver integration implemented and tested
- [ ] VTL templates generated correctly
- [ ] IAM permissions configured properly
- [ ] All unit tests passing
- [ ] Integration tests verify resolver functionality
- [ ] Example resolvers work end-to-end
- [ ] Component Overview documentation created
- [ ] Phase Component Overview documentation updated
- [ ] User documentation: Resolver guide created

**Notes**:
- VTL can be complex; provide good defaults and examples
- Document when to use Lambda vs DynamoDB resolvers
- Pipeline resolvers enable complex orchestration; show examples
- AppSync caching can significantly improve performance
- Consider adding resolver performance monitoring in Scalable profile

---

### Component 2.3: DynamoDB Module with Table Creation and IAM Permissions

**Phase**: Phase 2 - GraphQL, Data Services & AI Assistant

**Priority**: Must-have

**Estimated Effort**: 6-7 hours

**Owner**: AI Agent

**Dependencies**:
- Phase 1 complete (CDK base stack, configuration system)
- Component 1.2: Configuration system must support DynamoDB config

**Features**:
- DynamoDB table creation with key schema (AI Agent)
- Global Secondary Index (GSI) configuration (AI Agent)
- Point-in-time recovery for Scalable profile (AI Agent)
- CloudWatch alarms for throttling and errors (AI Agent)
- IAM permission grants for Lambda/AppSync access (AI Agent)

**Description**:
Implement the DynamoDB module that creates tables with proper key schemas (partition key, optional sort key), configures GSIs, enables point-in-time recovery for Scalable profile, sets up CloudWatch alarms, and provides IAM permission methods for Lambda and AppSync to access tables.

**Acceptance Criteria**:
- [ ] DynamoDB tables created with partition key (and optional sort key)
- [ ] GSIs created from configuration
- [ ] Billing mode set per profile (PAY_PER_REQUEST for both)
- [ ] Point-in-time recovery enabled for Scalable profile
- [ ] CloudWatch alarms created for throttling (Scalable)
- [ ] IAM permission methods grant appropriate access
- [ ] Table names follow naming conventions
- [ ] Table ARNs registered as outputs
- [ ] Integration test: create table and write/read item
- [ ] Unit tests for construct configuration

**Technical Details**:
- **Files to Create/Modify**:
  - `src/aws_api_factory/constructs/data/__init__.py`
  - `src/aws_api_factory/constructs/data/dynamodb.py`
  - `src/aws_api_factory/constructs/data/dynamodb_permissions.py`
  - `tests/constructs/test_dynamodb.py`
  - `tests/integration/test_dynamodb_e2e.py`
- **Key Functions/Classes**:
  - `DynamoDbConstruct(BaseConstruct)` - creates DynamoDB tables
  - `create_table()` - table creation with key schema
  - `create_gsi()` - Global Secondary Index creation
  - `grant_read_write()` - IAM permission helper
- **Human/AI Agent**: All implementation by AI Agent
- **Database Changes**: DynamoDB tables created in AWS
- **API Endpoints**: N/A
- **Dependencies**: `aws-cdk-lib` (dynamodb, iam, cloudwatch modules)

**Detailed Implementation Requirements**:
- **File: `src/aws_api_factory/constructs/data/dynamodb.py`**: Implement `DynamoDbConstruct` that: 1) iterates table configurations from config, 2) creates DynamoDB table with partition key (pk) and optional sort key (sk) from config, 3) sets billing mode to PAY_PER_REQUEST, 4) creates GSIs if configured (with projection types), 5) enables point-in-time recovery if Scalable profile, 6) enables deletion protection if Scalable profile, 7) configures TTL if specified, 8) sets up CloudWatch alarms for read/write throttles (Scalable only), 9) applies table-level encryption (AWS managed keys), 10) registers table name and ARN as outputs. Support stream configuration (NEW_AND_OLD_IMAGES) if needed.
- **File: `src/aws_api_factory/constructs/data/dynamodb_permissions.py`**: Implement IAM permission helpers: `grant_read_data(table, grantee)` grants GetItem and Query permissions, `grant_write_data(table, grantee)` grants PutItem, UpdateItem, DeleteItem permissions, `grant_read_write_data(table, grantee)` grants all data plane operations, `grant_stream_read(table, grantee)` grants stream read permissions if enabled. Methods should work with Lambda functions, AppSync data sources, and IAM roles. Use least-privilege permissions.
- **File: `tests/constructs/test_dynamodb.py`**: Unit tests for DynamoDB construct: verify table created with correct key schema, verify GSIs configured properly, verify point-in-time recovery enabled in Scalable, verify CloudWatch alarms created in Scalable, verify billing mode set correctly, verify IAM permission methods grant correct policies, test table naming follows conventions. Use CDK assertions for CloudFormation verification. Test both Minimal and Scalable profiles.
- **File: `tests/integration/test_dynamodb_e2e.py`**: Integration test that: 1) creates factory.yaml with DynamoDB table config, 2) synthesizes stack, 3) validates CloudFormation includes DynamoDB table, 4) optionally deploys to test AWS account, 5) writes item to table using boto3, 6) reads item back, 7) verifies GSI query works, 8) cleans up resources. Mark as integration/slow test.

**Test Requirements**:
- [ ] Unit tests for table creation with various key schemas
- [ ] Unit tests for GSI configuration
- [ ] Unit tests for profile-specific features (PITR, alarms)
- [ ] Unit tests for IAM permission grant methods
- [ ] Integration test: synthesize stack with DynamoDB tables
- [ ] Integration test: deploy and perform CRUD operations (optional, slow)
- [ ] Manual test: verify table created in AWS console
- [ ] Manual test: verify CloudWatch alarms configured correctly

**Definition of Done**:
- [ ] DynamoDB construct implemented and tested
- [ ] Table creation with key schema working
- [ ] GSI support functional
- [ ] Profile-specific features applied correctly
- [ ] IAM permission helpers working
- [ ] All unit tests passing
- [ ] Integration test synthesizes valid CloudFormation
- [ ] CloudWatch alarms functional (Scalable)
- [ ] Component Overview documentation created
- [ ] Phase Component Overview documentation updated
- [ ] User documentation: DynamoDB guide created

**Notes**:
- PAY_PER_REQUEST billing is simpler for most use cases
- GSIs are powerful but add cost; document when to use them
- Point-in-time recovery adds cost but provides data protection
- DynamoDB streams enable event-driven architectures
- Consider documenting DynamoDB best practices (single table design, etc.)

---

### Component 2.4: Aurora Serverless v2 Module with Secrets Integration

**Phase**: Phase 2 - GraphQL, Data Services & AI Assistant

**Priority**: Must-have

**Estimated Effort**: 8 hours

**Owner**: AI Agent

**Dependencies**:
- Phase 1 complete (CDK base stack, configuration system)
- Component 2.6: Secrets management (can develop in parallel, integrate after)
- Component 1.2: Configuration system must support Aurora config

**Features**:
- Aurora Serverless v2 cluster creation (AI Agent)
- PostgreSQL and MySQL engine support (AI Agent)
- VPC and security group configuration (AI Agent)
- Master credentials in Secrets Manager (AI Agent)
- Database initialization (optional) (AI Agent)
- Connection info injection to Lambda (AI Agent)

**Description**:
Implement the Aurora Serverless v2 module that creates RDS clusters with auto-scaling capabilities, supports PostgreSQL and MySQL engines, configures VPC networking and security groups, stores master credentials in Secrets Manager, and injects connection information into Lambda functions via environment variables.

**Acceptance Criteria**:
- [ ] Aurora Serverless v2 cluster created with configured engine
- [ ] VPC, subnets, and security groups configured properly
- [ ] Master credentials generated and stored in Secrets Manager
- [ ] ACU (Aurora Capacity Units) min/max configured per profile
- [ ] Database name created if specified in config
- [ ] Connection secret available to Lambda functions
- [ ] Security group allows Lambda access
- [ ] Backup retention configured per profile
- [ ] Cluster endpoint registered as output
- [ ] Integration test: deploy cluster and connect from Lambda
- [ ] Unit tests for construct configuration

**Technical Details**:
- **Files to Create/Modify**:
  - `src/aws_api_factory/constructs/data/aurora.py`
  - `src/aws_api_factory/constructs/data/vpc.py`
  - `src/aws_api_factory/constructs/data/aurora_permissions.py`
  - `tests/constructs/test_aurora.py`
  - `tests/integration/test_aurora_e2e.py`
  - `starter/src/services/db_example/handler.py`
- **Key Functions/Classes**:
  - `AuroraConstruct(BaseConstruct)` - creates Aurora cluster
  - `create_vpc_for_rds()` - VPC and subnet configuration
  - `create_security_group()` - security group for RDS
  - `inject_connection_info()` - adds secrets to Lambda
- **Human/AI Agent**: All implementation by AI Agent
- **Database Changes**: Aurora cluster created in AWS
- **API Endpoints**: N/A
- **Dependencies**: `aws-cdk-lib` (rds, ec2, secretsmanager, iam modules)

**Detailed Implementation Requirements**:
- **File: `src/aws_api_factory/constructs/data/aurora.py`**: Implement `AuroraConstruct` that: 1) creates or imports VPC (default: create new VPC with private subnets), 2) creates DB subnet group with private subnets, 3) creates security group allowing ingress from Lambda security group, 4) generates master credentials (username: admin, random password), 5) stores credentials in Secrets Manager, 6) creates Aurora Serverless v2 cluster with engine from config (postgres15 or mysql8.0), 7) configures scaling (Minimal: min=0.5 max=2 ACU, Scalable: min=1 max=8 ACU), 8) creates database instance in cluster, 9) optionally creates initial database with name from config, 10) configures backup retention (Minimal: 7 days, Scalable: 30 days), 11) enables deletion protection if Scalable, 12) registers cluster endpoint and secret ARN as outputs. Support importing existing VPC via config.
- **File: `src/aws_api_factory/constructs/data/vpc.py`**: Implement VPC utilities: `create_vpc_for_rds()` creates VPC with private subnets (2 AZs minimum for RDS), NAT gateways for Lambda access to internet, VPC endpoints for AWS services (reduce NAT costs), proper CIDR allocation. `get_or_create_vpc(config)` checks if VPC ID provided in config, imports if exists, creates if not. Keep VPC configuration simple and cost-effective.
- **File: `src/aws_api_factory/constructs/data/aurora_permissions.py`**: Implement permission helpers: `grant_connect(cluster, lambda_function)` adds security group rules and secret read permissions to Lambda, `inject_connection_secret(lambda_function, secret)` adds secret ARN as environment variable, `create_rds_proxy()` (optional, for connection pooling - document as future enhancement). Ensure Lambda can read secret and connect to RDS.
- **File: `tests/constructs/test_aurora.py`**: Unit tests for Aurora construct: verify cluster created with correct engine, verify VPC and subnets configured, verify security groups allow Lambda access, verify secret created with master credentials, verify scaling configuration per profile, verify backup retention per profile, verify deletion protection in Scalable. Use CDK assertions for CloudFormation verification. Test both PostgreSQL and MySQL engines.
- **File: `tests/integration/test_aurora_e2e.py`**: Integration test that: 1) creates factory.yaml with Aurora config, 2) synthesizes stack, 3) validates CloudFormation includes Aurora cluster, VPC, security groups, secrets, 4) optionally deploys (slow, expensive test), 5) creates Lambda that reads secret and connects to RDS, 6) executes query, 7) cleans up resources. Mark as integration/slow/expensive test. Consider using Aurora Serverless v1 or smaller instance for testing to reduce costs.
- **File: `starter/src/services/db_example/handler.py`**: Create example Lambda handler that: 1) reads RDS connection secret from environment variable, 2) parses secret JSON (host, port, username, password, dbname), 3) connects to database using psycopg2 (PostgreSQL) or pymysql (MySQL), 4) executes simple query (SELECT 1), 5) returns result, 6) handles connection errors gracefully. Include docstring explaining secret structure and connection pattern. Document connection pooling best practices.

**Test Requirements**:
- [ ] Unit tests for Aurora cluster creation
- [ ] Unit tests for VPC and security group configuration
- [ ] Unit tests for secrets integration
- [ ] Unit tests for profile-specific configurations
- [ ] Integration test: synthesize stack with Aurora cluster
- [ ] Integration test: deploy and connect from Lambda (optional, slow, expensive)
- [ ] Manual test: verify cluster in RDS console
- [ ] Manual test: connect to database and execute queries
- [ ] Manual test: verify scaling behavior under load

**Definition of Done**:
- [ ] Aurora construct implemented and tested
- [ ] VPC networking configured properly
- [ ] Secrets integration working
- [ ] Lambda can connect to RDS successfully
- [ ] Profile-specific settings applied
- [ ] All unit tests passing
- [ ] Integration test synthesizes valid CloudFormation
- [ ] Example Lambda handler works
- [ ] Component Overview documentation created
- [ ] Phase Component Overview documentation updated
- [ ] User documentation: Aurora guide created
- [ ] Cost implications documented

**Notes**:
- Aurora Serverless v2 has minimum cost even at 0.5 ACU; document clearly
- Cold starts (scaling from 0) can take 15-30 seconds
- VPC networking adds complexity; provide clear diagrams in docs
- Connection pooling (RDS Proxy) recommended for Lambda; document pattern
- Document when to choose DynamoDB vs Aurora (cost, query patterns, transactions)
- Aurora is expensive compared to DynamoDB; warn users about costs

---

### Component 2.5: S3 Module for File Storage

**Phase**: Phase 2 - GraphQL, Data Services & AI Assistant

**Priority**: Must-have

**Estimated Effort**: 4-5 hours

**Owner**: AI Agent

**Dependencies**:
- Phase 1 complete (CDK base stack, configuration system)
- Component 1.2: Configuration system must support S3 config

**Features**:
- S3 bucket creation with naming conventions (AI Agent)
- Versioning and lifecycle policies per profile (AI Agent)
- Encryption at rest (AWS managed keys) (AI Agent)
- CORS configuration for web uploads (AI Agent)
- IAM permission grants for Lambda/AppSync (AI Agent)
- Presigned URL generation helper (AI Agent)

**Description**:
Implement the S3 module that creates buckets for file storage, configures versioning and lifecycle policies based on profile, enables encryption, sets up CORS for web uploads, and provides IAM permission helpers and presigned URL utilities for secure file access.

**Acceptance Criteria**:
- [ ] S3 buckets created with proper naming conventions
- [ ] Server-side encryption enabled (AWS managed keys)
- [ ] Versioning enabled for Scalable profile
- [ ] Lifecycle policies configured (e.g., transition to IA after 30 days)
- [ ] CORS configured if specified in config
- [ ] Public access blocked by default
- [ ] IAM permission helpers grant appropriate access
- [ ] Bucket ARNs and names registered as outputs
- [ ] Integration test: upload and download file via Lambda
- [ ] Unit tests for construct configuration

**Technical Details**:
- **Files to Create/Modify**:
  - `src/aws_api_factory/constructs/data/s3.py`
  - `src/aws_api_factory/constructs/data/s3_permissions.py`
  - `src/aws_api_factory/utils/s3_helpers.py`
  - `tests/constructs/test_s3.py`
  - `tests/integration/test_s3_e2e.py`
  - `starter/src/services/s3_example/handler.py`
- **Key Functions/Classes**:
  - `S3Construct(BaseConstruct)` - creates S3 buckets
  - `configure_lifecycle_rules()` - lifecycle policy setup
  - `grant_read_write()` - IAM permission helper
  - `generate_presigned_url()` - presigned URL utility
- **Human/AI Agent**: All implementation by AI Agent
- **Database Changes**: N/A
- **API Endpoints**: N/A (file access via presigned URLs)
- **Dependencies**: `aws-cdk-lib` (s3, iam modules)

**Detailed Implementation Requirements**:
- **File: `src/aws_api_factory/constructs/data/s3.py`**: Implement `S3Construct` that: 1) iterates bucket configurations from config, 2) creates S3 bucket with name following convention (project-env-bucket_name), 3) enables server-side encryption with AWS managed keys (AES256), 4) blocks all public access by default, 5) enables versioning if Scalable profile, 6) configures lifecycle rules if specified (e.g., transition to GLACIER after 90 days, expire after 365 days), 7) sets up CORS rules if configured (allow origins, methods, headers), 8) enables bucket logging if Scalable (log to separate logging bucket), 9) configures object lock if required (immutable objects), 10) registers bucket name and ARN as outputs. Support bucket policies via config escape hatch.
- **File: `src/aws_api_factory/constructs/data/s3_permissions.py`**: Implement IAM permission helpers: `grant_read(bucket, grantee)` grants s3:GetObject and s3:ListBucket permissions, `grant_write(bucket, grantee)` grants s3:PutObject and s3:DeleteObject permissions, `grant_read_write(bucket, grantee)` grants all data operations, `grant_public_read(bucket)` creates bucket policy allowing public read (use cautiously, warn user). Methods work with Lambda functions and IAM roles. Use resource-level permissions for least privilege.
- **File: `src/aws_api_factory/utils/s3_helpers.py`**: Implement utility functions for Lambda: `generate_presigned_url(bucket_name, key, expiration=3600, operation='get_object')` generates presigned URL for upload or download using boto3, `parse_s3_event(event)` extracts bucket and key from S3 event notification, `get_object_metadata(bucket_name, key)` retrieves object metadata. Include error handling for missing objects and permission issues. Document presigned URL security considerations.
- **File: `tests/constructs/test_s3.py`**: Unit tests for S3 construct: verify bucket created with encryption, verify versioning enabled in Scalable, verify lifecycle rules configured, verify CORS rules if specified, verify public access blocked by default, verify IAM permission methods grant correct policies, test bucket naming follows conventions. Use CDK assertions for CloudFormation verification. Test both Minimal and Scalable profiles.
- **File: `tests/integration/test_s3_e2e.py`**: Integration test that: 1) creates factory.yaml with S3 bucket config, 2) synthesizes stack, 3) validates CloudFormation includes S3 bucket, 4) optionally deploys to test AWS account, 5) uploads file to bucket using boto3, 6) generates presigned URL for download, 7) downloads file via presigned URL, 8) cleans up resources. Mark as integration/slow test.
- **File: `starter/src/services/s3_example/handler.py`**: Create example Lambda handler demonstrating S3 usage: `def upload_handler(event, context): # generate presigned URL for upload, return to client`, `def download_handler(event, context): # generate presigned URL for download`, `def process_s3_event(event, context): # handle S3 event notification`. Show proper use of s3_helpers utilities. Include docstrings explaining S3 event structure and presigned URL flow.

**Test Requirements**:
- [ ] Unit tests for S3 bucket creation
- [ ] Unit tests for lifecycle and CORS configuration
- [ ] Unit tests for IAM permission grant methods
- [ ] Unit tests for presigned URL generation
- [ ] Integration test: synthesize stack with S3 buckets
- [ ] Integration test: upload and download files (optional, slow)
- [ ] Manual test: verify bucket created in S3 console
- [ ] Manual test: test presigned URLs in browser
- [ ] Test CORS configuration with web application

**Definition of Done**:
- [ ] S3 construct implemented and tested
- [ ] Bucket configuration working (encryption, versioning, lifecycle)
- [ ] IAM permission helpers functional
- [ ] Presigned URL utilities working
- [ ] All unit tests passing
- [ ] Integration test synthesizes valid CloudFormation
- [ ] Example Lambda handlers work
- [ ] Component Overview documentation created
- [ ] Phase Component Overview documentation updated
- [ ] User documentation: S3 guide created

**Notes**:
- S3 is cost-effective for file storage but watch for request costs
- Presigned URLs are essential for secure direct browser uploads
- Document S3 event notifications for event-driven architectures
- Consider adding S3 Transfer Acceleration for global users (optional)
- Document when to use S3 vs DynamoDB for binary data

---

### Component 2.6: Secrets Management Abstraction (SSM vs Secrets Manager)

**Phase**: Phase 2 - GraphQL, Data Services & AI Assistant

**Priority**: Must-have

**Estimated Effort**: 5-6 hours

**Owner**: AI Agent

**Dependencies**:
- Phase 1 complete (CDK base stack, configuration system)
- Component 1.2: Configuration system must support secrets config

**Features**:
- SSM Parameter Store integration (AI Agent)
- AWS Secrets Manager integration (AI Agent)
- Unified API for both providers (AI Agent)
- Secret creation and rotation configuration (AI Agent)
- Lambda environment variable injection (AI Agent)
- Secret value retrieval utilities (AI Agent)

**Description**:
Implement a secrets management abstraction that supports both SSM Parameter Store (for simple config) and AWS Secrets Manager (for auto-rotation and complex secrets). Provide a unified API for creating secrets, injecting them into Lambda functions, and retrieving values at runtime. Support automatic rotation for RDS credentials.

**Acceptance Criteria**:
- [ ] SSM Parameter Store parameters created for simple secrets
- [ ] Secrets Manager secrets created for complex secrets
- [ ] Unified API abstracts provider differences
- [ ] Secret rotation configured for RDS credentials (Secrets Manager)
- [ ] Lambda functions can access secrets via environment variables
- [ ] Runtime utilities retrieve secret values efficiently
- [ ] IAM permissions grant appropriate secret access
- [ ] Secret ARNs registered as outputs
- [ ] Integration test: create secret and retrieve from Lambda
- [ ] Unit tests for both providers

**Technical Details**:
- **Files to Create/Modify**:
  - `src/aws_api_factory/constructs/secrets/__init__.py`
  - `src/aws_api_factory/constructs/secrets/manager.py`
  - `src/aws_api_factory/constructs/secrets/ssm.py`
  - `src/aws_api_factory/constructs/secrets/secrets_manager.py`
  - `src/aws_api_factory/utils/secrets.py`
  - `tests/constructs/test_secrets.py`
  - `tests/integration/test_secrets_e2e.py`
  - `starter/src/services/secrets_example/handler.py`
- **Key Functions/Classes**:
  - `SecretsManagerConstruct` - unified secrets interface
  - `SsmParameterProvider` - SSM implementation
  - `SecretsManagerProvider` - Secrets Manager implementation
  - `inject_secret()` - add secret to Lambda env
  - `get_secret_value()` - runtime retrieval utility
- **Human/AI Agent**: All implementation by AI Agent
- **Database Changes**: N/A
- **API Endpoints**: N/A
- **Dependencies**: `aws-cdk-lib` (ssm, secretsmanager, iam modules)

**Detailed Implementation Requirements**:
- **File: `src/aws_api_factory/constructs/secrets/manager.py`**: Implement `SecretsManagerConstruct` that: 1) determines provider based on config (ssm or secrets_manager), 2) provides unified interface: `create_secret(name, value)`, `grant_read(secret, grantee)`, `inject_into_lambda(secret, lambda_fn, env_var_name)`, 3) delegates to appropriate provider (SSM or Secrets Manager), 4) registers secret ARNs/names as outputs, 5) handles provider-specific features (rotation for Secrets Manager). Factory method pattern for provider selection.
- **File: `src/aws_api_factory/constructs/secrets/ssm.py`**: Implement `SsmParameterProvider` that: 1) creates SSM parameters with type=SecureString, 2) sets parameter tier (Standard for <4KB, Advanced for >4KB), 3) encrypts with AWS managed key, 4) grants read permissions (ssm:GetParameter, ssm:GetParameters), 5) injects parameter ARN into Lambda environment variables, 6) follows naming convention: /{project}/{env}/{secret_name}. Keep simple for config values.
- **File: `src/aws_api_factory/constructs/secrets/secrets_manager.py`**: Implement `SecretsManagerProvider` that: 1) creates Secrets Manager secrets with description from config, 2) generates secret value (random string) or accepts user-provided value, 3) configures automatic rotation if specified (e.g., 30 days for RDS), 4) sets up rotation Lambda if needed (for RDS, use AWS provided rotation), 5) grants read permissions (secretsmanager:GetSecretValue), 6) injects secret ARN into Lambda environment variables, 7) supports secret versioning and staging labels. Use for sensitive data like API keys, database passwords.
- **File: `src/aws_api_factory/utils/secrets.py`**: Implement runtime utilities for Lambda: `get_secret_value(secret_arn_or_name, cache=True)` retrieves secret from SSM or Secrets Manager with caching to reduce API calls and cold start impact, `parse_json_secret(secret_string)` parses JSON secrets (e.g., RDS credentials), `SecretCache` class for efficient secret caching across Lambda invocations. Use boto3 with proper error handling. Document caching strategy and cache invalidation.
- **File: `tests/constructs/test_secrets.py`**: Unit tests for secrets constructs: verify SSM parameter created correctly, verify Secrets Manager secret created correctly, verify unified API delegates to correct provider, verify IAM permissions granted properly, verify rotation configured for Secrets Manager, verify Lambda environment variable injection. Use CDK assertions for CloudFormation verification. Test both providers.
- **File: `tests/integration/test_secrets_e2e.py`**: Integration test that: 1) creates factory.yaml with secrets config (both SSM and Secrets Manager), 2) synthesizes stack, 3) validates CloudFormation includes parameters and secrets, 4) optionally deploys to test AWS account, 5) creates Lambda that retrieves secrets using utilities, 6) verifies secret values retrieved correctly, 7) tests caching behavior, 8) cleans up resources. Mark as integration/slow test.
- **File: `starter/src/services/secrets_example/handler.py`**: Create example Lambda handler: `def handler(event, context): api_key = get_secret_value(os.environ['API_KEY_SECRET']); db_creds = parse_json_secret(get_secret_value(os.environ['DB_SECRET'])); return {"status": "secrets loaded"}`. Show proper use of secret utilities with caching. Include error handling for missing secrets.

**Test Requirements**:
- [ ] Unit tests for SSM Parameter Store provider
- [ ] Unit tests for Secrets Manager provider
- [ ] Unit tests for unified secrets interface
- [ ] Unit tests for secret retrieval utilities
- [ ] Integration test: synthesize stack with secrets
- [ ] Integration test: retrieve secrets from Lambda (optional, slow)
- [ ] Manual test: verify secrets in AWS console
- [ ] Manual test: verify rotation works (Secrets Manager)
- [ ] Test caching reduces API calls

**Definition of Done**:
- [ ] Secrets management abstraction implemented
- [ ] Both SSM and Secrets Manager providers working
- [ ] Unified API functional
- [ ] Runtime utilities with caching working
- [ ] All unit tests passing
- [ ] Integration test synthesizes valid CloudFormation
- [ ] Example Lambda handler works
- [ ] Component Overview documentation created
- [ ] Phase Component Overview documentation updated
- [ ] User documentation: Secrets guide created

**Notes**:
- SSM Parameter Store is free (Standard tier) but limited to 4KB
- Secrets Manager costs $0.40/secret/month but includes rotation
- Document when to use each provider (cost vs features)
- Secret caching is critical for Lambda performance
- Consider adding secret validation at creation time
- Document rotation Lambda setup for custom secrets

---

### Component 2.7: Enhanced Observability Module (Alarms, Dashboards, Tracing)

**Phase**: Phase 2 - GraphQL, Data Services & AI Assistant

**Priority**: Must-have

**Estimated Effort**: 7-8 hours

**Owner**: AI Agent

**Dependencies**:
- Phase 1 complete (all constructs must exist for observability)
- All Phase 2 data constructs (for comprehensive monitoring)

**Features**:
- CloudWatch alarms for key metrics (AI Agent)
- CloudWatch dashboard creation (AI Agent)
- X-Ray tracing integration (AI Agent)
- Log insights queries (AI Agent)
- SNS topic for alarm notifications (AI Agent)
- Scalable profile comprehensive monitoring (AI Agent)

**Description**:
Implement the enhanced observability module that creates CloudWatch alarms for critical metrics (Lambda errors, API Gateway 5xx, DynamoDB throttles), builds unified dashboards showing system health, enables X-Ray tracing for distributed tracing, provides pre-built Log Insights queries, and sets up SNS notifications for alarms (Scalable profile only).

**Acceptance Criteria**:
- [ ] CloudWatch alarms created for Lambda errors and duration
- [ ] CloudWatch alarms created for API Gateway 4xx/5xx errors
- [ ] CloudWatch alarms created for DynamoDB throttles (if enabled)
- [ ] CloudWatch dashboard displays key metrics across all resources
- [ ] X-Ray tracing enabled for API Gateway and Lambda (Scalable)
- [ ] SNS topic created for alarm notifications (Scalable)
- [ ] Pre-built Log Insights queries available
- [ ] Alarm actions configured to notify SNS topic
- [ ] Dashboard URL registered as output
- [ ] Integration test: trigger alarm and verify notification
- [ ] Unit tests for observability configuration

**Technical Details**:
- **Files to Create/Modify**:
  - `src/aws_api_factory/constructs/observability/__init__.py`
  - `src/aws_api_factory/constructs/observability/alarms.py`
  - `src/aws_api_factory/constructs/observability/dashboard.py`
  - `src/aws_api_factory/constructs/observability/tracing.py`
  - `src/aws_api_factory/constructs/observability/log_insights.py`
  - `tests/constructs/test_observability.py`
  - `tests/integration/test_observability_e2e.py`
  - `docs/guides/observability.md`
- **Key Functions/Classes**:
  - `ObservabilityConstruct(BaseConstruct)` - main observability setup
  - `create_alarms()` - alarm creation for all resources
  - `create_dashboard()` - unified dashboard
  - `enable_xray()` - X-Ray tracing setup
  - `create_log_insights_queries()` - pre-built queries
- **Human/AI Agent**: All implementation by AI Agent
- **Database Changes**: N/A
- **API Endpoints**: N/A
- **Dependencies**: `aws-cdk-lib` (cloudwatch, sns, xray, logs modules)

**Detailed Implementation Requirements**:
- **File: `src/aws_api_factory/constructs/observability/alarms.py`**: Implement alarm creation: `create_lambda_alarms(function)` creates alarms for errors (>5 in 5 minutes), duration (>80% of timeout), throttles, `create_api_gateway_alarms(api)` creates alarms for 5xx errors (>5% of requests), 4xx errors (>20%), latency (p99 >3000ms), `create_dynamodb_alarms(table)` creates alarms for read/write throttles, consumed capacity (>80% provisioned), `create_aurora_alarms(cluster)` creates alarms for CPU (>80%), connections (>80% max), storage. Alarms only created in Scalable profile. Use appropriate thresholds and evaluation periods.
- **File: `src/aws_api_factory/constructs/observability/dashboard.py`**: Implement dashboard creation: `create_dashboard(resources)` creates CloudWatch dashboard with widgets for: Lambda metrics (invocations, errors, duration), API Gateway metrics (requests, latency, errors), DynamoDB metrics (consumed capacity, throttles), Aurora metrics (CPU, connections), overall system health. Use graph widgets for time series, number widgets for current values. Organize widgets logically by service. Dashboard updated as resources are added.
- **File: `src/aws_api_factory/constructs/observability/tracing.py`**: Implement X-Ray tracing: `enable_xray_for_lambda(function)` enables active tracing on Lambda, `enable_xray_for_api_gateway(api)` enables tracing on API stage, `create_xray_group(name, filter_expression)` creates X-Ray group for filtering traces. Tracing only enabled in Scalable profile. Add annotations to Lambda for custom trace metadata. Document how to view traces in X-Ray console.
- **File: `src/aws_api_factory/constructs/observability/log_insights.py`**: Implement Log Insights queries: `create_query_definition(name, log_groups, query_string)` creates saved query, provide pre-built queries: "Lambda Errors" (find all Lambda errors with stack traces), "API Gateway Slow Requests" (find requests >1000ms), "DynamoDB Throttles" (find throttled operations), "GraphQL Errors" (find GraphQL resolver errors). Queries automatically target correct log groups. Document query syntax for users to create custom queries.
- **File: `tests/constructs/test_observability.py`**: Unit tests for observability: verify alarms created for all resource types in Scalable, verify dashboard includes all metrics, verify X-Ray enabled in Scalable, verify SNS topic created and alarms configured to notify, verify Log Insights queries created, verify no observability resources in Minimal (just basic CloudWatch logs). Use CDK assertions for CloudFormation verification.
- **File: `tests/integration/test_observability_e2e.py`**: Integration test that: 1) deploys stack with Scalable profile, 2) triggers Lambda error (exceeds threshold), 3) waits for alarm to trigger, 4) verifies SNS notification sent (requires SNS subscription setup), 5) checks X-Ray traces appear, 6) executes Log Insights query and verifies results. Mark as integration/slow test. May require manual verification of some aspects.
- **File: `docs/guides/observability.md`**: Write comprehensive observability guide: 1) explain observability strategy (Minimal vs Scalable), 2) document all alarms and their thresholds, 3) show dashboard examples with screenshots, 4) explain X-Ray tracing and how to view traces, 5) provide Log Insights query examples and syntax guide, 6) document how to customize alarms and thresholds, 7) explain SNS notification setup, 8) provide troubleshooting runbook based on common alarms. Include best practices for monitoring production systems.

**Test Requirements**:
- [ ] Unit tests for alarm creation (all resource types)
- [ ] Unit tests for dashboard creation
- [ ] Unit tests for X-Ray tracing enablement
- [ ] Unit tests for Log Insights query creation
- [ ] Integration test: synthesize stack with observability
- [ ] Integration test: trigger alarm and verify (optional, slow)
- [ ] Manual test: view dashboard in CloudWatch console
- [ ] Manual test: generate traces and view in X-Ray
- [ ] Manual test: execute Log Insights queries

**Definition of Done**:
- [ ] Observability construct implemented and tested
- [ ] Alarms created for all resource types
- [ ] Dashboard displays key metrics
- [ ] X-Ray tracing enabled (Scalable)
- [ ] Log Insights queries functional
- [ ] All unit tests passing
- [ ] Integration test synthesizes valid CloudFormation
- [ ] Observability guide complete
- [ ] Component Overview documentation created
- [ ] Phase Component Overview documentation updated

**Notes**:
- CloudWatch costs increase with custom metrics and alarms; document costs
- X-Ray tracing adds latency (~1-2ms) but invaluable for debugging
- Log Insights queries can be expensive; encourage saved queries over ad-hoc
- SNS notifications require user to create subscription (email, SMS, etc.)
- Consider adding composite alarms for complex conditions
- Document alarm fatigue and how to tune thresholds

---

### Component 2.8: LLM Compatibility Assistant (OpenAI Integration, Patch Generation)

**Phase**: Phase 2 - GraphQL, Data Services & AI Assistant

**Priority**: Must-have

**Estimated Effort**: 8 hours

**Owner**: AI Agent

**Dependencies**:
- Phase 1 complete (CLI must exist)
- OpenAI API key available (Human prerequisite)

**Features**:
- OpenAI API integration using Responses API (AI Agent)
- Code scanning and analysis (AI Agent)
- Adapter code generation (AI Agent)
- Config suggestion generation (AI Agent)
- Unified diff patch output (AI Agent)
- Redaction filters for secrets (AI Agent)
- Explanation report generation (AI Agent)

**Description**:
Implement the LLM compatibility assistant that scans user business logic, generates factory-compatible adapter code, suggests factory.yaml configurations, produces unified diff patches for review, and provides explanation reports. Use OpenAI Responses API, implement redaction filters to prevent secret leakage, and never silently edit files.

**Acceptance Criteria**:
- [ ] `factory compat` command invokes LLM assistant
- [ ] User can select scope (files/directories to analyze)
- [ ] OpenAI API called with user business logic
- [ ] Adapter code generated matching factory conventions
- [ ] Config suggestions generated for factory.yaml
- [ ] Unified diff patch produced for review
- [ ] Explanation report describes suggested changes
- [ ] Redaction filters prevent secret leakage
- [ ] No files modified without user approval
- [ ] Graceful degradation if OpenAI unavailable
- [ ] Integration test: generate patch from sample code
- [ ] Unit tests for code analysis and patch generation

**Technical Details**:
- **Files to Create/Modify**:
  - `src/aws_api_factory/llm_assistant/__init__.py`
  - `src/aws_api_factory/llm_assistant/client.py`
  - `src/aws_api_factory/llm_assistant/scanner.py`
  - `src/aws_api_factory/llm_assistant/generator.py`
  - `src/aws_api_factory/llm_assistant/redactor.py`
  - `src/aws_api_factory/llm_assistant/patch.py`
  - `src/aws_api_factory/cli/commands/compat.py`
  - `tests/llm_assistant/test_compat.py`
  - `tests/integration/test_compat_e2e.py`
- **Key Functions/Classes**:
  - `OpenAIClient` - API client wrapper
  - `CodeScanner` - analyzes user code
  - `AdapterGenerator` - generates factory adapters
  - `Redactor` - filters sensitive data
  - `PatchGenerator` - creates unified diffs
- **Human/AI Agent**: All implementation by AI Agent
- **Database Changes**: N/A
- **API Endpoints**: Calls OpenAI Responses API
- **Dependencies**: `openai>=1.0.0`, `GitPython` (for diff generation)

**Detailed Implementation Requirements**:
- **File: `src/aws_api_factory/llm_assistant/client.py`**: Implement `OpenAIClient` that: 1) loads API key from environment variable (OPENAI_API_KEY) or Secrets Manager, 2) uses OpenAI Responses API (not deprecated Completions), 3) sends system prompt explaining factory conventions, 4) sends user code as context, 5) requests adapter code and config in structured format, 6) handles rate limiting and retries, 7) handles API errors gracefully (offline mode), 8) logs API usage for cost tracking. Use streaming for better UX if possible.
- **File: `src/aws_api_factory/llm_assistant/scanner.py`**: Implement `CodeScanner` that: 1) walks directory tree for Python files (default: src/services/**), 2) identifies functions that look like business logic (not named handler, no AWS SDK calls), 3) extracts function signatures and docstrings, 4) detects frameworks (FastAPI, Flask, Django) for appropriate adapter patterns, 5) identifies routes/paths from decorators, 6) builds structured representation of code for LLM. Respect .gitignore patterns. Skip large files (>100KB) with warning.
- **File: `src/aws_api_factory/llm_assistant/generator.py`**: Implement `AdapterGenerator` that: 1) takes LLM response and parses suggested adapters, 2) validates adapter code syntax (ast.parse), 3) ensures adapters match factory conventions (def handler(event, context) for Lambda), 4) generates factory.yaml snippets for new routes/services, 5) maps detected routes to Lambda or App Runner services, 6) suggests appropriate auth modes based on code patterns. Validate before returning to user.
- **File: `src/aws_api_factory/llm_assistant/redactor.py`**: Implement `Redactor` that: 1) scans code for patterns matching secrets (AWS keys, API tokens, passwords), 2) uses regex patterns for common secret formats, 3) redacts matched content with <REDACTED>, 4) scans file paths for sensitive directories (.env, secrets/), 5) redacts environment variables, 6) provides warning if potential secrets detected. Conservative approach: redact if uncertain.
- **File: `src/aws_api_factory/llm_assistant/patch.py`**: Implement `PatchGenerator` that: 1) creates unified diff format output, 2) shows file paths, line numbers, changes, 3) includes both adapter code additions and factory.yaml updates, 4) generates explanation section describing why changes suggested, 5) formats output for easy review and application, 6) provides commands to apply patch (git apply, manual copy). Use GitPython or manual diff generation.
- **File: `src/aws_api_factory/cli/commands/compat.py`**: Implement `factory compat` command that: 1) prompts user to select scope (directories to analyze), 2) scans code using CodeScanner, 3) applies redaction filters, 4) calls OpenAI API with redacted code, 5) generates adapters and config suggestions, 6) creates unified diff patch, 7) writes patch to file (compat.patch) and displays explanation, 8) prompts user to review and apply, 9) does NOT automatically apply changes. Add --dry-run flag to show what would be sent to API without calling it. Add --output flag for patch file location.
- **File: `tests/llm_assistant/test_compat.py`**: Unit tests for LLM assistant: test code scanning identifies correct files and functions, test redactor catches secrets and sensitive data, test adapter generation produces valid Python code, test patch generation creates valid unified diff, test OpenAI client handles errors gracefully, mock OpenAI API calls. Use sample code fixtures for testing.
- **File: `tests/integration/test_compat_e2e.py`**: Integration test that: 1) creates sample business logic files, 2) runs factory compat command, 3) verifies patch file generated, 4) validates patch contains expected adapters, 5) checks redaction worked (no secrets in patch), 6) optionally calls real OpenAI API (slow, costs money) to verify end-to-end. Mock OpenAI by default. Mark as integration test.

**Test Requirements**:
- [ ] Unit tests for code scanning
- [ ] Unit tests for redaction filters
- [ ] Unit tests for adapter generation
- [ ] Unit tests for patch generation
- [ ] Unit tests for OpenAI client (mocked)
- [ ] Integration test: full compat workflow with mock API
- [ ] Integration test: real OpenAI API call (optional, slow, costs)
- [ ] Manual test: run compat on sample project
- [ ] Manual test: apply generated patch and deploy
- [ ] Verify no secrets leaked in any test

**Definition of Done**:
- [ ] LLM assistant implemented and tested
- [ ] OpenAI integration working
- [ ] Code scanning and redaction functional
- [ ] Adapter generation produces valid code
- [ ] Patch generation creates reviewable diffs
- [ ] CLI command works end-to-end
- [ ] All unit tests passing (with mocked API)
- [ ] Integration test validates workflow
- [ ] Graceful degradation if API unavailable
- [ ] Component Overview documentation created
- [ ] Phase Component Overview documentation updated
- [ ] User documentation: LLM assistant guide created

**Notes**:
- OpenAI API costs money; document expected costs and token usage
- User must provide own API key; never commit keys
- LLM output is non-deterministic; always require human review
- Redaction is critical; err on side of over-redacting
- Consider adding local LLM support (Ollama, etc.) in future
- Document limitations: LLM may make mistakes, always review patches

---

### Component 2.9: Comprehensive Examples and Production Deployment Guide

**Phase**: Phase 2 - GraphQL, Data Services & AI Assistant

**Priority**: Must-have

**Estimated Effort**: 6-7 hours

**Owner**: AI Agent

**Dependencies**:
- All previous Phase 2 components (2.1-2.8) must be complete
- Phase 1 documentation must exist

**Features**:
- Complete GraphQL blog example (AI Agent)
- Multi-service architecture example (AI Agent)
- DynamoDB + AppSync example (AI Agent)
- Aurora + Lambda example (AI Agent)
- Production deployment checklist (AI Agent)
- Security hardening guide (AI Agent)
- Cost optimization guide (AI Agent)
- Migration guide from Phase 1 to Phase 2 (AI Agent)

**Description**:
Create comprehensive example projects demonstrating Phase 2 capabilities (GraphQL blog, multi-service architecture, data integrations) and production deployment guide covering security hardening, cost optimization, multi-environment strategies, CI/CD integration, and migration from Phase 1 projects.

**Acceptance Criteria**:
- [ ] GraphQL blog example deployable and functional
- [ ] Multi-service example shows REST + GraphQL + data
- [ ] DynamoDB + AppSync example demonstrates direct resolvers
- [ ] Aurora + Lambda example shows RDS connection patterns
- [ ] Production deployment guide covers all critical topics
- [ ] Security hardening checklist comprehensive
- [ ] Cost optimization strategies documented
- [ ] Migration guide tested with Phase 1 project
- [ ] All example projects have README with instructions
- [ ] Examples tested by deploying to AWS

**Technical Details**:
- **Files to Create/Modify**:
  - `starter/examples/graphql-blog/factory.yaml`
  - `starter/examples/graphql-blog/src/graphql/schema.graphql`
  - `starter/examples/graphql-blog/src/services/blog/resolvers.py`
  - `starter/examples/multi-service/factory.yaml`
  - `starter/examples/multi-service/README.md`
  - `docs/examples/graphql-blog.md`
  - `docs/examples/multi-service-architecture.md`
  - `docs/examples/dynamodb-appsync.md`
  - `docs/examples/aurora-lambda.md`
  - `docs/guides/production-deployment.md`
  - `docs/guides/security-hardening.md`
  - `docs/guides/cost-optimization.md`
  - `docs/guides/migration-phase1-to-phase2.md`
- **Key Functions/Classes**: N/A (examples and documentation)
- **Human/AI Agent**: All documentation by AI Agent; human reviews for clarity
- **Database Changes**: Example data models only
- **API Endpoints**: Example APIs only
- **Dependencies**: None beyond existing

**Detailed Implementation Requirements**:
- **File: `starter/examples/graphql-blog/factory.yaml`**: Create complete config for GraphQL blog: AppSync API, DynamoDB table for posts (pk: postId, gsi on authorId), DynamoDB table for comments (pk: commentId, gsi on postId), Lambda resolvers for complex queries (getPostWithComments), direct DynamoDB resolvers for simple CRUD, Cognito auth for mutations. Profile: scalable. Include all necessary config sections.
- **File: `starter/examples/graphql-blog/src/graphql/schema.graphql`**: Define blog schema: type Post (id, title, content, authorId, createdAt), type Comment (id, postId, content, authorId, createdAt), type Query (getPost, listPosts, getPostWithComments), type Mutation (createPost, updatePost, deletePost, createComment). Use proper GraphQL types and relationships.
- **File: `starter/examples/graphql-blog/src/services/blog/resolvers.py`**: Implement Lambda resolvers: `resolve_get_post_with_comments(event, context)` queries post from DynamoDB, queries comments by postId GSI, combines and returns, demonstrates batch fetching and N+1 prevention. Include proper error handling and logging.
- **File: `starter/examples/multi-service/factory.yaml`**: Create multi-service architecture config: REST API for public endpoints, GraphQL API for internal admin, Lambda services for business logic, App Runner service for background workers, DynamoDB for data, S3 for file storage, Aurora for transactional data, demonstrates how different components work together. Include comments explaining architecture decisions.
- **File: `docs/examples/graphql-blog.md`**: Write complete GraphQL blog tutorial: 1) architecture overview with diagram, 2) step-by-step deployment instructions, 3) sample GraphQL queries to test (createPost, getPost, listPosts, createComment, getPostWithComments), 4) explanation of resolver implementations, 5) how to add Cognito users for testing, 6) performance considerations (caching, batching), 7) how to extend with features (likes, tags, search). Include all code with explanations.
- **File: `docs/examples/multi-service-architecture.md`**: Document multi-service architecture: 1) explain why you'd use multiple APIs (public REST, internal GraphQL), 2) show how services communicate (via shared DynamoDB, S3), 3) demonstrate proper IAM boundary separation, 4) show how to use different auth modes (API key for REST, Cognito for GraphQL), 5) explain data consistency patterns, 6) show monitoring across services. Include architecture diagram and deployment instructions.
- **File: `docs/examples/dynamodb-appsync.md`**: Write DynamoDB + AppSync example: 1) explain when to use direct DynamoDB resolvers vs Lambda, 2) show VTL template patterns for CRUD operations, 3) demonstrate GSI queries and filtering, 4) show batch operations for list queries, 5) explain pagination patterns, 6) show error handling in VTL, 7) performance comparison vs Lambda resolvers. Include working example with deployment instructions.
- **File: `docs/examples/aurora-lambda.md`**: Write Aurora + Lambda example: 1) explain when to choose Aurora over DynamoDB, 2) show proper connection management in Lambda (use RDS Proxy if available), 3) demonstrate transaction patterns, 4) show how to handle connection pooling, 5) explain cold start implications, 6) show secret rotation handling, 7) demonstrate query patterns (SELECT, INSERT, UPDATE, JOIN). Include working example with cost considerations.
- **File: `docs/guides/production-deployment.md`**: Write comprehensive production deployment guide: 1) multi-environment strategy (dev, staging, prod), 2) CI/CD integration (GitHub Actions example), 3) deployment checklist (backups, monitoring, alarms, docs), 4) rollback procedures, 5) blue-green deployment patterns, 6) canary deployments with weighted routing, 7) disaster recovery planning, 8) incident response runbook, 9) on-call procedures, 10) SLA considerations. Make it enterprise-ready.
- **File: `docs/guides/security-hardening.md`**: Write security hardening guide: 1) checklist of security best practices (least privilege IAM, encryption at rest/transit, VPC isolation, WAF rules), 2) explain each AWS service's security features, 3) show how to enable GuardDuty for threat detection, 4) configure AWS Config for compliance, 5) set up CloudTrail for audit logging, 6) implement AWS Systems Manager Session Manager for secure access, 7) configure Security Hub for centralized security view, 8) explain secret rotation policies, 9) show how to conduct security reviews, 10) provide penetration testing guidelines. Include compliance mappings (SOC2, HIPAA, etc.).
- **File: `docs/guides/cost-optimization.md`**: Write cost optimization guide: 1) explain AWS pricing for each service (Lambda, API Gateway, DynamoDB, Aurora, S3, CloudWatch), 2) show how to set up billing alarms, 3) demonstrate cost allocation tags, 4) explain reserved capacity strategies, 5) show DynamoDB on-demand vs provisioned comparison, 6) explain Aurora Serverless v2 cost model and when it's worth it, 7) S3 lifecycle policies for cost savings, 8) CloudWatch Logs retention optimization, 9) Lambda memory tuning for cost/performance, 10) provide monthly cost estimation worksheet. Include real cost examples.
- **File: `docs/guides/migration-phase1-to-phase2.md`**: Write migration guide: 1) assess current Phase 1 deployment, 2) plan migration (which Phase 2 features to adopt), 3) step-by-step migration procedure (update config, add new constructs, test, deploy), 4) zero-downtime migration strategies, 5) rollback plan if migration fails, 6) data migration patterns (if adding Aurora to existing DynamoDB), 7) testing strategies for migrated system, 8) common migration pitfalls and solutions. Test guide with actual Phase 1 project migration.

**Test Requirements**:
- [ ] Deploy GraphQL blog example to AWS successfully
- [ ] Deploy multi-service example and verify all components work
- [ ] Test DynamoDB + AppSync example with sample queries
- [ ] Test Aurora + Lambda example with database operations
- [ ] Follow production deployment guide and verify completeness
- [ ] Follow security hardening checklist and verify all items
- [ ] Validate cost estimates with actual AWS deployments
- [ ] Test migration guide by migrating Phase 1 project to Phase 2
- [ ] Verify all example code is syntactically correct
- [ ] Have someone unfamiliar with project follow examples

**Definition of Done**:
- [ ] All example projects created and tested
- [ ] GraphQL blog example deployable
- [ ] Multi-service example demonstrates integration
- [ ] Data integration examples working
- [ ] Production deployment guide complete and tested
- [ ] Security hardening guide comprehensive
- [ ] Cost optimization guide practical
- [ ] Migration guide validated with real migration
- [ ] All documentation reviewed for clarity
- [ ] Examples deployed successfully to test account
- [ ] Component Overview documentation created
- [ ] Phase Component Overview documentation finalized

**Notes**:
- Examples should be production-ready, not toys
- Cost estimates should be based on real deployments
- Security guide should be reviewed by security expert if possible
- Migration guide critical for Phase 1 users to adopt Phase 2
- Consider adding video walkthroughs for complex examples
- Examples gallery in README should showcase Phase 2 capabilities

---

## Phase Acceptance Criteria

- [ ] Users can deploy AppSync GraphQL APIs with Lambda resolvers successfully
- [ ] Users can deploy AppSync GraphQL APIs with direct DynamoDB resolvers
- [ ] DynamoDB tables created with correct key schemas and IAM permissions
- [ ] Aurora Serverless v2 clusters provision successfully with connection secrets
- [ ] Lambda functions can connect to Aurora and execute queries
- [ ] S3 buckets created with appropriate policies and encryption
- [ ] Secrets abstraction works with both SSM and Secrets Manager
- [ ] Enhanced observability (alarms, dashboards, X-Ray) functional in Scalable profile
- [ ] `factory compat` generates valid adapter code from user business logic
- [ ] All Phase 1 functionality continues to work (no regressions)
- [ ] GraphQL blog example deploys and functions correctly
- [ ] Multi-service example demonstrates component integration
- [ ] Documentation enables new users to use all Phase 2 features
- [ ] All unit and integration tests pass with >85% coverage
- [ ] Zero secrets leaked in repository or LLM assistant output
- [ ] Production deployment guide enables enterprise adoption
- [ ] Security hardening guide comprehensive and actionable
- [ ] Cost optimization guide reduces deployment costs
- [ ] Migration guide successfully migrates Phase 1 projects

---

## Phase Dependencies

**Prerequisites (Human Setup Required)**:
- Phase 1 completely implemented and tested
- OpenAI API key available for LLM assistant (OPENAI_API_KEY environment variable)
- AWS service limits verified for Aurora, AppSync, DynamoDB in target regions
- VPC and networking knowledge for Aurora deployment

**Component Dependencies**:
- Component 2.1 depends on Phase 1 complete (base stack, config system)
- Component 2.2 depends on Component 2.1 (AppSync API must exist)
- Component 2.2 depends on Component 2.3 (DynamoDB for resolvers, can develop in parallel)
- Component 2.3 depends on Phase 1 complete
- Component 2.4 depends on Phase 1 complete and Component 2.6 (secrets)
- Component 2.5 depends on Phase 1 complete
- Component 2.6 depends on Phase 1 complete
- Component 2.7 depends on all Phase 1 and Phase 2 constructs (comprehensive monitoring)
- Component 2.8 depends on Phase 1 complete (CLI must exist)
- Component 2.9 depends on all previous Phase 2 components (examples cover everything)

**Parallel Development Opportunities**:
- Components 2.3, 2.5, 2.6 can be developed in parallel (independent data services)
- Components 2.1 and 2.3 can be developed in parallel (integrated later in 2.2)
- Component 2.8 can be developed in parallel with data components

---

## Phase Risks and Mitigation

### Risk 1: Aurora Serverless v2 Cold Starts
**Risk**: Aurora Serverless v2 scaling from 0 ACU takes 15-30 seconds, impacting user experience and causing Lambda timeouts
**Impact**: High - users may experience failed requests during cold starts
**Mitigation**:
- Document cold start behavior clearly with timing expectations
- Recommend min ACU of 0.5 or 1 to avoid complete shutdowns
- Provide warm-up strategies (scheduled Lambda to keep cluster warm)
- Suggest DynamoDB as alternative for latency-sensitive workloads
- Document RDS Proxy for connection pooling (reduces impact)

### Risk 2: LLM Assistant Generates Incorrect Code
**Risk**: LLM assistant generates invalid or insecure adapter code, leading to user frustration or security issues
**Impact**: Medium - users may lose trust in assistant or deploy vulnerable code
**Mitigation**:
- Always generate diffs, never direct edits (user must review and approve)
- Validate generated Python code with ast.parse before returning
- Include extensive testing with sample codebases to catch common errors
- Clear "review required" warnings in CLI output
- Graceful degradation if OpenAI unavailable (tool still works without assistant)
- Document limitations prominently: "LLM may make mistakes, always review"

### Risk 3: GraphQL Schema-First Conflicts
**Risk**: Schema-first approach for GraphQL conflicts with code-first resolver implementations, causing confusion
**Impact**: Medium - users may struggle to keep schema and resolvers in sync
**Mitigation**:
- Clear conventions for schema location and resolver naming
- Validation that resolvers match schema types/fields
- Examples showing best practices for schema/resolver organization
- Documentation explaining schema-first vs code-first tradeoffs
- Consider adding schema generation from code in future (escape hatch)

### Risk 4: OpenAI API Costs
**Risk**: OpenAI API costs become prohibitive for users or open-source project, limiting assistant adoption
**Impact**: Low - feature is optional but may limit usefulness
**Mitigation**:
- User brings own API key (project doesn't pay costs)
- Opt-in feature, not required for core functionality
- Document expected costs based on token usage (~$0.01-0.10 per generation)
- Consider caching LLM responses for repeated patterns
- Consider rate limiting or cost caps in future
- Document local LLM alternatives (Ollama, LLaMA) for future support

### Risk 5: VPC Networking Complexity
**Risk**: Aurora requires VPC setup, adding significant complexity that confuses users unfamiliar with AWS networking
**Impact**: Medium - users may struggle with VPC, subnets, security groups, NAT gateways
**Mitigation**:
- Provide sensible VPC defaults that work out-of-box
- Clear diagrams showing VPC architecture
- Document VPC costs (NAT gateways are expensive)
- Support importing existing VPCs for advanced users
- Troubleshooting guide for common networking issues
- Consider adding VPC-less alternatives (DynamoDB) as primary recommendation

### Risk 6: Phase 2 Complexity Overwhelms Users
**Risk**: Phase 2 adds so many features (GraphQL, DynamoDB, Aurora, S3, Secrets, Observability, LLM) that users are overwhelmed and don't know where to start
**Impact**: Medium - users may not adopt Phase 2 features or make poor architectural choices
**Mitigation**:
- Clear getting started path: start with Phase 1 REST API, add Phase 2 incrementally
- Decision trees and comparison guides (when to use DynamoDB vs Aurora, etc.)
- Progressive disclosure: basic features first, advanced features in separate guides
- Examples organized by complexity (simple → intermediate → advanced)
- Migration guide helps Phase 1 users adopt Phase 2 gradually
- Each feature has standalone guide, not monolithic documentation

---

## Phase Testing Strategy

### Unit Testing (Target: >85% coverage)
**Scope**: All Phase 2 constructs, LLM assistant logic, secret management, observability configuration

**Approach**:
- pytest for all Python tests
- Mock AWS CDK constructs for isolation
- Mock OpenAI API calls for LLM assistant tests
- Use fixtures for GraphQL schemas, DynamoDB tables, Aurora clusters
- Test VTL template generation extensively
- Test redaction filters comprehensively

**Tools**: pytest, pytest-cov, pytest-mock, CDK assertions library, moto (for AWS mocking)

### Integration Testing
**Scope**: CDK synthesis for Phase 2 stacks, multi-component workflows, LLM assistant end-to-end

**Approach**:
- Synthesize stacks with various Phase 2 configurations
- Validate CloudFormation includes all Phase 2 resources
- Test GraphQL schema loading and resolver attachment
- Test secrets injection into Lambda
- Test LLM assistant workflow with mock API
- Use temporary directories for file operations

**Tools**: pytest, tempfile, CDK synthesis API

### End-to-End Testing (Optional, Slow, Expensive)
**Scope**: Actual deployment to AWS test account, execute GraphQL queries, database operations, LLM generation

**Approach**:
- Deploy Phase 2 stack to isolated AWS account
- Execute GraphQL queries via AppSync endpoint
- Write/read items from DynamoDB
- Connect to Aurora from Lambda and execute queries
- Upload/download files from S3
- Trigger alarms and verify notifications
- Generate code with real OpenAI API (expensive)
- Clean up all resources after test

**Tools**: pytest, boto3, GraphQL client, psycopg2/pymysql, OpenAI SDK

### Manual Testing Checklist
- [ ] Follow GraphQL blog example step-by-step
- [ ] Deploy multi-service architecture and test all components
- [ ] Test all GraphQL resolver types (Lambda, DynamoDB)
- [ ] Connect to Aurora from Lambda and execute queries
- [ ] Upload files to S3 and generate presigned URLs
- [ ] Create secrets in SSM and Secrets Manager, retrieve from Lambda
- [ ] Trigger CloudWatch alarms and verify notifications
- [ ] View CloudWatch dashboard and verify metrics
- [ ] View X-Ray traces for GraphQL and Lambda operations
- [ ] Run `factory compat` on sample project and review patch
- [ ] Apply generated patch and verify deployment works
- [ ] Follow production deployment guide for one example
- [ ] Follow security hardening checklist and verify controls
- [ ] Estimate costs for each example project
- [ ] Migrate a Phase 1 project to Phase 2 using migration guide

---

## Phase Documentation Strategy

### Documentation Structure
```
docs/
  guides/
    graphql-api.md              # GraphQL concepts and usage (Component 2.1)
    graphql-resolvers.md        # Resolver patterns (Component 2.2)
    dynamodb.md                 # DynamoDB usage (Component 2.3)
    aurora.md                   # Aurora Serverless v2 (Component 2.4)
    s3-storage.md               # S3 file storage (Component 2.5)
    secrets-management.md       # Secrets abstraction (Component 2.6)
    observability.md            # Monitoring & alarms (Component 2.7)
    llm-assistant.md            # Compat command (Component 2.8)
    production-deployment.md    # Production guide (Component 2.9)
    security-hardening.md       # Security checklist (Component 2.9)
    cost-optimization.md        # Cost strategies (Component 2.9)
    migration-phase1-to-phase2.md # Migration guide (Component 2.9)
  examples/
    graphql-blog.md             # Complete blog tutorial (Component 2.9)
    multi-service-architecture.md # Multi-service example (Component 2.9)
    dynamodb-appsync.md         # Direct resolvers (Component 2.9)
    aurora-lambda.md            # RDS patterns (Component 2.9)
  reference/
    vtl-templates.md            # VTL reference for DynamoDB resolvers
    alarm-thresholds.md         # Observability alarm reference
```

### Developer Context Documentation
Each component creates:
- **Component Overview**: What was built, key decisions, usage examples
- **Phase Component Overview**: Updated with each component, tracks phase progress

### Documentation Quality Gates
- [ ] All code examples tested and working
- [ ] All GraphQL schemas valid
- [ ] All configuration examples validate successfully
- [ ] Architecture diagrams included where helpful
- [ ] Internal links verified (no broken links)
- [ ] Cost estimates validated with real deployments
- [ ] Security best practices reviewed
- [ ] Examples tested by deploying to AWS
- [ ] Migration guide tested with real Phase 1 project

---

## Phase Success Metrics

### Functional Metrics
- [ ] 100% of Phase 2 components completed and tested
- [ ] Unit test coverage >85% across all Phase 2 modules
- [ ] Integration tests synthesize valid CloudFormation for all scenarios
- [ ] Zero critical security findings from security scans
- [ ] Zero secrets leaked in repository, LLM output, or logs
- [ ] All GraphQL queries/mutations execute successfully
- [ ] All data integrations (DynamoDB, Aurora, S3) working
- [ ] LLM assistant generates valid code for sample projects

### User Experience Metrics
- [ ] New user deploys GraphQL API in <20 minutes
- [ ] LLM assistant patch generation completes in <60 seconds
- [ ] CloudWatch dashboard provides actionable insights
- [ ] Alarms trigger appropriately for error conditions
- [ ] Documentation enables self-service for all Phase 2 features
- [ ] Examples demonstrate real-world use cases

### Performance Metrics
- [ ] GraphQL queries complete in <500ms (p95)
- [ ] DynamoDB operations complete in <100ms (p95)
- [ ] Aurora connections established in <1000ms (cold) or <50ms (warm with RDS Proxy)
- [ ] S3 presigned URL generation in <100ms
- [ ] CloudWatch alarms trigger within 5 minutes of threshold breach
- [ ] LLM assistant code generation uses <10,000 tokens per request

### Cost Metrics (Typical Workloads)
- [ ] Minimal profile deployment costs <$50/month for low traffic
- [ ] Scalable profile deployment costs <$200/month for moderate traffic
- [ ] Aurora Serverless v2 costs documented and predictable
- [ ] Cost optimization guide reduces costs by 20-30% vs naive deployment
- [ ] Users can estimate costs before deploying

### Code Quality Metrics
- [ ] All code passes security scans (Bandit)
- [ ] All CloudFormation passes best practices (Checkov)
- [ ] No TODO or FIXME comments in production code
- [ ] All public APIs have comprehensive docstrings
- [ ] All complex logic has inline comments explaining why

---

## Post-Phase 2 Readiness Checklist

Before marking Phase 2 complete, verify:

**Functionality**:
- [ ] AppSync GraphQL APIs deploy and function correctly
- [ ] All resolver types (Lambda, DynamoDB) working
- [ ] DynamoDB tables created with proper schemas and permissions
- [ ] Aurora Serverless v2 clusters provision and accept connections
- [ ] S3 buckets created with encryption and lifecycle policies
- [ ] Secrets management works with both SSM and Secrets Manager
- [ ] Enhanced observability (alarms, dashboards, tracing) functional
- [ ] LLM assistant generates valid, reviewable patches
- [ ] All Phase 1 functionality still works (no regressions)

**Quality**:
- [ ] All tests passing (unit + integration)
- [ ] Test coverage >85% for Phase 2 code
- [ ] Code quality gates passing (lint, format, security scan)
- [ ] No known bugs or security vulnerabilities
- [ ] Documentation complete, accurate, and tested
- [ ] All example projects deploy successfully

**Operations**:
- [ ] CI/CD pipeline runs and passes for Phase 2 code
- [ ] CloudWatch alarms configured for all critical metrics
- [ ] Dashboards provide visibility into system health
- [ ] Runbooks exist for common operational issues
- [ ] Backup and restore procedures tested

**User Readiness**:
- [ ] GraphQL blog example validated by new user
- [ ] Multi-service example demonstrates integration correctly
- [ ] Production deployment guide enables enterprise deployment
- [ ] Security hardening checklist comprehensive and actionable
- [ ] Migration guide successfully migrates Phase 1 project
- [ ] Cost optimization guide reduces real deployment costs
- [ ] All documentation reviewed for clarity and accuracy

**Technical Debt**:
- [ ] No temporary workarounds or hacks
- [ ] No partial implementations or TODOs
- [ ] No commented-out code
- [ ] Architecture is extensible for future phases
- [ ] All escape hatches documented and tested

**Business Readiness**:
- [ ] Feature set competitive with alternatives (Serverless Framework, SAM)
- [ ] Documentation quality suitable for open-source adoption
- [ ] Examples showcase real-world use cases
- [ ] Project ready for public release and community contributions

---

## Notes and Recommendations

### Implementation Philosophy Reminder
**CRITICAL**: All code must be complete and production-ready. No placeholders, no "TODO" comments, and no partial implementations. Each component should be broken down small enough (2-8 hours) that it can be fully implemented in one focused session. It is better to deliver a smaller, fully working feature than a larger partially-implemented one.

### Component Execution Order
Suggested execution order:
1. **Components 2.3, 2.5, 2.6** (parallel) - Independent data services
2. **Component 2.1** - AppSync foundation
3. **Component 2.2** - GraphQL resolvers (depends on 2.1, 2.3)
4. **Component 2.4** - Aurora (depends on 2.6 for secrets)
5. **Component 2.7** - Observability (depends on all constructs)
6. **Component 2.8** - LLM assistant (parallel with others)
7. **Component 2.9** - Examples and guides (depends on all)

### Human vs AI Agent Split
- **Human Tasks**: OpenAI API key setup, AWS account configuration, reviewing documentation, testing deployments, cost validation
- **AI Agent Tasks**: All coding, testing, documentation writing, example creation

### Testing Philosophy
- Integration tests more valuable than heavy mocking for AWS services
- Real deployments catch configuration issues unit tests miss
- Aurora and OpenAI tests are expensive; mock by default, real tests optional
- Example projects are the ultimate integration test

### Documentation Philosophy
- Show, don't tell: examples > explanations
- Include cost information for every service
- Architecture diagrams for complex concepts (VPC, multi-service)
- Progressive disclosure: simple → intermediate → advanced
- Migration guides critical for adoption

### Performance Considerations
- Aurora cold starts are significant; document and provide mitigation
- DynamoDB is faster than Aurora for most use cases; recommend DynamoDB first
- X-Ray adds minimal latency but invaluable for debugging
- Lambda connection pooling critical for Aurora performance
- GraphQL N+1 queries can be expensive; document batching patterns

### Cost Considerations
- Aurora is most expensive service; warn users clearly
- NAT gateways for VPC add ongoing costs ($30-50/month)
- CloudWatch alarms and custom metrics add up quickly
- Secrets Manager costs $0.40/secret/month vs free SSM
- Document realistic monthly costs for each example

### Security Considerations
- Secrets never in code, logs, or LLM output
- Redaction filters in LLM assistant are critical
- VPC isolation for Aurora adds security but complexity
- IAM permissions must be least-privilege throughout
- Security hardening guide should be reviewed by expert

### Future Extensibility
- Phase 2 completes core platform
- Future phases might add: WebSocket APIs, EventBridge, Step Functions, SQS/SNS, custom domains, CDN, WAF rules
- Plugin architecture could enable community contributions
- Local development environment (LocalStack) for faster iteration

---

## Appendix: Component Summary Table

| Component | Priority | Effort | Owner | Dependencies | Key Deliverable |
|-----------|----------|--------|-------|--------------|-----------------|
| 2.1 AppSync GraphQL | Must-have | 7-8h | AI Agent | Phase 1 complete | Working GraphQL API |
| 2.2 GraphQL Resolvers | Must-have | 8h | AI Agent | 2.1, (2.3 parallel) | Lambda & DynamoDB resolvers |
| 2.3 DynamoDB Module | Must-have | 6-7h | AI Agent | Phase 1 complete | DynamoDB tables + IAM |
| 2.4 Aurora Serverless v2 | Must-have | 8h | AI Agent | 2.6 (parallel) | RDS cluster + secrets |
| 2.5 S3 Module | Must-have | 4-5h | AI Agent | Phase 1 complete | S3 buckets + presigned URLs |
| 2.6 Secrets Management | Must-have | 5-6h | AI Agent | Phase 1 complete | SSM + Secrets Manager abstraction |
| 2.7 Enhanced Observability | Must-have | 7-8h | AI Agent | All constructs | Alarms + dashboards + X-Ray |
| 2.8 LLM Assistant | Must-have | 8h | AI Agent | Phase 1 CLI | OpenAI integration + patch gen |
| 2.9 Examples + Guides | Must-have | 6-7h | AI Agent | All Phase 2 | Complete examples + prod guide |

**Total Estimated Effort**: 60-68 hours (approximately 8-9 days for single developer)

**Parallel Development Potential**: With 2 developers, Phase 2 could complete in 5-6 days by parallelizing independent components.

---

## End of Phase 2 Component Breakdown

This completes the detailed component breakdown for Phase 2: GraphQL, Data Services & AI Assistant. Upon completion of all components, the AWS API Factory will be feature-complete with REST and GraphQL APIs, comprehensive data layer options, production-grade observability, and AI-powered assistance for adapter generation.

**Next Steps**: 
1. Begin implementation with Components 2.3, 2.5, 2.6 (parallel)
2. Follow suggested execution order for optimal dependency management
3. Complete all acceptance criteria before moving to next component
4. Update Phase Component Overview documentation after each component
5. Conduct Post-Phase 2 Readiness Checklist before public release
6. Prepare for v1.0.0 release with both Phase 1 and Phase 2 complete