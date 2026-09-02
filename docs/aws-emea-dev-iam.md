# AWS EMEA NonProd DEV — IAM permissions

Phase 3 reads EKS and ACM in `eu-west-1` only. The identity policy below was generated with IAM Policy Autopilot from the adapter and worker source (do not hand-author this policy from memory):

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
  --region eu-west-1 \
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
      "Resource": ["arn:aws:acm:eu-west-1:*:certificate/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["acm:ListCertificates"],
      "Resource": ["*"]
    },
    {
      "Effect": "Allow",
      "Action": ["eks:DescribeCluster"],
      "Resource": ["arn:aws:eks:eu-west-1:*:cluster/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["eks:ListClusters"],
      "Resource": ["*"]
    },
    {
      "Effect": "Allow",
      "Action": ["kms:Decrypt"],
      "Resource": ["arn:aws:kms:eu-west-1:*:key/*"],
      "Condition": {
        "StringEquals": {
          "kms:ViaService": ["secretsmanager.eu-west-1.amazonaws.com"]
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": ["arn:aws:secretsmanager:eu-west-1:*:secret:*"]
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
        "arn:aws:iam::*:role/*",
        "arn:aws:sts::*:self"
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

Scope the generated ARNs to the NonProd EMEA account and the CloudOps read-only role before attaching. Prefer IRSA / instance profile / workstation profile assumption over long-lived access keys. Never store access keys in PostgreSQL.

Kubernetes API access is not an IAM action. Grant the assumed role an EKS access entry (or `aws-auth` mapping) plus read-only RBAC: `get`/`list` on `nodes`, `pods`, `deployments`, and `jobs`.

## What remains mocked

Live adapters replace mock data **only** after a successful AWS EMEA DEV discovery (clusters/dashboard cell) or certificate scan. Until then the console still shows the mock `eu-west-1-dev-k8s` cluster.

Still mocked:

- AWS AMER — all environments
- AWS APAC — all environments
- AWS EMEA INT/TST, UAT, NPD, and PRD
- Alibaba China — all environments
- Applications, secrets, health checks, deployments, pipelines, GitHub, alerts, audit, and administration catalogs
- Destructive AWS actions (none are implemented)
