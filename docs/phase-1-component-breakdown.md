# Phase 1 Component Breakdown: Core Framework & REST API Lane

## Phase Overview

**Objective**: Deliver a working, installable AWS API Factory that enables users to deploy REST APIs with Lambda or App Runner compute, including authentication options and basic observability.

**Deliverables**: 
- Installable Python library (`aws-api-factory`) with proper packaging
- Configuration system with validation and defaults resolution
- CLI tools for project scaffolding and deployment
- CDK constructs for REST API + Lambda integration
- CDK constructs for REST API + App Runner integration
- Authentication module supporting API Keys, IAM, and Cognito
- Starter template with working examples
- Comprehensive documentation for getting started

**Dependencies**: 
- AWS account with admin access configured (Human prerequisite)
- Python 3.9+ development environment (Human prerequisite)
- AWS CDK CLI installed globally (Human prerequisite)
- Docker installed for App Runner testing (Human prerequisite)
- GitHub repository created (Human prerequisite)

## Phase Goals

- Users can install `aws-api-factory` via pip and scaffold new projects in seconds
- Users can define REST APIs via simple YAML configuration
- Users can deploy REST APIs with Lambda backends to AWS in under 15 minutes
- Users can deploy REST APIs with App Runner (containerized) backends successfully
- Authentication options (API Keys, IAM, Cognito) work end-to-end
- Minimal and Scalable profiles produce appropriate CloudFormation templates
- All code is production-ready with >85% test coverage
- Documentation enables zero-to-deployed workflow for new users

---

## Components

### Component 1.1: Project Structure and Packaging Setup

**Phase**: Phase 1 - Core Framework & REST API Lane

**Priority**: Must-have

**Estimated Effort**: 3-4 hours

**Owner**: AI Agent

**Dependencies**:
- GitHub repository created (Human prerequisite)
- Python 3.9+ installed (Human prerequisite)

**Features**:
- Monorepo structure with library and starter template separation (AI Agent)
- Python packaging configuration with pyproject.toml (AI Agent)
- Development tooling setup: black, pytest (AI Agent)
- Pre-commit hooks for security and code quality (AI Agent)
- Basic CI/CD workflow for testing (AI Agent)

**Description**:
Establish the foundational project structure as a Python monorepo with separate `src/aws_api_factory/` library code and `starter/` template. Configure modern Python packaging with pyproject.toml, development dependencies, and quality tooling. Set up pre-commit hooks to prevent secrets leakage and enforce code standards.

**Acceptance Criteria**:
- [ ] Monorepo structure matches specification in solution doc section 9.1
- [ ] `pyproject.toml` defines project metadata, dependencies, and build system
- [ ] Development dependencies include: pytest, black, pre-commit, aws-cdk-lib
- [ ] Pre-commit hooks configured for: black, bandit (security), detect-secrets
- [ ] GitHub Actions workflow runs lint + format check + type check on push
- [ ] README.md includes project overview and development setup instructions
- [ ] CONTRIBUTING.md documents development workflow and PR requirements
- [ ] All files have proper LICENSE headers (Apache 2.0 or MIT)

**Technical Details**:
- **Files to Create/Modify**: 
  - `pyproject.toml`, `.pre-commit-config.yaml`, `README.md`, `CONTRIBUTING.md`, `LICENSE`
  - `.github/workflows/ci.yml`, `.gitignore`
- **Key Functions/Classes**: N/A (configuration files)
- **Human/AI Agent**: All configuration and setup by AI Agent; human reviews structure
- **Database Changes**: N/A
- **API Endpoints**: N/A
- **Dependencies**: 
  - Core: `aws-cdk-lib>=2.100.0`, `pydantic>=2.0`, `pyyaml`, `click>=8.0`
  - Dev: `pytest>=7.0`, `pytest-cov`, `black`, `bandit`, `pre-commit`

**Detailed Implementation Requirements**:
- **File: `pyproject.toml`**: Define project as `aws-api-factory` with version 0.1.0, include all production and development dependencies, configure build system (setuptools or hatchling), define CLI entry point `factory = aws_api_factory.cli:main`, specify Python 3.9+ requirement, include project URLs (GitHub repo, docs, issues).
- **File: `.pre-commit-config.yaml`**: Configure hooks for black (formatter), bandit (security scanner), detect-secrets (prevent credential leaks), and trailing whitespace removal. Set to run on commit and push.
- **File: `.github/workflows/ci.yml`**: Create GitHub Actions workflow that runs on push/PR, sets up Python 3.9-3.12 matrix, installs dependencies, runs pre-commit hooks, executes pytest with coverage reporting, fails if coverage <85% or any check fails.
- **File: `README.md`**: Write comprehensive overview including: project mission, quick start example, installation instructions (`pip install -e .` for dev), link to documentation, contribution guidelines, license information.
- **File: `CONTRIBUTING.md`**: Document development setup (clone, create venv, install with `pip install -e ".[dev]"`), pre-commit hook setup, testing commands, PR process, code review expectations, branch naming conventions.

**Test Requirements**:
- [ ] Pre-commit hooks execute successfully on sample commit
- [ ] CI workflow runs and passes with empty test suite
- [ ] All configuration files are syntactically valid
- [ ] Manual verification: clone repo, run `pip install -e ".[dev]"`, verify no errors

**Definition of Done**:
- [ ] All configuration files created and committed
- [ ] Pre-commit hooks tested and working
- [ ] CI/CD pipeline runs successfully
- [ ] README and CONTRIBUTING docs complete
- [ ] Code passes all quality gates (lint, format, type check)
- [ ] No secrets or sensitive data in repository
- [ ] Component Overview documentation created
- [ ] Phase Component Overview documentation created

**Notes**:
- Use modern Python packaging with `pyproject.toml` (PEP 621) instead of setup.py
- Configure aggressive pre-commit hooks to catch issues early
- Document all tooling choices in CONTRIBUTING.md for new contributors

---

### Component 1.2: Configuration System (Pydantic Models & YAML Schema)

**Phase**: Phase 1 - Core Framework & REST API Lane

**Priority**: Must-have

**Estimated Effort**: 5-6 hours

**Owner**: AI Agent

**Dependencies**:
- Component 1.1: Project structure must exist

**Features**:
- Pydantic v2 models for all configuration sections (AI Agent)
- YAML loading and validation with clear error messages (AI Agent)
- JSON Schema export for documentation and IDE support (AI Agent)
- Comprehensive validation rules with helpful error messages (AI Agent)
- Configuration merging for environment-specific overrides (AI Agent)

**Description**:
Implement the complete configuration system using Pydantic v2 models that validate factory.yaml files. Create models for all configuration sections (project, profile, apis, compute, data, secrets, observability) with proper validation rules, defaults, and clear error messages. Enable JSON Schema export for IDE autocomplete and documentation generation.

**Acceptance Criteria**:
- [ ] Pydantic models exist for all config sections from solution doc section 8.1
- [ ] YAML files load and validate correctly with helpful error messages
- [ ] Invalid configurations fail fast with specific, actionable error messages
- [ ] JSON Schema exported successfully for IDE/documentation use
- [ ] Environment-specific config merging works (e.g., dev/prod overrides)
- [ ] All validation rules documented in docstrings
- [ ] Type hints complete and pass mypy strict mode
- [ ] Unit tests achieve >90% coverage for config module

**Technical Details**:
- **Files to Create/Modify**:
  - `src/aws_api_factory/config/__init__.py`
  - `src/aws_api_factory/config/models.py`
  - `src/aws_api_factory/config/loader.py`
  - `src/aws_api_factory/config/schema.py`
  - `src/aws_api_factory/config/validators.py`
  - `tests/config/test_models.py`
  - `tests/config/test_loader.py`
  - `tests/config/fixtures/*.yaml`
- **Key Functions/Classes**: 
  - `FactoryConfig` (root model), `ProjectConfig`, `ProfileEnum`, `ApisConfig`, `RestApiConfig`, `GraphQLConfig`, `ComputeConfig`, `LambdaConfig`, `AppRunnerConfig`, `DataConfig`, `SecretsConfig`, `ObservabilityConfig`
  - `load_config(path: Path) -> FactoryConfig`
  - `export_json_schema() -> dict`
- **Human/AI Agent**: All implementation by AI Agent
- **Database Changes**: N/A
- **API Endpoints**: N/A
- **Dependencies**: `pydantic>=2.0`, `pyyaml`, `typing-extensions`

