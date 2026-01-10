# Phase Plan: AWS API Factory

## Overview
This implementation plan delivers a production-ready, open-source AWS API Factory in 2 phases, starting with core REST API capabilities and essential tooling, then adding GraphQL, data services, and the LLM compatibility assistant. Each phase delivers a fully functional, deployable system that users can adopt immediately.

## Timeline Summary
- **Number of Phases**: 2 phases
- **Number of Components**: 18 components total (9 per phase)
- **Estimated Total Effort**: 72-144 hours
- **Target Delivery**: Phase 1 enables basic REST API deployments; Phase 2 adds GraphQL, data services, and AI assistance

## Phase List

### Phase 1: Core Framework & REST API Lane (Foundation)
**Goal**: Deliver a working, installable AWS API Factory that enables users to deploy REST APIs with Lambda or App Runner compute, including authentication options and basic observability.

**Duration**: 36-72 hours

**Core Components**:
1. Project structure and packaging setup (pyproject.toml, library structure)
2. Configuration system (pydantic models, YAML schema, validation)
3. Profile defaults engine (Minimal vs Scalable resolution)
4. CLI foundation (init, validate, synth, deploy commands)
5. CDK base stack and constructs architecture
6. REST API + Lambda integration construct
7. REST API + App Runner integration construct
8. Authentication module (API Keys, IAM, Cognito)
9. Starter template and documentation

**Deliverable**: Users can install aws-api-factory, scaffold a project, configure REST APIs with Lambda or App Runner backends, add authentication, and deploy to AWS successfully.

---

### Phase 2: GraphQL, Data Services & AI Assistant (Feature Complete)
**Goal**: Add GraphQL capabilities, data layer options (DynamoDB, Aurora, S3), enhanced observability for Scalable profile, and the LLM compatibility assistant for adapter generation.

**Duration**: 36-72 hours

**Core Components**:
1. AppSync GraphQL construct with schema deployment
2. GraphQL resolver integrations (Lambda, DynamoDB)
3. DynamoDB module with table creation and IAM permissions
4. Aurora Serverless v2 module with secrets integration
5. S3 module for file storage
6. Secrets management abstraction (SSM vs Secrets Manager)
7. Enhanced observability module (alarms, dashboards, tracing)
8. LLM compatibility assistant (OpenAI integration, patch generation)
9. Comprehensive examples and production deployment guide

**Deliverable**: Full-featured AWS API Factory supporting REST and GraphQL APIs, complete data layer options, production observability, and AI-powered adapter generation assistance.

---

## Cross-Cutting Concerns

### Testing Strategy
- **Unit Testing**: All configuration models, defaults resolvers, and utility functions require pytest unit tests with >50% coverage; mock AWS CDK constructs for isolated testing
- **Integration Testing**: Each construct (REST API, AppSync, Lambda, App Runner) has integration tests that synthesize CloudFormation and validate resource properties match expected configuration
- **E2E Testing**: Critical user journeys tested via actual CDK deploy to isolated AWS account (deploy REST+Lambda, deploy GraphQL+DynamoDB, deploy with Cognito auth) in CI/CD
- **Validation Testing**: Config validation logic tested extensively with valid/invalid YAML fixtures ensuring fast-fail behavior and helpful error messages
- **Template Testing**: Starter template scaffolding tested to ensure generated projects can immediately synth and deploy

### Documentation Requirements
- **Developer Context Documentation**:
  - Phase Overview: High-level goals and deliverables for each phase
  - README.md with quick start, installation, and architecture overview
  - CONTRIBUTING.md with development setup and PR guidelines
- **Code Documentation**:
  - Docstrings (Google style) for all public classes and functions
  - Inline comments for complex CDK construct logic and IAM policies
  - Type hints throughout for IDE support
- **API Documentation**:
  - Config schema exported as JSON Schema with examples
  - CLI commands documented with --help text and examples
  - Construct interfaces documented for users building custom extensions
- **Architecture Decision Records**:
  - ADR-001: Why two profiles only (Minimal/Scalable)
  - ADR-002: Config-driven vs code-driven approach
  - ADR-003: OpenAI Responses API for LLM assistant
  - ADR-004: Convention over configuration for adapters
- **User Documentation**:
  - Getting Started guide (15-minute tutorial)
  - Configuration reference (all factory.yaml options)
  - Module guides (REST, GraphQL, Auth, Data, Compute)
  - Examples for common patterns (CRUD API, GraphQL blog, multi-service)
- **Deployment Documentation**:
  - AWS account setup and prerequisites
  - CI/CD integration patterns (GitHub Actions, GitLab CI)
  - Multi-environment deployment strategy
  - Troubleshooting common deployment issues

### Quality Gates
- **Code Review**: All PRs require review from maintainer; automated checks must pass (lint, format, type-check)
- **Automated Tests**: pytest suite must pass with >50% coverage; integration tests must synthesize valid CloudFormation
- **Code Quality**: black formatter (enforced)
- **Security Scan**: Bandit security scanner for Python code; checkov for CDK/CloudFormation best practices; no secrets in code (pre-commit hooks)
- **Documentation**: All new features require corresponding documentation updates; docstrings required for public APIs

### DevOps & Deployment
- **CI/CD Pipeline**:
  - GitHub Actions workflow: lint → test → build → publish to PyPI
  - Automated testing on Python 3.12
  - Integration tests run against real AWS account (isolated test environment)
  - Release automation with semantic versioning
- **Environment Promotion**:
  - Library: Dev branch → Main (after review) → PyPI release (tagged)
  - Test deployments: Isolated AWS accounts per PR for integration testing
