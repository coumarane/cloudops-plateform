# Cloud provider identity onboarding

This guide describes the cloud-side objects required before adding a provider in **Administration**. CloudOps performs read-only inventory. It never needs owner, administrator, or write permissions for discovery.

## Provider support


| Provider        | Platform | Cloud-side identity                                       | Live validation and inventory                        |
| ----------------- | ---------- | ----------------------------------------------------------- | ------------------------------------------------------ |
| AWS             | EKS      | IAM role assumed through AWS STS                          | Supported                                            |
| Alibaba Cloud   | ACK      | RAM role assumed through Alibaba Cloud STS                | Supported                                            |
| Microsoft Azure | AKS      | Managed identity, workload identity, or service principal | Configuration only; Azure adapter is not implemented |

## Common model

Every supported live provider needs two separate identities:

1. **Caller identity**: the identity used by the CloudOps runtime to request temporary credentials.
2. **Target inventory role**: the read-only role in the cloud account or subscription that CloudOps assumes.

The target role has a trust policy that names the caller. The caller also needs permission to assume that target role. This prevents direct, long-lived administrator credentials from being used for inventory.

Create one target role per cloud account. Use separate read-only roles for non-production and production accounts. Never put access keys, client secrets, private keys, or kubeconfig content in this repository or in an account description.

## AWS EKS

### Objects to create

Create these IAM objects in the AWS account that owns the EKS clusters:

1. An IAM role named `CloudOpsDiscoveryRole`.
2. A trust policy that permits the CloudOps caller role or user to use `sts:AssumeRole`.
3. A read-only permission policy attached to `CloudOpsDiscoveryRole`.
4. An `sts:AssumeRole` permission attached to the CloudOps caller identity.
5. An EKS access entry (or legacy `aws-auth` mapping) and Kubernetes read-only RBAC if CloudOps will collect Kubernetes workload health.

Create the role from **AWS Console -> IAM -> Roles -> Create role -> Custom trust policy**. IAM Identity Center is useful for human workforce access but is not where this target inventory role is created.

### Trust policy

Replace the placeholder with the exact caller role or user that supplies CloudOps' base AWS credentials. Prefer a dedicated runner role over an IAM user.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:role/CloudOpsRunner"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

For a third-party-operated CloudOps deployment, add a unique `sts:ExternalId` condition to the trust policy and configure the same value in CloudOps. Do not use an external ID as a password; AWS does not treat it as a secret.

### Target role permissions

On **Add permissions**, select **Create inline policy**. Do not attach `AdministratorAccess`. Avoid the broad AWS managed `ReadOnlyAccess` policy: CloudOps needs only the following starting permissions for EKS discovery, optional ACM certificate discovery, and connection validation.

Attach this policy to the new **target** role, `CloudOpsDiscoveryRole`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EksInventory",
      "Effect": "Allow",
      "Action": [
        "eks:ListClusters",
        "eks:DescribeCluster"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AcmCertificateInventory",
      "Effect": "Allow",
      "Action": [
        "acm:ListCertificates",
        "acm:DescribeCertificate"
      ],
      "Resource": "*"
    },
    {
      "Sid": "S3BucketInventory",
      "Effect": "Allow",
      "Action": "s3:ListAllMyBuckets",
      "Resource": "*"
    },
    {
      "Sid": "IdentityCheck",
      "Effect": "Allow",
      "Action": "sts:GetCallerIdentity",
      "Resource": "*"
    }
  ]
}
```

Remove the `AcmCertificateInventory` statement when CloudOps must not scan ACM certificates.

The **caller** identity, such as `CloudOpsRunner`, needs only permission to assume the target role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": "arn:aws:iam::123456789012:role/CloudOpsDiscoveryRole"
    }
  ]
}
```

The broader source-derived policy in [aws-emea-dev-iam.md](aws-emea-dev-iam.md) is for a CloudOps runtime that also reads its connection configuration from AWS Secrets Manager. Attach it to the caller/runtime identity only when that AWS Secrets Manager integration is enabled; do not attach it to `CloudOpsDiscoveryRole` by default.

### Values for Administration

Select **AWS -> AssumeRole**, then enter the target account ID, the logical and AWS regions, and the target role ARN:

```text
arn:aws:iam::123456789012:role/CloudOpsDiscoveryRole
```