**Detailed Implementation Requirements**:
- **File: `src/aws_api_factory/config/models.py`**: Define all Pydantic models with Field validators for each config section. Use enums for profile (minimal/scalable), auth modes (none/api_key/iam/cognito), secrets provider (ssm/secrets_manager). Add computed fields for derived values. Include comprehensive docstrings for each field. Use Pydantic v2 features: model_validator, field_validator, ConfigDict. Define nested models: RouteConfig (path, methods, service, auth), ResolverConfig (type, field, service, resolver), ServiceConfig (entry, memory_mb, timeout_s), TableConfig (name, pk, sk), etc.
- **File: `src/aws_api_factory/config/loader.py`**: Implement `load_config()` function that reads YAML, merges environment-specific overrides, validates with Pydantic, catches ValidationError and reformats into user-friendly messages with line numbers and suggestions. Support loading from Path or string. Handle missing files gracefully. Add function to merge base config with environment overrides (e.g., factory.yaml + factory.dev.yaml).
- **File: `src/aws_api_factory/config/schema.py`**: Implement `export_json_schema()` that uses Pydantic's `model_json_schema()` to generate JSON Schema, adds custom descriptions and examples, formats for readability, includes all nested models. Add CLI command hook for exporting schema to file.
- **File: `src/aws_api_factory/config/validators.py`**: Implement custom validators: validate_service_exists (service referenced in routes exists in compute.lambda.services), validate_path_format (paths start with /), validate_auth_config (if auth=cognito, cognito config must exist), validate_memory_timeout (sensible ranges), validate_dynamodb_keys (pk required, sk optional).
- **File: `tests/config/test_models.py`**: Unit tests for each Pydantic model covering: valid minimal config, valid full config, invalid configs with expected error messages, edge cases (empty lists, null values, invalid enums), computed fields work correctly, defaults applied properly. Use pytest fixtures for config variations.
- **File: `tests/config/test_loader.py`**: Unit tests for config loading covering: load valid YAML successfully, handle missing file with clear error, handle invalid YAML syntax, handle validation errors with user-friendly messages, environment override merging works correctly, JSON Schema export succeeds.
- **File: `tests/config/fixtures/*.yaml`**: Create fixture files: `minimal_valid.yaml` (minimal working config), `scalable_valid.yaml` (full scalable config), `invalid_*.yaml` files for each validation scenario (missing required fields, invalid values, bad references).

**Test Requirements**:
- [ ] Unit tests for all Pydantic models with valid and invalid inputs
- [ ] Unit tests for YAML loading with various file formats
- [ ] Unit tests for validation error formatting
- [ ] Unit tests for JSON Schema export
- [ ] Unit tests for environment config merging
- [ ] Achieve >90% code coverage for config module
- [ ] Manual test: load sample factory.yaml files and verify error messages are helpful

**Definition of Done**:
- [ ] All Pydantic models implemented with validation
- [ ] YAML loading works with clear error messages
- [ ] JSON Schema export functional
- [ ] All unit tests passing with >90% coverage
- [ ] Documentation: config module docstrings complete
- [ ] Type hints complete, mypy passes in strict mode
- [ ] Component Overview documentation created
- [ ] Phase Component Overview documentation updated
- [ ] No regression in project structure

**Notes**:
- Pydantic v2 has breaking changes from v1; use v2 API throughout
- Focus on error message quality; users will see these frequently
- JSON Schema should be suitable for VS Code YAML extension autocomplete
- Consider validator performance; config loading should be <100ms for typical files

---

### Component 1.3: Profile Defaults Engine (Minimal vs Scalable Resolution)

**Phase**: Phase 1 - Core Framework & REST API Lane

**Priority**: Must-have

**Estimated Effort**: 4-5 hours

**Owner**: AI Agent

**Dependencies**:
- Component 1.2: Configuration system must be complete

**Features**:
- Defaults resolution engine for Minimal profile (AI Agent)
- Defaults resolution engine for Scalable profile (AI Agent)
- Override mechanism for user-specified values (AI Agent)
- Clear documentation of all defaults per profile (AI Agent)
- Validation that resolved config is complete and valid (AI Agent)

**Description**:
Implement the defaults resolution system that takes user's profile choice (minimal/scalable) and factory.yaml config, then resolves all unspecified values to appropriate defaults per profile. The engine ensures that every required value is set, either from user config or profile defaults, before CDK synthesis begins.

**Acceptance Criteria**:
- [ ] Defaults engine resolves all missing values for Minimal profile
- [ ] Defaults engine resolves all missing values for Scalable profile
- [ ] User-specified values always override profile defaults
- [ ] Resolved config is complete and passes validation
- [ ] Defaults documented for all config sections in both profiles
- [ ] Unit tests cover all default resolution scenarios
- [ ] Integration test: minimal factory.yaml resolves to fully valid config
- [ ] Integration test: scalable factory.yaml resolves to fully valid config

**Technical Details**:
- **Files to Create/Modify**:
  - `src/aws_api_factory/config/defaults.py`
  - `src/aws_api_factory/config/resolver.py`
  - `tests/config/test_defaults.py`
  - `tests/config/test_resolver.py`
  - `docs/reference/defaults.md`
- **Key Functions/Classes**:
  - `MinimalDefaults` (dataclass with all minimal profile defaults)
  - `ScalableDefaults` (dataclass with all scalable profile defaults)
  - `DefaultsResolver` (class with `resolve(config: FactoryConfig) -> FactoryConfig` method)
  - Helper functions: `merge_defaults()`, `apply_profile_defaults()`, `validate_completeness()`
- **Human/AI Agent**: All implementation by AI Agent
- **Database Changes**: N/A
- **API Endpoints**: N/A
- **Dependencies**: None beyond existing

**Detailed Implementation Requirements**:
- **File: `src/aws_api_factory/config/defaults.py`**: Define `MinimalDefaults` and `ScalableDefaults` as dataclasses or Pydantic models containing all default values. For Lambda: Minimal (memory=512, timeout=30, concurrency=None), Scalable (memory=1024, timeout=60, reserved_concurrency=10). For API Gateway: Minimal (throttle=None, logging="INFO"), Scalable (throttle=1000, logging="INFO", metrics=True, tracing=True). For DynamoDB: Minimal (billing_mode="PAY_PER_REQUEST", pitr=False), Scalable (billing_mode="PAY_PER_REQUEST", pitr=True, alarms=True). For App Runner: Minimal (cpu=1, memory=2, min_instances=1, max_instances=10), Scalable (cpu=2, memory=4, min_instances=2, max_instances=25, healthcheck_protocol="HTTP"). Document all defaults with comments explaining rationale.
- **File: `src/aws_api_factory/config/resolver.py`**: Implement `DefaultsResolver` class with `resolve()` method that: 1) takes user's FactoryConfig, 2) loads appropriate defaults based on profile, 3) recursively merges defaults with user config (user values win), 4) handles "auto" values (e.g., memory_mb="auto" becomes profile default), 5) validates completeness (no None values remain for required fields), 6) returns fully resolved FactoryConfig. Use recursive dict merging to handle nested config sections. Add `explain()` method that returns human-readable diff showing what defaults were applied.
- **File: `tests/config/test_defaults.py`**: Unit tests verifying: MinimalDefaults has sensible values, ScalableDefaults has higher resource values than Minimal, all required fields have defaults, defaults are documented with rationale, defaults pass validation when used in config.
- **File: `tests/config/test_resolver.py`**: Unit tests covering: empty config resolves to full defaults, partial config merges with defaults correctly, user values override defaults, "auto" values resolve to profile defaults, nested config sections merge properly, completeness validation catches missing required fields, explain() method shows applied defaults correctly. Integration tests: load minimal factory.yaml fixture, resolve with Minimal profile, verify all values set; repeat for Scalable profile.
- **File: `docs/reference/defaults.md`**: Create comprehensive reference documentation listing all defaults for Minimal and Scalable profiles in tables. Include rationale for each default choice. Add decision tree for users: "When to use Minimal" (learning, prototyping, low traffic) vs "When to use Scalable" (production, high traffic, compliance requirements). Explain override mechanism with examples.

**Test Requirements**:
- [ ] Unit tests for MinimalDefaults and ScalableDefaults
- [ ] Unit tests for DefaultsResolver with various config combinations
- [ ] Integration tests resolving minimal and scalable fixture configs
- [ ] Test that user values always override defaults
- [ ] Test that "auto" values resolve correctly
- [ ] Test completeness validation catches missing fields
- [ ] Achieve >90% coverage for defaults module

**Definition of Done**:
- [ ] Defaults engine implemented and tested
- [ ] All defaults documented with rationale
- [ ] Unit and integration tests passing
- [ ] Documentation: defaults.md reference created
- [ ] Type hints complete, mypy passes
- [ ] Component Overview documentation created
- [ ] Phase Component Overview documentation updated
- [ ] Config system still works with resolved defaults

**Notes**:
- Profile defaults should be opinionated but safe
- Minimal profile should be approximately free-tier friendly where possible
- Scalable profile should prioritize reliability and observability over cost
- Document the cost implications of each profile in defaults.md
- Consider adding a "dry-run" mode that shows resolved config without deploying

---

### Component 1.4: CLI Foundation (init, validate, synth, deploy, destroy)

**Phase**: Phase 1 - Core Framework & REST API Lane

**Priority**: Must-have

**Estimated Effort**: 6-7 hours

**Owner**: AI Agent

**Dependencies**:
- Component 1.1: Project structure must exist
- Component 1.2: Configuration system must be complete
- Component 1.3: Defaults engine must be complete

**Features**:
- `factory init` command to scaffold new projects (AI Agent)
- `factory validate` command to check config and show resolved defaults (AI Agent)
- `factory synth` command to generate CloudFormation (AI Agent)
- `factory deploy <env>` command to deploy to AWS (AI Agent)
- `factory destroy <env>` command to tear down stacks (AI Agent)
- Rich CLI output with colors and progress indicators (AI Agent)
- Helpful error messages with suggestions (AI Agent)

