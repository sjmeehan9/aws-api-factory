# Profile Defaults Reference

AWS API Factory uses **two deployment profiles** to provide opinionated defaults:

- **Minimal**: Cost-effective, lower ops overhead, suitable for development, prototyping, and low-traffic applications
- **Scalable**: Production-ready, higher resilience, stronger observability, designed for production workloads

## When to Use Each Profile

### Choose Minimal When:
- Learning AWS API Factory or prototyping
- Building development or staging environments
- Running low-traffic applications (< 100 requests/minute)
- Optimizing for cost during early development
- Building internal tools with limited users

### Choose Scalable When:
- Deploying production workloads
- Handling high traffic (> 100 requests/minute)
- Requiring high availability and resilience
- Meeting compliance or audit requirements
- Operating customer-facing APIs

## Defaults Comparison

### Lambda Compute

| Setting | Minimal | Scalable | Rationale |
|---------|---------|----------|-----------|
| `memory_mb` | 512 | 1024 | Scalable provides more headroom for production traffic |
| `timeout_s` | 30 | 60 | Longer timeout for complex operations in production |
| `reserved_concurrency` | None | 10 | Scalable ensures consistent performance under load |

**Cost Impact**: Minimal uses ~50% less Lambda memory, reducing costs proportionally.

### API Gateway (REST)

| Setting | Minimal | Scalable | Rationale |
|---------|---------|----------|-----------|
| `throttle_rate` | None | 1000 req/s | Scalable protects backends from traffic spikes |
| `throttle_burst` | None | 2000 | Handles burst traffic while maintaining protection |
| `logging_level` | INFO | INFO | Both profiles log important events |
| `metrics_enabled` | false | true | Scalable enables detailed CloudWatch metrics |
| `tracing_enabled` | false | true | Scalable enables X-Ray distributed tracing |

**Cost Impact**: Minimal avoids CloudWatch detailed metrics costs (~$0.30/metric/month).

### App Runner

| Setting | Minimal | Scalable | Rationale |
|---------|---------|----------|-----------|
| `cpu` | 1 vCPU | 2 vCPU | Scalable handles more concurrent requests |
| `memory` | 2 GB | 4 GB | More memory for larger workloads |
| `min_instances` | 1 | 2 | Scalable maintains availability during deployments |
| `max_instances` | 10 | 25 | Higher scaling ceiling for production traffic |
| `healthcheck_protocol` | TCP | HTTP | Scalable validates application readiness |

**Cost Impact**: Scalable runs 2x the minimum instances, approximately doubling baseline costs.

### DynamoDB

| Setting | Minimal | Scalable | Rationale |
|---------|---------|----------|-----------|
| `billing_mode` | PAY_PER_REQUEST | PAY_PER_REQUEST | On-demand billing for both profiles |
| `pitr_enabled` | false | true | Scalable enables Point-in-Time Recovery |
| `alarms_enabled` | false | true | Scalable monitors table health |

**Cost Impact**: PITR adds ~25% to storage costs but enables recovery from accidental deletes.

### Aurora Serverless v2

| Setting | Minimal | Scalable | Rationale |
|---------|---------|----------|-----------|
| `min_acu` | 0.5 | 0.5 | Both can scale to minimum capacity |
| `max_acu` | 8 | 16 | Scalable handles higher peak loads |
| `backup_retention_days` | 1 | 7 | Longer backup retention for production |
| `deletion_protection` | false | true | Prevents accidental production database deletion |

**Cost Impact**: Higher max ACU only impacts cost during peak usage. Longer backup retention adds ~$0.02/GB/day.

### S3 Buckets

| Setting | Minimal | Scalable | Rationale |
|---------|---------|----------|-----------|
| `versioning_enabled` | false | true | Scalable protects against accidental overwrites |
| `encryption_enabled` | true | true | Always encrypted for security |
| `lifecycle_enabled` | false | true | Scalable manages storage costs over time |

**Cost Impact**: Versioning increases storage costs if objects are frequently updated.

### Observability

| Setting | Minimal | Scalable | Rationale |
|---------|---------|----------|-----------|
| `level` | basic | enhanced | Scalable provides full observability stack |
| `tracing_enabled` | false | true | X-Ray tracing for request flow analysis |
| `alarms_enabled` | false | true | CloudWatch alarms for proactive monitoring |
| `dashboards_enabled` | false | true | Pre-built dashboards for operations |
| `log_retention_days` | 7 | 30 | Longer retention for troubleshooting |

**Cost Impact**: Enhanced observability can add $20-100/month depending on request volume.

### Secrets Management

| Setting | Minimal | Scalable | Rationale |
|---------|---------|----------|-----------|
| `provider` | ssm | secrets_manager | Scalable uses Secrets Manager for rotation |

**Cost Impact**: Secrets Manager costs $0.40/secret/month vs SSM Parameter Store (free for standard parameters).

## Estimated Monthly Costs

These are rough estimates for typical usage patterns:

| Profile | Estimated Cost | Use Case |
|---------|---------------|----------|
| **Minimal** | $5-50/month | Development, low-traffic apps |
| **Scalable** | $100-500+/month | Production, scales with traffic |

Actual costs depend heavily on request volume, data storage, and regional pricing.

## Overriding Defaults

User-specified values **always override profile defaults**. You can mix and match:

```yaml
# Use minimal profile but with higher Lambda memory
profile: minimal

compute:
  lambda:
    services:
      my-service:
        entry: src/handler.py:handler
        memory_mb: 2048  # Overrides minimal default of 512
        timeout_s: auto   # Uses minimal default of 30
```

### The "auto" Value

Use `auto` to explicitly request profile defaults:

```yaml
compute:
  lambda:
    services:
      my-service:
        entry: src/handler.py:handler
        memory_mb: auto  # Resolves to 512 (minimal) or 1024 (scalable)
        timeout_s: auto  # Resolves to 30 (minimal) or 60 (scalable)
```

## Viewing Resolved Defaults

Use the CLI to see what defaults will be applied:

```bash
# Show resolved configuration
factory validate --show-resolved

# Show what defaults were applied
factory validate --explain
```

## Programmatic Access

```python
from aws_api_factory.config import (
    load_config,
    resolve_config,
    resolve_config_with_explanation,
    get_defaults,
    compare_profiles,
    ProfileEnum,
)

# Load and resolve config
config = load_config("factory.yaml")
resolved = resolve_config(config)

# Get explanation of applied defaults
resolved, explanation = resolve_config_with_explanation(config)
print(explanation)

# Get raw defaults for a profile
defaults = get_defaults(ProfileEnum.SCALABLE)
print(f"Scalable Lambda memory: {defaults.lambda_.memory_mb}")

# Compare profiles
diffs = compare_profiles()
print(diffs["lambda"])  # {'memory_mb': (512, 1024), ...}
```

## Best Practices

1. **Start with Minimal** for development and testing
2. **Switch to Scalable** when deploying to production
3. **Override specific values** rather than fighting the profile
4. **Review resolved config** before deploying with `factory validate`
5. **Use environment-specific configs** for different profiles per environment:
   ```
   factory.yaml           # base config (minimal)
   factory.prod.yaml      # production overrides (scalable)
   ```

## Migration Path

When moving from Minimal to Scalable:

1. Update `profile: scalable` in your config
2. Run `factory validate --explain` to see what will change
3. Review the changes, especially:
   - Throttle limits (may affect high-traffic endpoints)
   - Reserved concurrency (may limit scaling)
   - PITR and deletion protection (may prevent cleanup)
4. Deploy to a staging environment first
5. Monitor for any unexpected behavior