The Docker API container must also receive the caller identity credentials through a supported runtime mechanism, such as a workload role, an instance profile, or a mounted AWS profile for local development. The target role ARN alone cannot authenticate a local container.

For local Docker with IAM Identity Center, configure and log in to a named SSO profile on the host, then launch the optional Compose override. The override mounts `~/.aws` read-only into only the API, worker, and scheduler containers.

```bash
aws configure sso --profile cloudops
aws sso login --profile cloudops
CLOUDOPS_AWS_PROFILE=cloudops docker compose \
  -f infrastructure/docker-compose.yml \
  -f infrastructure/docker-compose.aws-sso.yml \
  up -d --force-recreate api worker beat
```

The SSO cache expires. Run `aws sso login --profile cloudops` again when CloudOps reports expired AWS credentials, then recreate the three services with the same command.

Validate with a non-production account first:

```bash
aws sts assume-role \
  --role-arn arn:aws:iam::123456789012:role/CloudOpsDiscoveryRole \
  --role-session-name cloudops-validation
```

See the [AWS IAM role guide](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-user.html) and [EKS access documentation](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html).

## Alibaba Cloud ACK

### Objects to create

Create these RAM objects in the Alibaba Cloud account that owns the ACK clusters:

1. A RAM role named `CloudOpsInventoryReadOnly` with trusted entity type **Alibaba Cloud Account**.
2. A read-only RAM policy attached to that role.
3. A dedicated RAM caller user or role with permission to call `sts:AssumeRole` on the target RAM role.
4. ACK Kubernetes RBAC granting only the read operations needed for health collection.

In the RAM console, open **Identity Management -> Roles -> Create Role**, select **Alibaba Cloud Account**, then select the current account or enter the separate CloudOps caller account for cross-account access. The target role's trust policy and the caller policy must both allow role assumption.

### Target role permissions

Use the complete policy in [alibaba-china-ram.md](alibaba-china-ram.md). It grants ACK cluster discovery, CAS certificate discovery, and STS caller identity, with no mutation actions.

The caller identity needs this additional policy, with the target account ID substituted:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": "acs:ram::<target-account-id>:role/CloudOpsInventoryReadOnly"
    }
  ]
}
```

### Values for Administration

Select **Alibaba Cloud -> RAM** or **STS**, then enter the account ID, `China`, `cn-hangzhou`, and the target RAM role ARN. Provide the caller AccessKey only through the configured secret backend or runtime environment; it is used solely to obtain a short-lived STS token and must never be committed.

See [Alibaba Cloud RAM role creation](https://help.aliyun.com/en/ram/create-a-ram-role-and-authorize-it) and [cross-account RAM role access](https://help.aliyun.com/en/ram/use-cases/use-a-ram-role-to-grant-permissions-across-alibaba-cloud-accounts).

## Microsoft Azure AKS

Azure appears in the Administration provider wizard so its organization, subscription ID, region, and intended identity pattern can be recorded. **CloudOps does not yet include an Azure adapter.** Validation, AKS discovery, health scans, and certificate scans are intentionally unavailable for Azure.

Do not create a production service principal or grant Azure roles for CloudOps until the Azure adapter is delivered. When it is implemented, the preferred deployment identity will be:

1. **Managed identity** when CloudOps runs on an Azure-hosted workload.
2. **Workload identity federation** when CloudOps runs on Kubernetes with Microsoft Entra ID federation.
3. **Service principal with a certificate** only when the first two options are unavailable; avoid client secrets where possible.

The future Azure target identity will need subscription-level read access, AKS cluster-user access, and Kubernetes read-only RBAC. Exact role assignments will be documented with the adapter because Azure permissions must match the operations it implements.

References: [AKS identity concepts](https://learn.microsoft.com/en-us/azure/aks/concepts-identity) and [AKS managed identities](https://learn.microsoft.com/en-us/azure/aks/managed-identity-overview).

## Before selecting Validate

Confirm all of the following:

- The target role trusts the exact CloudOps caller identity.
- The caller identity has permission to assume the target role.
- The target role has only read permissions required for the selected inventory features.
- The CloudOps runtime has base credentials for the caller identity.
- The account ID and cloud region in Administration match the target account.
- Kubernetes access is configured only if health collection is required.

Use a non-production account first. A successful validation confirms the cloud identity; a successful discovery confirms the provider permissions and cluster access.