**Description**:
Implement the complete CLI using Click framework with all core commands needed for the factory workflow. CLI should wrap CDK operations, provide user-friendly output, validate configs before deployment, and offer helpful guidance throughout the user journey.

**Acceptance Criteria**:
- [ ] `factory init` scaffolds complete starter project from template
- [ ] `factory validate` loads config, resolves defaults, shows what will be deployed
- [ ] `factory synth` generates CloudFormation templates via CDK
- [ ] `factory deploy <env>` deploys stack to AWS with progress output
- [ ] `factory destroy <env>` tears down stack with safety confirmation
- [ ] All commands have `--help` text with examples
- [ ] Error messages are clear and actionable
- [ ] CLI output is colorized and user-friendly
- [ ] Unit tests for CLI command logic (not CDK integration)
- [ ] Integration test: run full workflow (init → validate → synth)

**Technical Details**:
- **Files to Create/Modify**:
  - `src/aws_api_factory/cli/__init__.py`
  - `src/aws_api_factory/cli/main.py`
  - `src/aws_api_factory/cli/commands/init.py`
  - `src/aws_api_factory/cli/commands/validate.py`
  - `src/aws_api_factory/cli/commands/synth.py`
  - `src/aws_api_factory/cli/commands/deploy.py`
  - `src/aws_api_factory/cli/commands/destroy.py`
  - `src/aws_api_factory/cli/utils.py`
  - `tests/cli/test_commands.py`
- **Key Functions/Classes**:
  - `factory` (Click group, main entry point)
  - `init()`, `validate()`, `synth()`, `deploy()`, `destroy()` (Click commands)
  - `load_and_validate_config()`, `run_cdk_command()`, `confirm_action()` (utilities)
- **Human/AI Agent**: All implementation by AI Agent
- **Database Changes**: N/A
- **API Endpoints**: N/A
- **Dependencies**: `click>=8.0`, `rich>=10.0` (for pretty output), `aws-cdk-lib`

**Detailed Implementation Requirements**:
- **File: `src/aws_api_factory/cli/main.py`**: Define `factory` Click group as main entry point. Configure global options: `--verbose`, `--config-path` (default: factory.yaml), `--no-color`. Set up logging configuration. Handle keyboard interrupts gracefully. Show version with `--version`.
- **File: `src/aws_api_factory/cli/commands/init.py`**: Implement `factory init [project_name]` command that: 1) prompts for project name if not provided, 2) copies starter template to new directory, 3) replaces placeholder values in factory.yaml and other files, 4) initializes git repository, 5) installs pre-commit hooks, 6) prints success message with next steps. Add `--profile` option (minimal/scalable) to choose starter template variant. Use rich for progress output.
- **File: `src/aws_api_factory/cli/commands/validate.py`**: Implement `factory validate` command that: 1) loads factory.yaml, 2) validates with Pydantic, 3) resolves defaults, 4) prints resolved config in formatted YAML, 5) shows what resources will be created, 6) highlights any warnings or recommendations. Add `--output` option to write resolved config to file. Use rich tables to show resolved values vs user-specified values.
- **File: `src/aws_api_factory/cli/commands/synth.py`**: Implement `factory synth` command that: 1) validates config, 2) imports CDK app from infra/, 3) runs `cdk synth`, 4) prints CloudFormation template location, 5) optionally displays template. Add `--show` flag to print CloudFormation to stdout. Wrap CDK subprocess calls with error handling.
- **File: `src/aws_api_factory/cli/commands/deploy.py`**: Implement `factory deploy <env>` command that: 1) validates config with environment override, 2) runs `cdk deploy` with environment context, 3) shows deployment progress, 4) prints stack outputs (API URLs, etc.) on success. Add `--require-approval` option (default: broadening for security). Add `--outputs-file` to save outputs as JSON. Use rich progress spinners during deployment.
- **File: `src/aws_api_factory/cli/commands/destroy.py`**: Implement `factory destroy <env>` command that: 1) loads config, 2) shows resources that will be deleted, 3) prompts for confirmation (type environment name to confirm), 4) runs `cdk destroy`, 5) prints success message. Add `--force` flag to skip confirmation (dangerous, warn user).
- **File: `src/aws_api_factory/cli/utils.py`**: Implement helper functions: `load_and_validate_config(path, env)` (loads, validates, resolves), `run_cdk_command(args, cwd)` (subprocess wrapper with error handling), `confirm_action(message)` (prompt user for confirmation), `format_config_output(config)` (pretty-print config), `print_success()`, `print_error()`, `print_warning()` (rich-based output helpers).
- **File: `tests/cli/test_commands.py`**: Unit tests for CLI commands using Click's CliRunner: test init command creates files, test validate command loads config, test synth command calls CDK subprocess, test deploy command with mock subprocess, test destroy command requires confirmation. Mock filesystem operations and CDK subprocess calls. Test error handling: invalid config, missing AWS credentials, CDK errors.

**Test Requirements**:
- [ ] Unit tests for each CLI command using CliRunner
- [ ] Test command help text is complete and accurate
- [ ] Test error handling for invalid configs and missing files
- [ ] Test confirmation prompts work correctly
- [ ] Integration test: `factory init test-project` creates valid project
- [ ] Integration test: `factory validate` on starter template succeeds
- [ ] Manual test: run full CLI workflow end-to-end

**Definition of Done**:
- [ ] All CLI commands implemented and tested
- [ ] Help text complete for all commands with examples
- [ ] Error messages are user-friendly and actionable
- [ ] Rich output with colors and progress indicators
- [ ] Unit tests passing with >85% coverage
- [ ] CLI entry point works: `factory --help`
- [ ] Component Overview documentation created
- [ ] Phase Component Overview documentation updated
- [ ] User documentation: CLI reference created

**Notes**:
- Click is chosen for its simplicity and automatic help generation
- Rich library provides excellent terminal output capabilities
- Consider adding shell completion support (Click supports this)
- CLI should never silently fail; always show clear error messages
- For deploy/destroy, always show what will happen before doing it

---

### Component 1.5: CDK Base Stack and Constructs Architecture

**Phase**: Phase 1 - Core Framework & REST API Lane

**Priority**: Must-have

**Estimated Effort**: 5-6 hours

**Owner**: AI Agent

**Dependencies**:
- Component 1.1: Project structure must exist
- Component 1.2: Configuration system must be complete
- Component 1.3: Defaults engine must be complete

**Features**:
- Base CDK Stack class with common setup (AI Agent)
- Construct registry and composition pattern (AI Agent)
- Tagging and naming conventions (AI Agent)
- Output management system (AI Agent)
- Stack synthesis and validation (AI Agent)

**Description**:
Create the foundational CDK architecture with a base stack class, construct composition pattern, and infrastructure for module integration. This forms the backbone that all constructs (REST API, Lambda, App Runner, Auth, etc.) will plug into, ensuring consistent patterns and proper resource organization.

**Acceptance Criteria**:
- [ ] `FactoryStack` base class created with common initialization
- [ ] Construct registry allows dynamic module loading
- [ ] All resources tagged with project name, environment, profile
- [ ] Stack outputs collected and formatted consistently
- [ ] CDK synthesis produces valid CloudFormation
- [ ] Unit tests for stack initialization and tagging
- [ ] Integration test: minimal stack synthesizes successfully
- [ ] Documentation: construct development guide created

**Technical Details**:
- **Files to Create/Modify**:
  - `src/aws_api_factory/constructs/__init__.py`
  - `src/aws_api_factory/constructs/base.py`
  - `src/aws_api_factory/constructs/factory_stack.py`
  - `src/aws_api_factory/constructs/outputs.py`
  - `starter/infra/app.py`
  - `starter/infra/stacks/factory_stack.py`
  - `tests/constructs/test_factory_stack.py`
  - `docs/guides/construct-development.md`
- **Key Functions/Classes**:
  - `FactoryStack(Stack)` - main stack class
  - `BaseConstruct(Construct)` - base class for all factory constructs
  - `ConstructRegistry` - manages construct loading and composition
  - `OutputManager` - collects and formats stack outputs
  - `apply_tags()`, `generate_resource_name()` - utility functions
- **Human/AI Agent**: All implementation by AI Agent
- **Database Changes**: N/A
- **API Endpoints**: N/A
- **Dependencies**: `aws-cdk-lib>=2.100.0`, `constructs>=10.0.0`

