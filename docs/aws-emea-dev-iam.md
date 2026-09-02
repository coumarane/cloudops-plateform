# AWS multi-account IAM — read-only inventory

Phase 4 scans EKS and ACM in every configured AWS account (AMER, EMEA, APAC NonProd and Prod). The same adapter is used for all accounts; region and account IDs come from topology, not from this policy. The identity policy below was generated with IAM Policy Autopilot from the adapter and worker source (do not hand-author this policy from memory):

```bash
uvx iam-policy-autopilot@latest generate-policies \
  apps/api/app/providers/aws/auth.py \
  apps/api/app/providers/aws/client.py \
  apps/api/app/providers/aws/eks.py \
  apps/api/app/providers/aws/acm.py \
  apps/api/app/providers/aws/k8s.py \
  apps/worker/tasks/aws_cluster_discovery.py \
  apps/worker/tasks/aws_cluster_health.py \
  apps/worker/tasks/aws_certificate_scan.py \
  --pretty \
  --service-hints eks acm sts secretsmanager
```

Generated identity policy (Autopilot 0.3.0):

```json
{
  "Id": "IamPolicyAutopilot",
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["acm:DescribeCertificate"],
      "Resource": ["arn:*:acm:*:*:certificate/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["acm:ListCertificates"],
      "Resource": ["*"]
    },
    {
      "Effect": "Allow",
      "Action": ["eks:DescribeCluster"],
      "Resource": ["arn:*:eks:*:*:cluster/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["eks:ListClusters"],
      "Resource": ["*"]
    },
    {
      "Effect": "Allow",
      "Action": ["kms:Decrypt"],
      "Resource": ["arn:*:kms:*:*:key/*"],
      "Condition": {
        "StringEquals": {
          "kms:ViaService": ["secretsmanager.*.amazonaws.com"]
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": ["arn:*:secretsmanager:*:*:secret:*"]
    },
    {
      "Effect": "Allow",
      "Action": [
        "sts:AssumeRole",
        "sts:SetContext",
        "sts:SetSourceIdentity",
        "sts:TagSession"
      ],
      "Resource": [
        "arn:*:iam::*:role/*",
        "arn:*:sts::*:self"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["sts:GetCallerIdentity"],
      "Resource": ["*"]
    }
  ]
}
```

Attach this (or a tighter copy with explicit account IDs and regions) to the CloudOps scanner identity. Each topology account then uses STS AssumeRole into a **read-only** inventory role (`CLOUDOPS_AWS_{REGION}_{NONPROD|PROD}_ROLE_ARN`). Prefer IRSA / instance profile / workstation profile over long-lived access keys. Never store access keys in PostgreSQL. Prod accounts (NPD/PRD) are scanned read-only; no mutate APIs are called.

Kubernetes API access is not an IAM action. Grant each assumed role an EKS access entry (or `aws-auth` mapping) plus read-only RBAC: `get`/`list` on `nodes`, `pods`, `deployments`, and `jobs`.

## What remains mocked

Live adapters replace mock data **only** after a successful scan of that AWS account/environment. Unscanned cells keep mock inventory.

Still mocked:

- Alibaba China — all environments
- Applications, secrets, health checks, deployments, pipelines, GitHub, alerts, audit, and administration catalogs
- Destructive AWS actions (none are implemented)
- Any AWS cell whose last discovery has not succeeded
