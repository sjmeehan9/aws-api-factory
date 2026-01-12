# AWS API Factory

[![CI](https://github.com/seanmeehan/aws-api-factory/actions/workflows/ci.yml/badge.svg)](https://github.com/seanmeehan/aws-api-factory/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**AWS API Factory** is an open-source, config-driven "factory pattern" built with the **AWS CDK (Python)** that transforms your business logic into **production-ready APIs** on AWS.

## ✨ Features

- 🚀 **Config-Driven Deployment** — Define your API with a simple YAML file
- 🔧 **Two Profiles** — Choose between `minimal` (cost-optimized) or `scalable` (production-ready)
- 🌐 **REST APIs** — Amazon API Gateway with Lambda or App Runner backends
- � **Authentication** — API Keys, IAM, or Cognito out of the box
- 📊 **GraphQL APIs** — AWS AppSync with Lambda and DynamoDB resolvers *(Coming Soon)*
- 📦 **Data Layer** — DynamoDB, S3, and Aurora Serverless v2 support *(Coming Soon)*
- 🤖 **AI Assistant** — Optional LLM-powered adapter code generation *(Coming Soon)*

## 🚀 Quick Start

### Installation

```bash
pip install aws-api-factory
```

### Create a New Project

```bash
# Scaffold a new project
factory init my-api

cd my-api
```

### Define Your API

Edit `factory.yaml`:

```yaml
project:
  name: my-api
  envs: [dev, prod]

profile: minimal

apis:
  rest:
    enabled: true
    routes:
      - path: /hello
        methods: [GET]
        service: hello
        auth: none

compute:
  lambda:
    enabled: true
    services:
      hello:
        entry: src/services/hello/handler.py:handler
```

### Deploy

```bash
# Validate your configuration
factory validate

# Deploy to AWS
factory deploy dev
```

That's it! Your REST API is now live on AWS. 🎉

## 📋 Requirements

- **Python** 3.12 or higher
- **AWS CDK CLI** (`npm install -g aws-cdk`)
- **AWS Account** with credentials configured — See [AWS Setup Guide](docs/guides/aws-setup.md)
- **Docker** (optional, for App Runner deployments)

## 🛠️ Development Setup

```bash
# Clone the repository
git clone https://github.com/seanmeehan/aws-api-factory.git
cd aws-api-factory

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode with all dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest
```

## 📖 Documentation

- [Getting Started Guide](docs/getting-started.md) — Deploy your first API in 15 minutes
- [AWS Setup Guide](docs/guides/aws-setup.md) — Configure AWS credentials and profiles
- [Configuration Reference](docs/reference/configuration.md) — All `factory.yaml` options
- [REST API Guide](docs/guides/rest-api.md) — API Gateway and routing
- [Lambda Functions Guide](docs/guides/lambda-functions.md) — Handler patterns
- [App Runner Guide](docs/guides/app-runner-containers.md) — Container deployments
- [Authentication Guide](docs/guides/authentication.md) — API Keys, IAM, Cognito
- [CRUD API Example](docs/examples/crud-api.md) — Complete working example
- [Troubleshooting](docs/troubleshooting.md) — Common issues and solutions

## 🏗️ Project Structure

```
aws-api-factory/
├── src/aws_api_factory/     # Core library
│   ├── cli/                 # CLI commands
│   ├── config/              # Configuration models
│   ├── constructs/          # CDK constructs
│   └── templates/           # Scaffold templates
├── starter/                 # Starter template
├── tests/                   # Test suite
└── docs/                    # Documentation
```

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built with [AWS CDK](https://aws.amazon.com/cdk/), [Pydantic](https://pydantic.dev/), and [Click](https://click.palletsprojects.com/).