**Detailed Implementation Requirements**:
- **File: `src/aws_api_factory/constructs/base.py`**: Define `BaseConstruct(Construct)` abstract base class that all factory constructs extend. Include: `__init__(scope, id, config, profile_defaults)`, abstract method `_create_resources()`, method `add_output(key, value, description)` to register outputs, method `get_resource_name(logical_name)` for consistent naming. Add validation that required config sections exist. Implement `validate_config()` abstract method.
- **File: `src/aws_api_factory/constructs/factory_stack.py`**: Define `FactoryStack(Stack)` that: 1) accepts `FactoryConfig`, 2) initializes OutputManager, 3) applies global tags (project name, environment, profile, managed_by="aws-api-factory"), 4) creates ConstructRegistry, 5) dynamically loads and instantiates constructs based on config (if apis.rest.enabled, load RestApiConstruct), 6) collects outputs from all constructs, 7) creates CfnOutputs for all outputs. Include method `register_construct(construct_class, config_section)` to add constructs. Use context values from CDK for environment-specific config.
- **File: `src/aws_api_factory/constructs/outputs.py`**: Implement `OutputManager` class that: 1) collects outputs from constructs with `add(key, value, description, export_name)`, 2) formats outputs for CloudFormation CfnOutput, 3) generates JSON file with all outputs for CLI consumption, 4) validates output keys are unique. Add methods: `add_output()`, `get_outputs()`, `export_to_cfn()`, `export_to_json()`.
- **File: `starter/infra/app.py`**: Create CDK app entry point that: 1) loads factory.yaml from project root, 2) validates and resolves config, 3) reads environment from CDK context (--context env=dev), 4) instantiates FactoryStack with config and env, 5) synths app. Include error handling for missing config or invalid environment. Add logging to show what's being deployed.
- **File: `starter/infra/stacks/factory_stack.py`**: Create user-facing stack file that imports and extends FactoryStack from library. This file is customizable by users for escape hatches. Include comments showing how to add custom resources or override construct behavior. Keep minimal; most logic should be in library FactoryStack.
- **File: `tests/constructs/test_factory_stack.py`**: Unit tests for FactoryStack covering: stack initialization with valid config, tagging applied correctly, outputs registered properly, construct registry loads constructs based on config, stack synthesis produces valid CloudFormation template, environment context handled correctly. Use CDK assertions library to verify resource properties. Test with minimal and scalable profile configs.
- **File: `docs/guides/construct-development.md`**: Write guide for developers creating new constructs: 1) extend BaseConstruct, 2) implement required methods, 3) register outputs, 4) follow naming conventions, 5) write tests, 6) document config schema. Include examples of simple and complex constructs. Document escape hatches: `extra_cdk_props`, `custom_iam_statements`, importing existing resources.

**Test Requirements**:
- [ ] Unit tests for BaseConstruct and FactoryStack
- [ ] Test tagging applied to all resources
- [ ] Test output registration and export
- [ ] Test construct registry loads correct constructs based on config
- [ ] Integration test: synthesize stack with minimal config
- [ ] Integration test: synthesize stack with scalable config
- [ ] Verify CloudFormation template structure and validity

**Definition of Done**:
- [ ] Base stack architecture implemented
- [ ] Construct composition pattern working
- [ ] Tagging and naming conventions applied
- [ ] Output management functional
- [ ] Unit and integration tests passing
- [ ] CDK synthesis produces valid CloudFormation
- [ ] Documentation: construct development guide created
- [ ] Component Overview documentation created
- [ ] Phase Component Overview documentation updated

**Notes**:
- Use CDK Aspects for applying tags across all resources
- Follow AWS resource naming conventions: {project}-{env}-{resource-type}-{name}
- Outputs should include all user-facing endpoints and ARNs
- Consider adding CDK Nag for security and best practice checks
- ConstructRegistry should support lazy loading for better performance

---

### Component 1.6: REST API + Lambda Integration Construct

**Phase**: Phase 1 - Core Framework & REST API Lane

**Priority**: Must-have

**Estimated Effort**: 7-8 hours

**Owner**: AI Agent

**Dependencies**:
- Component 1.5: CDK base stack must exist
- Component 1.2: Configuration system must be complete

**Features**:
- API Gateway REST API construct (AI Agent)
- Lambda function creation and configuration (AI Agent)
- API Gateway → Lambda proxy integration (AI Agent)
- Per-route method and path configuration (AI Agent)
- CloudWatch logging for API and Lambda (AI Agent)
- Minimal vs Scalable defaults applied (AI Agent)

**Description**:
Implement the REST API construct that creates API Gateway REST APIs with Lambda backend integration. Support per-route configuration (path, methods, target Lambda), apply profile-based defaults for Lambda memory/timeout, set up CloudWatch logging, and enable proper IAM permissions between API Gateway and Lambda.

**Acceptance Criteria**:
- [ ] API Gateway REST API created with custom name
- [ ] Lambda functions created per service with correct handler paths
- [ ] API Gateway resources and methods map to config routes
- [ ] Lambda proxy integration works for all configured routes
- [ ] CloudWatch logs enabled for API Gateway and Lambda
- [ ] IAM roles grant least-privilege permissions
- [ ] Minimal profile uses lower resource limits
- [ ] Scalable profile uses higher resource limits with enhanced logging
- [ ] Integration test: deploy and invoke REST endpoint successfully
- [ ] Unit tests for construct creation and configuration

**Technical Details**:
- **Files to Create/Modify**:
  - `src/aws_api_factory/constructs/rest_api/__init__.py`
  - `src/aws_api_factory/constructs/rest_api/api.py`
  - `src/aws_api_factory/constructs/rest_api/lambda_integration.py`
  - `src/aws_api_factory/constructs/compute_lambda/__init__.py`
  - `src/aws_api_factory/constructs/compute_lambda/function.py`
  - `starter/src/services/hello/handler.py`
  - `tests/constructs/test_rest_api.py`
  - `tests/constructs/test_lambda.py`
  - `tests/integration/test_rest_lambda_e2e.py`
- **Key Functions/Classes**:
  - `RestApiConstruct(BaseConstruct)` - creates API Gateway
  - `LambdaFunctionConstruct(BaseConstruct)` - creates Lambda functions
  - `create_lambda_integration()` - sets up proxy integration
  - `create_api_resource()`, `create_api_method()` - API Gateway helpers
- **Human/AI Agent**: All implementation by AI Agent
- **Database Changes**: N/A
- **API Endpoints**: All routes defined in factory.yaml
- **Dependencies**: `aws-cdk-lib` (apigateway, lambda, iam, logs modules)

**Detailed Implementation Requirements**:
- **File: `src/aws_api_factory/constructs/rest_api/api.py`**: Implement `RestApiConstruct` that: 1) creates RestApi with name from config, 2) enables CloudWatch logging (access logs + execution logs), 3) creates deployment stage with stage name from environment, 4) iterates routes from config and creates resources/methods, 5) sets up Lambda integrations per route, 6) applies profile-specific settings (Minimal: basic logging; Scalable: detailed metrics, request/response logging, X-Ray tracing), 7) registers API endpoint URL as output. Handle nested paths correctly (e.g., /orders/{orderId}/items). Configure CORS if specified in config. Apply throttling settings from profile defaults.
- **File: `src/aws_api_factory/constructs/rest_api/lambda_integration.py`**: Implement helper functions: `create_lambda_integration(lambda_function)` returns LambdaIntegration with proxy=True, `attach_integration_to_method(method, integration)` connects integration to API method, `grant_invoke_permission(api, lambda_function)` sets up IAM permissions for API Gateway to invoke Lambda. Handle integration timeout settings.
- **File: `src/aws_api_factory/constructs/compute_lambda/function.py`**: Implement `LambdaFunctionConstruct` that: 1) creates Lambda function with runtime=Python3.11, 2) uses handler path from config (e.g., "src/services/hello/handler.py:handler"), 3) applies memory and timeout from resolved defaults, 4) creates execution role with CloudWatch Logs permissions, 5) enables X-Ray tracing if Scalable profile, 6) sets up log retention (7 days Minimal, 30 days Scalable), 7) configures environment variables from config, 8) packages code using aws-cdk-lib's Code.from_asset(). Support both inline handlers and asset bundles. Add reserved concurrency if specified in config.
- **File: `starter/src/services/hello/handler.py`**: Create example Lambda handler: `def handler(event, context): return {"statusCode": 200, "body": json.dumps({"message": "Hello from AWS API Factory!", "request_id": context.request_id})}`. Include proper error handling and logging. Add docstring explaining the handler contract. Keep simple and production-ready.
- **File: `tests/constructs/test_rest_api.py`**: Unit tests for RestApiConstruct: verify API created with correct name, deployment stage created, resources and methods match config routes, Lambda integrations attached, CloudWatch logs enabled, IAM permissions correct, profile-specific settings applied (Minimal vs Scalable). Use CDK assertions to verify CloudFormation properties. Mock Lambda construct creation.
- **File: `tests/constructs/test_lambda.py`**: Unit tests for LambdaFunctionConstruct: verify function created with correct runtime/handler/memory/timeout, execution role has CloudWatch permissions, code asset packaged correctly, environment variables set, X-Ray tracing enabled in Scalable, log retention configured. Test both Minimal and Scalable profile defaults.
- **File: `tests/integration/test_rest_lambda_e2e.py`**: Integration test that: 1) creates minimal factory.yaml with single REST route, 2) synthesizes stack, 3) validates CloudFormation template structure, 4) optionally deploys to test AWS account (if credentials available), 5) invokes API endpoint and verifies response, 6) cleans up resources. Use pytest fixtures for config and stack setup. Mark as slow/integration test.

**Test Requirements**:
- [ ] Unit tests for REST API construct with various configurations
- [ ] Unit tests for Lambda construct with Minimal and Scalable profiles
- [ ] Unit tests for integration setup and IAM permissions
- [ ] Integration test: synthesize stack with REST + Lambda
- [ ] Integration test: deploy and invoke endpoint (optional, slow)
- [ ] Manual test: deploy hello world API and curl endpoint
- [ ] Verify CloudWatch logs appear for API requests and Lambda execution

