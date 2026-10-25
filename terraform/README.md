# RentManager Terraform Infrastructure

Provisions RentManager on AWS: EKS, RDS (Postgres 17), ElastiCache (Redis 7), S3, ECR, CI/CD (GitHub OIDC), Route53 DNS, CloudWatch observability.

## Prerequisites

- Terraform >= 1.5
- AWS CLI configured (`aws configure`)
- AWS account with admin access

## Deploy Sequence

Resources must be deployed in this order (some depend on others):

```
1. bootstrap     → S3 state bucket + DynamoDB locks (run once, ever)
2. shared        → ECR repos + GitHub OIDC provider (run once per account)
3. dev or prod   → Full environment (VPC, EKS, RDS, Redis, DNS, etc.)
```

### 1. Bootstrap (once)

Creates S3 bucket and DynamoDB table for remote state:

```bash
cd terraform/bootstrap
terraform init
terraform apply
```

### 2. Shared resources (once)

Creates ECR container registries and GitHub OIDC provider — shared across all environments:

```bash
cd terraform/environments/shared
terraform init
terraform apply
```

### 3. Deploy an environment

```bash
cd terraform/environments/dev   # or prod
# Edit terraform.tfvars — set domain_name, alert_email
terraform init
terraform plan
terraform apply
```

### 4. Connect to EKS

```bash
aws eks update-kubeconfig --name rm-dev --region ap-south-1
kubectl get nodes
```

### 5. Destroy (reverse order)

```bash
# Destroy environment first
cd terraform/environments/dev
terraform destroy

# Then shared (only if tearing down everything)
cd terraform/environments/shared
terraform destroy

# Then bootstrap (only if done entirely)
cd terraform/bootstrap
terraform destroy
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  AWS Account                                            │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────┐  │
│  │  Bootstrap   │  │   Shared    │  │  Environment   │  │
│  │             │  │             │  │  (dev / prod)  │  │
│  │ S3 state    │  │ ECR repos   │  │ VPC + subnets  │  │
│  │ DynamoDB    │  │ GitHub OIDC │  │ EKS cluster    │  │
│  │ locks       │  │             │  │ RDS Postgres   │  │
│  └─────────────┘  └──────┬──────┘  │ ElastiCache    │  │
│                          │         │ S3 uploads     │  │
│                          │         │ CI/CD role     │  │
│                   remote_state     │ Route53 DNS    │  │
│                          │         │ CloudWatch     │  │
│                          └────────►│                │  │
│                                    └────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Module Reference

| Module | Purpose | Created In |
|--------|---------|------------|
| `bootstrap` | S3 + DynamoDB state backend | bootstrap/ |
| `networking` | VPC, subnets (public/private/isolated), NAT, security groups | dev, prod |
| `eks` | EKS cluster, managed node groups, IRSA, addons | dev, prod |
| `rds` | PostgreSQL 17 on RDS, Secrets Manager password | dev, prod |
| `elasticache` | Redis 7 on ElastiCache, auth token in Secrets Manager | dev, prod |
| `s3` | App uploads bucket (replaces MinIO) | dev, prod |
| `ecr` | Container registries for backend + frontend | shared |
| `cicd` | GitHub Actions deploy IAM role (per-env) | dev, prod |
| `dns` | Route53 hosted zone + subdomain records | dev, prod |
| `observability` | CloudWatch log groups, metric alarms, SNS alerts | dev, prod |

## Why "shared"?

Some AWS resources are account-wide singletons:

- **ECR repos** — same images used by both dev and prod (different tags)
- **GitHub OIDC provider** — one per identity URL per AWS account

These live in `environments/shared/` with their own state file. Dev and prod read shared outputs via `terraform_remote_state`.

## Environment Comparison

| Param | Dev | Prod |
|-------|-----|------|
| VPC CIDR | 10.0.0.0/16 | 10.1.0.0/16 |
| EKS nodes | 1x t3.medium | 2x t3.large |
| RDS | db.t4g.micro, single-AZ | db.t4g.small, multi-AZ |
| Redis | cache.t4g.micro, 1 node | cache.t4g.small, 2 nodes |
| NAT | single gateway | HA (per AZ) |
| Subdomain | rm-dev.mepant.com | rm-prod.mepant.com |
| Deletion protection | off | on |

## Directory Structure

```
terraform/
├── bootstrap/              # State backend (run once)
├── modules/
│   ├── networking/         # VPC, subnets, NAT, SGs
│   ├── eks/                # Cluster, nodes, IRSA
│   ├── rds/                # PostgreSQL
│   ├── elasticache/        # Redis
│   ├── s3/                 # Upload bucket
│   ├── ecr/                # Container registries
│   ├── cicd/               # GitHub deploy role
│   ├── dns/                # Route53
│   └── observability/      # CloudWatch, SNS
└── environments/
    ├── shared/             # Account-wide: ECR + OIDC
    ├── dev/                # Dev config + tfvars
    └── prod/               # Prod config + tfvars
```

## Cost Estimate (Monthly)

| Resource | Dev | Prod |
|----------|-----|------|
| EKS control plane | $73 | $73 |
| EC2 nodes | ~$30 | ~$120 |
| RDS | ~$15 | ~$50 |
| ElastiCache | ~$12 | ~$25 |
| NAT Gateway | ~$32 | ~$96 |
| S3/ECR | ~$2 | ~$5 |
| Route53 | ~$0.50 | ~$0.50 |
| **Total** | **~$165** | **~$370** |

## Configuration

Edit `terraform.tfvars` in each environment before applying:

| Variable | Description | Example |
|----------|-------------|---------|
| `aws_region` | AWS region | `ap-south-1` |
| `environment` | Environment name | `dev` or `prod` |
| `vpc_cidr` | VPC CIDR block | `10.0.0.0/16` |
| `availability_zones` | AZs to use | `["ap-south-1a", "ap-south-1b", "ap-south-1c"]` |
| `domain_name` | Root domain for Route53 | `mepant.com` |
| `subdomain` | Subdomain prefix | `rm-dev` |
| `alert_email` | CloudWatch alarm email | `you@example.com` |