- **Rollback Strategy**:
  - PyPI versioning allows users to pin to last-known-good version
  - CloudFormation stack rollback on deployment failure
  - CDK context caching prevents unintended resource replacements
- **Monitoring**:
  - Track PyPI download metrics and user adoption
  - Monitor GitHub issues for bug reports and feature requests
  - Log CDK deployment telemetry (opt-in) for usage patterns
- **Alerting**:
  - GitHub notifications for new issues/PRs
  - Dependabot alerts for security vulnerabilities in dependencies
  - CI/CD pipeline failures notify maintainers immediately

### Risk Management

#### Phase 1 Risks
1. **Risk**: CDK construct complexity leads to difficult-to-debug CloudFormation errors
   - **Mitigation**: Extensive integration tests synthesizing stacks; clear validation errors at config level; escape hatches for custom IAM/props

2. **Risk**: App Runner construct requires Docker build capabilities that complicate CI/CD
   - **Mitigation**: Provide clear Dockerfile templates; test with common base images; document local vs CI build considerations

3. **Risk**: Authentication module configuration is confusing for users unfamiliar with Cognito/IAM
   - **Mitigation**: Sensible defaults; clear documentation with decision tree; working examples for each auth mode

4. **Risk**: Starter template becomes outdated as library evolves
   - **Mitigation**: Automated tests that scaffold and deploy starter template; version starter template with library releases

#### Phase 2 Risks
1. **Risk**: Aurora Serverless v2 cold starts impact user experience
   - **Mitigation**: Document warm-up strategies; provide min ACU guidance; offer DynamoDB as faster alternative

2. **Risk**: LLM assistant generates incorrect adapter code leading to user frustration
   - **Mitigation**: Always generate diffs (never direct edits); extensive testing with sample codebases; clear "review required" warnings; graceful degradation if OpenAI unavailable

3. **Risk**: GraphQL schema-first approach conflicts with code-first resolver implementations
   - **Mitigation**: Clear conventions for schema location; validation that resolvers match schema; examples showing best practices

4. **Risk**: OpenAI API costs for LLM assistant become prohibitive for open-source project
   - **Mitigation**: User brings own API key; opt-in feature (not required); document expected costs; consider caching/rate limiting

### Prerequisites (Human Setup Required)

#### Phase 1 Prerequisites
- **AWS Account Setup** (Human): AWS account with admin access, AWS CLI configured, CDK bootstrap completed in target regions
- **Development Environment** (Human): Python 3.12+ installed, AWS CDK CLI installed (`npm install -g aws-cdk`), Docker installed for App Runner testing
- **GitHub Repository** (Human): Repository created, branch protection rules configured, GitHub Actions enabled
- **PyPI Account** (Human, for releases): PyPI account created, API token generated for automated publishing

#### Phase 2 Prerequisites
- **OpenAI API Access** (Human): OpenAI account created, API key generated (for LLM assistant testing/usage)
- **AWS Service Limits** (Human): Verify account limits for Aurora Serverless v2, AppSync APIs, and DynamoDB tables in target regions
- **Secrets Management** (Human): AWS Secrets Manager and SSM Parameter Store access configured

### Success Criteria

#### Phase 1 Success
- [ ] User can `pip install aws-api-factory` successfully
- [ ] `factory init` scaffolds working starter project
- [ ] User deploys REST API with Lambda backend to AWS in <15 minutes
- [ ] User deploys REST API with App Runner backend successfully
- [ ] API Key and Cognito authentication work end-to-end
- [ ] Minimal and Scalable profiles produce different CloudFormation with appropriate defaults
- [ ] Documentation enables new user to go from zero to deployed API
- [ ] All unit and integration tests pass with >50% coverage
- [ ] Zero secrets leaked in repository (pre-commit hooks enforced)

#### Phase 2 Success
- [ ] User can deploy AppSync GraphQL API with Lambda resolvers
- [ ] DynamoDB tables created with correct IAM permissions for Lambda access
- [ ] Aurora Serverless v2 cluster provisions successfully with connection secrets
- [ ] S3 buckets created with appropriate IAM policies
- [ ] `factory compat` generates valid adapter code for sample business logic
- [ ] Enhanced observability (alarms, dashboards) visible in Scalable profile deployments
- [ ] All Phase 1 functionality continues to work (no regressions)
- [ ] Comprehensive examples demonstrate REST, GraphQL, and multi-service patterns
- [ ] Production deployment guide enables teams to adopt for real workloads

### Dependencies Between Phases

**Phase 2 depends on Phase 1**:
- Configuration system must be extensible to add GraphQL, data, and LLM config sections
- CDK base stack architecture must support composing additional constructs
- CLI must be stable to add `compat` command
- Starter template structure must accommodate GraphQL schemas and resolver conventions

**No parallel work between phases**: Phase 1 must be complete, tested, and stable before Phase 2 begins to ensure foundation is solid.

---

## Notes

### Implementation Philosophy
All code produced must be **complete and production-ready**. No placeholders, no "TODO" comments in production code, and no partial implementations. Each component should be broken down small enough that it can be fully implemented in one focused session (2-8 hours). It is better to deliver a smaller, fully working feature than a larger partially-implemented one.

### Human vs AI Agent Ownership
Components requiring external account setup, service configuration, or third-party platform access are marked as requiring **Human** execution. All coding, testing, and documentation tasks can be executed by **AI Agent** with human review.

### Continuous Integration
After every component implementation, the entire application must still run successfully. This ensures we maintain a working system throughout development rather than breaking everything and fixing it at the end.

### Documentation Standards
Every component includes documentation requirements. Documentation is not an afterthought—it's part of the definition of done for each component. Phase Overview and Component Overview documents are created as components are completed to maintain context for future work.