**Definition of Done**:
- [ ] REST API construct implemented and tested
- [ ] Lambda construct implemented and tested
- [ ] API Gateway → Lambda integration working
- [ ] Profile defaults applied correctly
- [ ] CloudWatch logging functional
- [ ] IAM permissions least-privilege
- [ ] All unit tests passing
- [ ] Integration test synthesizes valid CloudFormation
- [ ] Example hello handler works end-to-end
- [ ] Component Overview documentation created
- [ ] Phase Component Overview documentation updated
- [ ] User documentation: REST API guide created

**Notes**:
- Lambda proxy integration simplifies request/response handling
- Use CDK's LambdaIntegration for automatic IAM permission setup
- Consider Lambda cold start implications; document in user guide
- For Scalable, consider adding Lambda reserved concurrency
- API Gateway stage variables can be used for environment-specific config

---

### Component 1.7: REST API + App Runner Integration Construct

**Phase**: Phase 1 - Core Framework & REST API Lane

**Priority**: Must-have

**Estimated Effort**: 7-8 hours

**Owner**: AI Agent

**Dependencies**:
- Component 1.5: CDK base stack must exist
- Component 1.6: REST API construct must exist (for patterns)

**Features**:
- App Runner service creation from Dockerfile (AI Agent)
- API Gateway HTTP integration to App Runner (AI Agent)
- Health check configuration (TCP/HTTP) (AI Agent)
- Auto-scaling configuration per profile (AI Agent)
- Secrets and environment variable injection (AI Agent)
- Docker image build and push to ECR (AI Agent)

**Description**:
Implement the App Runner construct that deploys containerized services with API Gateway integration. Support Dockerfile-based deployments, configure health checks and auto-scaling per profile, handle secrets injection, and set up API Gateway HTTP proxy integration to App Runner service URLs.

**Acceptance Criteria**:
- [ ] App Runner service created from Dockerfile
- [ ] Docker image built and pushed to ECR automatically
- [ ] Health checks configured (TCP for Minimal, HTTP for Scalable)
- [ ] Auto-scaling configured per profile defaults
- [ ] Environment variables and secrets injected correctly
- [ ] API Gateway HTTP integration to App Runner URL works
- [ ] IAM roles grant least-privilege permissions
- [ ] Integration test: deploy containerized service and access via API
- [ ] Unit tests for construct configuration

**Technical Details**:
- **Files to Create/Modify**:
  - `src/aws_api_factory/constructs/compute_apprunner/__init__.py`
  - `src/aws_api_factory/constructs/compute_apprunner/service.py`
  - `src/aws_api_factory/constructs/rest_api/http_integration.py`
  - `starter/src/services/public_api/app.py`
  - `starter/src/services/public_api/Dockerfile`
  - `tests/constructs/test_apprunner.py`
  - `tests/integration/test_rest_apprunner_e2e.py`
- **Key Functions/Classes**:
  - `AppRunnerConstruct(BaseConstruct)` - creates App Runner service
  - `create_http_integration()` - sets up API Gateway HTTP integration
  - `build_and_push_image()` - handles Docker image build/push
  - `configure_health_check()`, `configure_autoscaling()` - configuration helpers
- **Human/AI Agent**: All implementation by AI Agent; Docker installed (Human prerequisite)
- **Database Changes**: N/A
- **API Endpoints**: Routes configured to proxy to App Runner
- **Dependencies**: `aws-cdk-lib` (apprunner, apigateway, ecr, iam modules)

**Detailed Implementation Requirements**:
- **File: `src/aws_api_factory/constructs/compute_apprunner/service.py`**: Implement `AppRunnerConstruct` that: 1) creates ECR repository for container images, 2) builds Docker image using DockerImageAsset from dockerfile path in config, 3) creates App Runner service with image from ECR, 4) configures health check (Minimal: TCP on port, Scalable: HTTP on /healthz), 5) sets auto-scaling (Minimal: min=1 max=10, Scalable: min=2 max=25), 6) injects environment variables from config, 7) configures secrets if using Secrets Manager, 8) creates IAM role with ECR pull permissions, 9) registers service URL as output. Apply CPU/memory from profile defaults. Enable observability configuration for Scalable.
- **File: `src/aws_api_factory/constructs/rest_api/http_integration.py`**: Implement HTTP integration for App Runner: `create_http_integration(app_runner_url)` returns HttpIntegration configured for proxy, `attach_http_integration_to_routes(api, routes, app_runner_url)` sets up API Gateway routes to proxy to App Runner. Handle path parameter forwarding. Configure integration timeout (30s). Add request/response transformations if needed for header handling.
- **File: `starter/src/services/public_api/app.py`**: Create FastAPI example: 1) FastAPI app with CORS middleware, 2) `/healthz` endpoint returning {"status": "healthy"}, 3) `/` endpoint returning welcome message, 4) example POST endpoint with Pydantic model validation, 5) proper error handling and logging, 6) environment variable reading example. Keep production-ready with structured logging and request ID tracking. Document FastAPI startup and shutdown events.
- **File: `starter/src/services/public_api/Dockerfile`**: Create multi-stage Dockerfile: 1) FROM python:3.11-slim as base, 2) install dependencies (FastAPI, uvicorn, pydantic), 3) copy app code, 4) expose port 8000, 5) CMD to run uvicorn with proper workers, 6) use non-root user, 7) optimize layers for caching. Include health check instruction. Add comments explaining each stage.
- **File: `tests/constructs/test_apprunner.py`**: Unit tests for AppRunnerConstruct: verify service created with correct CPU/memory, health check configured per profile, auto-scaling settings match profile, environment variables injected, ECR repository created, IAM role has ECR permissions, observability enabled for Scalable. Use CDK assertions to verify CloudFormation. Mock Docker image build.
- **File: `tests/integration/test_rest_apprunner_e2e.py`**: Integration test that: 1) creates factory.yaml with App Runner service config, 2) synthesizes stack with REST API + App Runner integration, 3) validates CloudFormation includes App Runner service and HTTP integration, 4) optionally builds Docker image and deploys (slow test), 5) verifies health check endpoint responds, 6) cleans up resources. Mark as integration/slow test.

**Test Requirements**:
- [ ] Unit tests for App Runner construct with various configurations
- [ ] Unit tests for HTTP integration setup
- [ ] Unit tests for health check and auto-scaling configuration
- [ ] Integration test: synthesize stack with REST + App Runner
- [ ] Integration test: build Docker image (if Docker available)
- [ ] Manual test: deploy FastAPI app and access via API Gateway
- [ ] Verify health check endpoint responds correctly
- [ ] Verify auto-scaling triggers work (load test if possible)

**Definition of Done**:
- [ ] App Runner construct implemented and tested
- [ ] Docker image build and ECR push working
- [ ] API Gateway HTTP integration functional
- [ ] Health checks and auto-scaling configured
- [ ] Profile defaults applied correctly
- [ ] All unit tests passing
- [ ] Integration test synthesizes valid CloudFormation
- [ ] FastAPI example app works end-to-end
- [ ] Component Overview documentation created
- [ ] Phase Component Overview documentation updated
- [ ] User documentation: App Runner guide created

**Notes**:
- App Runner is better for stateful services or when you need container control
- Document Lambda vs App Runner decision guide for users
- Health check path convention: always use /healthz
- App Runner cold starts are slower than Lambda; document implications
- Consider cost differences between Lambda and App Runner in documentation

---

### Component 1.8: Authentication Module (API Keys, IAM, Cognito)

**Phase**: Phase 1 - Core Framework & REST API Lane

**Priority**: Must-have

**Estimated Effort**: 8 hours

**Owner**: AI Agent

**Dependencies**:
- Component 1.6: REST API construct must exist
- Component 1.2: Configuration system must support auth config

**Features**:
- API Key authentication with usage plans (AI Agent)
- IAM (SigV4) authentication for REST API (AI Agent)
- Cognito User Pool creation and JWT authorizer (AI Agent)
- Per-route auth configuration (AI Agent)
- Auth helper utilities for Lambda handlers (AI Agent)

**Description**:
Implement complete authentication module supporting three auth modes: API Keys (with usage plans), IAM authentication (SigV4), and Cognito (User Pools with JWT authorizer). Enable per-route auth configuration, create Cognito resources when needed, and provide helper utilities for Lambda functions to validate and extract auth context.

**Acceptance Criteria**:
- [ ] API Key auth works with usage plans and rate limiting
- [ ] IAM auth works with SigV4 signing
- [ ] Cognito User Pool created with sensible defaults
- [ ] JWT authorizer validates Cognito tokens
- [ ] Per-route auth configuration enforced
- [ ] Auth helper utilities work in Lambda handlers
- [ ] Unauthenticated requests return 401/403 appropriately
- [ ] Integration test: verify each auth mode end-to-end
- [ ] Unit tests for auth construct configuration

**Technical Details**:
- **Files to Create/Modify**:
  - `src/aws_api_factory/constructs/auth/__init__.py`
  - `src/aws_api_factory/constructs/auth/api_key.py`
  - `src/aws_api_factory/constructs/auth/iam.py`
  - `src/aws_api_factory/constructs/auth/cognito.py`
  - `src/aws_api_factory/constructs/auth/helpers.py`
  - `src/aws_api_factory/utils/auth.py` (Lambda helper utilities)
  - `tests/constructs/test_auth.py`
  - `tests/integration/test_auth_e2e.py`
  - `starter/src/services/hello/auth_handler.py` (example with auth)
- **Key Functions/Classes**:
  - `ApiKeyAuthConstruct(BaseConstruct)` - creates API keys and usage plans
  - `IamAuthConstruct(BaseConstruct)` - configures IAM authorizer
  - `CognitoAuthConstruct(BaseConstruct)` - creates User Pool and authorizer
  - `apply_auth_to_method()` - applies auth to API Gateway method
  - `extract_auth_context()` - Lambda helper to get user info
- **Human/AI Agent**: All implementation by AI Agent
- **Database Changes**: N/A
- **API Endpoints**: Auth applied to routes per config
- **Dependencies**: `aws-cdk-lib` (apigateway, cognito, iam modules)

**Detailed Implementation Requirements**:
- **File: `src/aws_api_factory/constructs/auth/api_key.py`**: Implement `ApiKeyAuthConstruct` that: 1) creates API keys (one per environment or per config), 2) creates usage plan with rate limits from profile (Minimal: 1000 req/day, Scalable: 10000 req/day), 3) associates usage plan with API stage, 4) requires API key on specified methods, 5) registers API key value as output (securely). Support multiple API keys if configured. Document key rotation strategy.
- **File: `src/aws_api_factory/constructs/auth/iam.py`**: Implement `IamAuthConstruct` that: 1) configures IAM authorizer on API, 2) applies authorization type AWS_IAM to methods, 3) creates example IAM policy document showing how to grant access, 4) registers policy ARN as output. Document SigV4 signing requirements for clients.
- **File: `src/aws_api_factory/constructs/auth/cognito.py`**: Implement `CognitoAuthConstruct` that: 1) creates Cognito User Pool with email sign-in, 2) creates User Pool Client, 3) configures password policy (strong by default), 4) creates JWT authorizer for API Gateway, 5) applies authorizer to configured methods, 6) registers User Pool ID and Client ID as outputs. For Scalable, enable MFA and advanced security. Support custom domain if configured. Add example user creation script.
- **File: `src/aws_api_factory/constructs/auth/helpers.py`**: Implement helper functions: `apply_auth_to_method(method, auth_type, auth_construct)` applies appropriate authorizer to API Gateway method based on auth type, `get_auth_construct(auth_type, scope, config)` factory function to create correct auth construct, `validate_auth_config(routes, auth_configs)` validates auth references are valid.
- **File: `src/aws_api_factory/utils/auth.py`**: Implement Lambda helper utilities: `extract_auth_context(event)` returns dict with user info (API key, IAM principal, Cognito username), `require_auth(event, allowed_roles)` decorator/function to enforce auth in handlers, `get_cognito_claims(event)` extracts JWT claims. Handle all three auth types. Include error handling for invalid/missing auth.
- **File: `tests/constructs/test_auth.py`**: Unit tests for each auth construct: verify API key creation and usage plan, verify IAM authorizer configuration, verify Cognito User Pool created with correct settings, verify authorizers applied to methods correctly, test profile-specific settings (rate limits, MFA). Use CDK assertions for CloudFormation verification.
- **File: `tests/integration/test_auth_e2e.py`**: Integration tests for auth: 1) deploy API with API key auth, attempt access without key (expect 403), access with valid key (expect 200), 2) deploy API with IAM auth, attempt SigV4 signed request (requires boto3 signing), 3) deploy API with Cognito auth, create test user, get JWT token, access with token. Mark as integration/slow tests.
- **File: `starter/src/services/hello/auth_handler.py`**: Create example handler demonstrating auth usage: `def handler(event, context): auth_context = extract_auth_context(event); return {"statusCode": 200, "body": json.dumps({"message": "Authenticated!", "user": auth_context})}`. Show how to use helper utilities. Document auth context structure for each auth type.

**Test Requirements**:
- [ ] Unit tests for each auth construct type
- [ ] Unit tests for auth helper utilities
- [ ] Integration test: API key auth prevents unauthorized access
- [ ] Integration test: IAM auth with SigV4 signing
- [ ] Integration test: Cognito auth with JWT token
- [ ] Manual test: create Cognito user and obtain JWT
- [ ] Manual test: verify rate limiting works for API keys
- [ ] Verify auth context extraction in Lambda handlers

**Definition of Done**:
- [ ] All three auth modes implemented and tested
- [ ] Per-route auth configuration working
- [ ] Lambda helper utilities functional
- [ ] All unit tests passing
- [ ] Integration tests verify auth enforcement
- [ ] Example authenticated handler works
- [ ] Component Overview documentation created
- [ ] Phase Component Overview documentation updated
- [ ] User documentation: Authentication guide created
- [ ] Security best practices documented

**Notes**:
- API keys are suitable for partner APIs, not public user auth
- IAM auth is best for service-to-service communication within AWS
- Cognito is recommended for user-facing authentication
- Document when to use each auth mode in guide
- Consider adding example Postman collection for testing auth

---

### Component 1.9: Starter Template and Documentation

**Phase**: Phase 1 - Core Framework & REST API Lane

**Priority**: Must-have

**Estimated Effort**: 6-7 hours

**Owner**: AI Agent

**Dependencies**:
- All previous components (1.1-1.8) must be complete

**Features**:
- Complete starter template with examples (AI Agent)
- Getting Started guide (15-minute tutorial) (AI Agent)
- Configuration reference documentation (AI Agent)
- Module guides (REST, Lambda, App Runner, Auth) (AI Agent)
- Example projects (CRUD API, multi-service) (AI Agent)
- Troubleshooting guide (AI Agent)

**Description**:
Create comprehensive starter template and documentation that enables new users to go from zero to deployed API in under 15 minutes. Include working examples for all supported features (REST + Lambda, REST + App Runner, all auth modes), detailed configuration reference, module guides, and troubleshooting documentation.

**Acceptance Criteria**:
- [ ] Starter template has working examples for all Phase 1 features
- [ ] `factory init` creates complete, runnable project
- [ ] Getting Started guide takes user from install to deployed API
- [ ] Configuration reference documents all factory.yaml options
- [ ] Each module has dedicated guide with examples
- [ ] Example projects demonstrate common patterns
- [ ] Troubleshooting guide covers common issues
- [ ] All documentation reviewed for clarity and accuracy
- [ ] Documentation tested by following steps exactly
- [ ] Example projects deploy successfully

**Technical Details**:
- **Files to Create/Modify**:
  - `starter/factory.yaml` (comprehensive example)
  - `starter/README.md` (project-specific guidance)
  - `starter/src/services/hello/handler.py` (simple Lambda)
  - `starter/src/services/orders/handler.py` (CRUD example)
  - `starter/src/services/public_api/app.py` (FastAPI app)
  - `starter/src/services/public_api/Dockerfile`
  - `docs/getting-started.md`
  - `docs/reference/configuration.md`
  - `docs/guides/rest-api.md`
  - `docs/guides/lambda-functions.md`
  - `docs/guides/app-runner-containers.md`
  - `docs/guides/authentication.md`
  - `docs/examples/crud-api.md`
  - `docs/troubleshooting.md`
  - `README.md` (project root, comprehensive)
- **Key Functions/Classes**: N/A (documentation and templates)
- **Human/AI Agent**: All documentation by AI Agent; human reviews for clarity
- **Database Changes**: N/A
- **API Endpoints**: Examples only
- **Dependencies**: None beyond existing

**Detailed Implementation Requirements**:
- **File: `starter/factory.yaml`**: Create comprehensive example config demonstrating: minimal profile with REST + Lambda, commented options showing scalable alternatives, multiple routes with different auth modes, both Lambda and App Runner services, environment overrides example, all config sections with inline documentation. Include comments explaining each option and when to use it.
- **File: `starter/README.md`**: Write project-specific README: 1) overview of generated project structure, 2) prerequisites (AWS account, CDK, Docker), 3) quick start (validate, deploy, test), 4) how to add new services/routes, 5) how to customize configuration, 6) links to main documentation. Keep concise, focus on project-specific guidance.
- **File: `starter/src/services/orders/handler.py`**: Create CRUD example handler with: GET list orders, GET order by ID, POST create order, PUT update order, DELETE delete order. Use in-memory storage (dict) for simplicity. Demonstrate request validation, error handling, response formatting. Include docstrings. Keep production-ready patterns.
- **File: `docs/getting-started.md`**: Write 15-minute tutorial: 1) install aws-api-factory, 2) scaffold project with `factory init`, 3) review generated structure, 4) understand factory.yaml, 5) validate configuration, 6) deploy to AWS, 7) test API endpoints with curl, 8) view logs in CloudWatch, 9) modify and redeploy, 10) clean up resources. Include screenshots/terminal output examples. Add "what's next" section with links to guides.
- **File: `docs/reference/configuration.md`**: Create comprehensive config reference: document every factory.yaml option with: type, required/optional, default value, description, when to use, example. Organize by section (project, profile, apis, compute, data, secrets, observability). Include full example configs for common scenarios. Add JSON Schema reference.
- **File: `docs/guides/rest-api.md`**: Write REST API guide: 1) concepts (API Gateway, resources, methods), 2) defining routes in config, 3) path parameters and query strings, 4) request/response handling, 5) CORS configuration, 6) throttling and rate limiting, 7) custom domains (teaser for future), 8) best practices. Include multiple examples. Link to AWS API Gateway docs.
- **File: `docs/guides/lambda-functions.md`**: Write Lambda guide: 1) handler contract explained, 2) event structure, 3) context object, 4) error handling patterns, 5) logging best practices, 6) environment variables, 7) memory and timeout tuning, 8) cold starts and optimization, 9) testing locally, 10) common patterns (middleware, decorators). Include code examples.
- **File: `docs/guides/app-runner-containers.md`**: Write App Runner guide: 1) when to use App Runner vs Lambda, 2) Dockerfile best practices, 3) health check implementation, 4) environment variables and secrets, 5) auto-scaling configuration, 6) cost considerations, 7) debugging App Runner deployments, 8) custom runtimes (non-Python). Include FastAPI example walkthrough.
- **File: `docs/guides/authentication.md`**: Write auth guide: 1) comparison table (API Key vs IAM vs Cognito), 2) when to use each auth mode, 3) API Key setup and management, 4) IAM auth with SigV4 signing (Python example), 5) Cognito setup and user management, 6) testing authenticated endpoints, 7) auth in Lambda handlers (using helper utilities), 8) security best practices. Include decision tree for choosing auth.
- **File: `docs/examples/crud-api.md`**: Write CRUD API example: walk through building complete CRUD API with: multiple routes, request validation with Pydantic, error handling, DynamoDB integration (note: requires Phase 2, show in-memory alternative), authentication, logging. Include full code with explanations. Deployable end-to-end example.
- **File: `docs/troubleshooting.md`**: Create troubleshooting guide covering: CDK synthesis errors (missing dependencies, invalid config), deployment failures (IAM permissions, resource limits), runtime errors (Lambda timeouts, cold starts), authentication issues (invalid tokens, missing permissions), CloudWatch logs missing, common CloudFormation errors. For each issue: symptoms, cause, solution, prevention. Include debugging tips.
- **File: `README.md` (root)**: Write comprehensive project README: 1) compelling overview of AWS API Factory, 2) key features highlighted, 3) quick start in 5 commands, 4) when to use vs alternatives, 5) installation instructions, 6) link to documentation, 7) examples gallery, 8) contributing guidelines, 9) license, 10) badges (build status, coverage, PyPI version). Make it compelling for GitHub viewers.

**Test Requirements**:
- [ ] Follow Getting Started guide exactly, verify each step works
- [ ] Deploy each example project successfully
- [ ] Verify all code examples in documentation are syntactically correct
- [ ] Test all configuration examples by validating with CLI
- [ ] Have someone unfamiliar with project follow getting started
- [ ] Check all internal documentation links work
- [ ] Verify documentation renders correctly (Markdown, formatting)

**Definition of Done**:
- [ ] Starter template complete with all examples
- [ ] Getting Started guide tested end-to-end
- [ ] Configuration reference complete and accurate
- [ ] All module guides written and reviewed
- [ ] Example projects tested and working
- [ ] Troubleshooting guide covers common issues
- [ ] All documentation links working
- [ ] Documentation reviewed for clarity
- [ ] Root README compelling and comprehensive
- [ ] Component Overview documentation created
- [ ] Phase Component Overview documentation finalized

**Notes**:
- Documentation quality is critical for user adoption
- Use real terminal output and screenshots where helpful
- Keep examples simple but production-ready (no TODOs)
- Consider adding video walkthrough link for Getting Started
- Documentation should be versioned with releases
- Use consistent terminology throughout all docs

---

## Phase Acceptance Criteria

- [ ] Users can install aws-api-factory via pip successfully
- [ ] `factory init` scaffolds working starter project in under 30 seconds
- [ ] User deploys REST API with Lambda backend to AWS in under 15 minutes
- [ ] User deploys REST API with App Runner backend successfully
- [ ] API Key authentication prevents unauthorized access
- [ ] IAM authentication works with SigV4 signing
- [ ] Cognito authentication works with JWT tokens
- [ ] Minimal and Scalable profiles produce different CloudFormation with appropriate defaults
- [ ] Documentation enables new user to go from zero to deployed API
- [ ] All unit and integration tests pass with >85% coverage
- [ ] Zero secrets leaked in repository (pre-commit hooks prevent commits)
- [ ] CDK synthesis completes in under 10 seconds for typical config
- [ ] CloudFormation deployment completes in under 5 minutes for simple stack
- [ ] All example projects in starter template deploy successfully
- [ ] Getting Started guide tested by following steps exactly
- [ ] No placeholders or TODOs in any production code
- [ ] All documentation reviewed for accuracy and clarity

---

## Phase Dependencies

**Prerequisites (Human Setup Required)**:
- AWS Account with admin access configured
- AWS CLI installed and configured with credentials
- AWS CDK CLI installed globally (`npm install -g aws-cdk`)
- Python 3.9+ installed
- Docker installed (for App Runner testing)
- GitHub repository created
- CDK bootstrap completed in target regions (`cdk bootstrap`)

**Component Dependencies**:
- Component 1.2 depends on Component 1.1 (project structure)
- Component 1.3 depends on Component 1.2 (config system)
- Component 1.4 depends on Components 1.1, 1.2, 1.3 (CLI needs config and defaults)
- Component 1.5 depends on Components 1.1, 1.2, 1.3 (stack needs config)
- Component 1.6 depends on Components 1.5, 1.2 (REST API needs base stack)
- Component 1.7 depends on Components 1.5, 1.6 (App Runner uses REST API patterns)
- Component 1.8 depends on Components 1.6, 1.2 (Auth attaches to REST API)
- Component 1.9 depends on all previous components (documentation covers everything)

---

## Phase Risks and Mitigation

### Risk 1: CDK Complexity
**Risk**: CDK construct complexity leads to difficult-to-debug CloudFormation errors, frustrating users
**Impact**: High - users may abandon project if errors are cryptic
**Mitigation**: 
- Extensive integration tests that synthesize and validate CloudFormation
- Config validation catches errors before CDK synthesis
- Clear error messages with suggestions in CLI
- Escape hatches documented for advanced users
- Troubleshooting guide covers common CDK issues

### Risk 2: Docker Build Requirements
**Risk**: App Runner construct requires Docker build capabilities that complicate CI/CD and local development
**Impact**: Medium - some users may not have Docker or face build issues
**Mitigation**:
- Provide clear Dockerfile templates that work out-of-box
- Test with common base images (Python, Node.js)
- Document Docker installation and troubleshooting
- Make App Runner optional; users can start with Lambda-only
- Provide pre-built example images for testing

### Risk 3: Authentication Confusion
**Risk**: Authentication module configuration confusing for users unfamiliar with Cognito/IAM
**Impact**: Medium - auth is critical but complex
**Mitigation**:
- Sensible defaults that work without customization
- Clear documentation with decision tree (which auth mode?)
- Working examples for each auth mode in starter template
- Helper utilities abstract away complexity in Lambda handlers
- Dedicated authentication guide with best practices

### Risk 4: Template Maintenance
**Risk**: Starter template becomes outdated as library evolves, causing version mismatch issues
**Impact**: Low - but affects user experience
**Mitigation**:
- Automated tests that scaffold and deploy starter template
- Version starter template with library releases
- CLI validates config version compatibility
- Documentation includes migration guides for breaking changes
- Pin library version in generated pyproject.toml

### Risk 5: AWS Service Limits
**Risk**: Users hit AWS service limits (Lambda concurrency, API Gateway throttles) during deployment or testing
**Impact**: Medium - causes deployment failures
**Mitigation**:
- Document common service limits in troubleshooting guide
- Provide commands to check current limits
- Use sensible defaults that stay within free tier where possible
- Warn users before deploying resource-intensive configs
- Include instructions for requesting limit increases

### Risk 6: Testing Coverage
**Risk**: >85% test coverage requirement is ambitious for CDK constructs
**Impact**: Medium - may slow development or lead to superficial tests
**Mitigation**:
- Focus on testing business logic and config validation (easier to test)
- Use CDK assertions for construct tests (validates CloudFormation)
- Integration tests verify end-to-end workflows
- Mock AWS SDK calls in unit tests
- Exclude CDK boilerplate from coverage requirements if needed

---

## Phase Testing Strategy

### Unit Testing (Target: >85% coverage)
**Scope**: Configuration models, defaults resolution, CLI logic, construct creation logic

**Approach**:
- pytest for all Python tests
- Mock AWS CDK constructs to isolate business logic
- Use fixtures for config variations (minimal, scalable, invalid)
- Test validation error messages are helpful
- Test defaults resolution for edge cases

**Tools**: pytest, pytest-cov, pytest-mock, CDK assertions library

### Integration Testing
**Scope**: CDK synthesis, CloudFormation validation, multi-component workflows

**Approach**:
- Synthesize stacks with various configurations
- Validate CloudFormation templates match expected resources
- Test CLI commands end-to-end (without actual AWS deployment)
- Use temporary directories for file operations
- Mark as `@pytest.mark.integration` for separate execution

**Tools**: pytest, tempfile, CDK synthesis API

### End-to-End Testing (Optional, Slow)
**Scope**: Actual deployment to AWS test account, invoke endpoints, verify functionality

**Approach**:
- Deploy to isolated AWS account (ephemeral if possible)
- Test each auth mode with real requests
- Invoke Lambda functions and verify responses
- Check CloudWatch logs are created
- Clean up all resources after test
- Mark as `@pytest.mark.e2e` and `@pytest.mark.slow`

**Tools**: pytest, boto3, requests, AWS credentials

### Manual Testing Checklist
- [ ] Follow Getting Started guide step-by-step with fresh install
- [ ] Deploy REST API + Lambda with all three auth modes
- [ ] Deploy REST API + App Runner and access endpoints
- [ ] Modify config and redeploy, verify updates applied
- [ ] Check CloudWatch logs for API and Lambda
- [ ] Test `factory validate` with invalid configs, verify error messages
- [ ] Run full CLI workflow: init → validate → synth → deploy → destroy
- [ ] Test with both Minimal and Scalable profiles
- [ ] Verify pre-commit hooks prevent secrets from being committed
- [ ] Test on fresh AWS account (not development account)

---

## Phase Documentation Strategy

### Documentation Structure
```
docs/
  getting-started.md          # 15-minute tutorial (Component 1.9)
  reference/
    configuration.md          # Complete config reference (Component 1.9)
    defaults.md              # Profile defaults explained (Component 1.3)
    cli.md                   # CLI command reference (Component 1.4)
  guides/
    construct-development.md # For library contributors (Component 1.5)
    rest-api.md              # REST API usage guide (Component 1.9)
    lambda-functions.md      # Lambda guide (Component 1.9)
    app-runner-containers.md # App Runner guide (Component 1.9)
    authentication.md        # Auth modes explained (Component 1.9)
  examples/
    crud-api.md              # Complete CRUD example (Component 1.9)
  troubleshooting.md         # Common issues (Component 1.9)
  
README.md                    # Project overview (Component 1.1, 1.9)
CONTRIBUTING.md              # Development guide (Component 1.1)
```

### Developer Context Documentation
Each component creates:
- **Component Overview**: What was built, why, key decisions, usage examples
- **Phase Component Overview**: Updated with each component, tracks phase progress

### Documentation Quality Gates
- [ ] All code examples are tested and work
- [ ] All configuration examples validate successfully
- [ ] Internal links verified (no broken links)
- [ ] Consistent terminology throughout
- [ ] Screenshots/terminal output included where helpful
- [ ] Documentation reviewed by someone unfamiliar with project
- [ ] Spelling and grammar checked
- [ ] Markdown renders correctly in GitHub and docs site

---

## Phase Success Metrics

### Functional Metrics
- [ ] 100% of Phase 1 components completed and tested
- [ ] Unit test coverage >85% across all modules
- [ ] Integration tests synthesize valid CloudFormation for all scenarios
- [ ] Zero critical security findings from Bandit/Checkov scans
- [ ] Zero secrets leaked (pre-commit hooks enforced)
- [ ] CLI commands work without errors for happy path
- [ ] All example projects deploy successfully

### User Experience Metrics
- [ ] New user deploys working API in <15 minutes
- [ ] Getting Started guide can be followed without questions
- [ ] Error messages provide actionable next steps
- [ ] Configuration validation catches 90%+ of user errors before deployment
- [ ] Documentation answers common questions without support

### Performance Metrics
- [ ] Config validation completes in <100ms for typical config
- [ ] CDK synthesis completes in <10 seconds for simple stack
- [ ] CloudFormation deployment completes in <5 minutes for minimal REST+Lambda
- [ ] Pre-commit hooks run in <5 seconds

### Code Quality Metrics
- [ ] All code formatted with black (zero diffs)
- [ ] No TODO or FIXME comments in production code
- [ ] All public APIs have docstrings
- [ ] All complex logic has inline comments

---

## Post-Phase 1 Readiness Checklist

Before proceeding to Phase 2, verify:

**Functionality**:
- [ ] REST API + Lambda deployments work end-to-end
- [ ] REST API + App Runner deployments work end-to-end
- [ ] All three authentication modes function correctly
- [ ] Both Minimal and Scalable profiles produce valid stacks
- [ ] CLI commands handle errors gracefully
- [ ] Configuration validation catches common mistakes

**Quality**:
- [ ] All tests passing (unit + integration)
- [ ] Test coverage >85%
- [ ] Code quality gates passing (lint, format, type check, security scan)
- [ ] No known bugs or regressions
- [ ] Documentation complete and accurate
- [ ] Example projects tested and working

**Operations**:
- [ ] CI/CD pipeline running and passing
- [ ] Pre-commit hooks preventing secrets
- [ ] CloudFormation templates follow AWS best practices
- [ ] IAM roles use least-privilege permissions
- [ ] CloudWatch logging working for all resources

**User Readiness**:
- [ ] Getting Started guide validated with new user
- [ ] Troubleshooting guide covers observed issues
- [ ] Installation instructions tested on clean environment
- [ ] All documentation reviewed for clarity
- [ ] Example projects demonstrate Phase 1 capabilities

**Technical Debt**:
- [ ] No temporary workarounds or hacks
- [ ] No partial implementations
- [ ] No commented-out code
- [ ] Architecture supports Phase 2 additions
- [ ] Escape hatches documented and tested

---

## Notes and Recommendations

### Implementation Philosophy Reminder
**CRITICAL**: All code must be complete and production-ready. No placeholders, no "TODO" comments, and no partial implementations. Each component should be broken down small enough (2-8 hours) that it can be fully implemented in one focused session. It is better to deliver a smaller, fully working feature than a larger partially-implemented one.

### Component Execution Order
Components should be executed in order (1.1 → 1.2 → 1.3 → ... → 1.9) due to dependencies. However, within components that have minimal dependencies, work can proceed in parallel if multiple developers are available.

### Human vs AI Agent Split
- **Human Tasks**: AWS account setup, reviewing code, testing deployments, documentation review
- **AI Agent Tasks**: All coding, testing, documentation writing, configuration

### Testing Philosophy
- Test behavior, not implementation
- Integration tests are more valuable than mocking everything
- Real AWS deployments in CI catch issues unit tests miss
- Error messages are part of the user interface; test them

### Documentation Philosophy
- Documentation is code; it must be maintained
- Examples must be tested and working
- Assume reader has basic AWS knowledge but not CDK expertise
- Link to AWS docs for service-specific details
- Show, don't just tell (examples > descriptions)

### Performance Considerations
- Config loading should be fast (<100ms)
- CDK synthesis time matters for developer experience
- Lambda cold starts are user-facing; document mitigation strategies
- App Runner cold starts are slower; set expectations

### Cost Considerations
- Minimal profile should be approximately free-tier friendly
- Document actual costs for realistic workloads
- Scalable profile prioritizes reliability over cost
- Provide cost estimation guidance in documentation

### Security Considerations
- Least-privilege IAM is non-negotiable
- Never commit secrets; pre-commit hooks enforce this
- API Keys should rotate; document rotation strategy
- Cognito password policies should be strong by default
- Document security best practices in each guide

### Future Extensibility
- Phase 1 architecture must support Phase 2 additions (GraphQL, Data, LLM assistant)
- Configuration schema should be extensible without breaking changes
- Construct pattern should allow community contributions
- CLI should support plugins in future

---

## Appendix: Component Summary Table

| Component | Priority | Effort | Owner | Dependencies | Key Deliverable |
|-----------|----------|--------|-------|--------------|-----------------|
| 1.1 Project Structure | Must-have | 3-4h | AI Agent | None | Monorepo with packaging |
| 1.2 Configuration System | Must-have | 5-6h | AI Agent | 1.1 | Pydantic models + validation |
| 1.3 Profile Defaults | Must-have | 4-5h | AI Agent | 1.2 | Defaults resolution engine |
| 1.4 CLI Foundation | Must-have | 6-7h | AI Agent | 1.1, 1.2, 1.3 | Complete CLI with all commands |
| 1.5 CDK Base Stack | Must-have | 5-6h | AI Agent | 1.1, 1.2, 1.3 | Base stack + construct pattern |
| 1.6 REST + Lambda | Must-have | 7-8h | AI Agent | 1.5, 1.2 | Working REST API + Lambda |
| 1.7 REST + App Runner | Must-have | 7-8h | AI Agent | 1.5, 1.6 | Working REST API + containers |
| 1.8 Authentication | Must-have | 8h | AI Agent | 1.6, 1.2 | All three auth modes working |
| 1.9 Starter + Docs | Must-have | 6-7h | AI Agent | All previous | Complete documentation |

**Total Estimated Effort**: 52-59 hours (approximately 7-8 days for single developer)

---

## End of Phase 1 Component Breakdown

This completes the detailed component breakdown for Phase 1: Core Framework & REST API Lane. Upon completion of all components, the AWS API Factory will have a solid foundation with working REST API capabilities, multiple compute options (Lambda and App Runner), comprehensive authentication, and excellent documentation.

**Next Steps**: 
1. Begin implementation with Component 1.1
2. Follow component order strictly due to dependencies
3. Complete all acceptance criteria before moving to next component
4. Update Phase Component Overview documentation after each component
5. Conduct Post-Phase 1 Readiness Checklist before proceeding to Phase 2