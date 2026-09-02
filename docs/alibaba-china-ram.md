# Alibaba China RAM — read-only inventory

Phase 5 scans ACK and Alibaba SSL Certificates Service (CAS) in China NonProd and Prod. The same Alibaba adapter is used for both accounts. Account IDs, RAM roles, and AccessKey **references** come from topology and environment variables. AccessKey Secrets are never stored in PostgreSQL.

Prefer RAM role assumption (`sts:AssumeRole`) from a dedicated CloudOps identity. The AccessKey ID/Secret referenced by `CLOUDOPS_ALIBABA_*` should belong to that identity, not to a long-lived application user in the target account.

## Required RAM permissions (target accounts)

Attach a read-only policy to the assumed role in each China account (`alibaba-china-nonprod`, `alibaba-china-prod`):

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cs:DescribeClustersV1",
        "cs:DescribeClusterDetail",
        "cs:DescribeClusterUserKubeconfig",
        "cs:DescribeClusterResources"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cas:ListUserCertificateOrder",
        "cas:DescribeUserCertificateDetail"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

The CloudOps caller identity additionally needs:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": [
        "acs:ram::<nonprod-account-id>:role/CloudOpsInventoryReadOnly",
        "acs:ram::<prod-account-id>:role/CloudOpsInventoryReadOnly"
      ]
    }
  ]
}
```

Kubernetes RBAC on each ACK cluster should allow the kubeconfig user to **get/list** (not mutate):

- nodes
- pods
- deployments
- statefulsets
- jobs
- ingresses
- secrets (TLS certificates only; CloudOps parses `tls.crt` and never stores `tls.key`)

## Configuration

| Variable | Purpose |
| --- | --- |
| `CLOUDOPS_ALIBABA_NONPROD_ACCOUNT_ID` | Expected NonProd account ID |
| `CLOUDOPS_ALIBABA_NONPROD_ROLE_ARN` | RAM role ARN to assume in NonProd |
| `CLOUDOPS_ALIBABA_NONPROD_ACCESS_KEY_ID` | AccessKey **ID** (or env name referenced by topology) |
| `CLOUDOPS_ALIBABA_NONPROD_ACCESS_KEY_SECRET` | AccessKey Secret. Runtime only. Never persist. |
| `CLOUDOPS_ALIBABA_PROD_ACCOUNT_ID` | Expected Prod account ID |
| `CLOUDOPS_ALIBABA_PROD_ROLE_ARN` | RAM role ARN to assume in Prod |
| `CLOUDOPS_ALIBABA_PROD_ACCESS_KEY_ID` | Prod AccessKey ID |
| `CLOUDOPS_ALIBABA_PROD_ACCESS_KEY_SECRET` | Prod AccessKey Secret. Runtime only. |
| `CLOUDOPS_ALIBABA_ACCOUNT_ID` / `_ROLE_ARN` / `_ACCESS_KEY_ID` / `_ACCESS_KEY_SECRET` | Legacy NonProd fallbacks |
| `CLOUDOPS_ALIBABA_CLOUD_REGION` | ACK region, default `cn-hangzhou` |
| `CLOUDOPS_ALIBABA_SCAN_CONCURRENCY` | Max parallel account scans (default 2) |
| `CLOUDOPS_ALIBABA_CLUSTER_ENVIRONMENT_TAG` | Cluster tag used to map DEV/TST/UAT/NPD/PRD (default `Environment`) |

PostgreSQL stores only:

- credential reference (`env:CLOUDOPS_ALIBABA_NONPROD_ACCESS_KEY_SECRET`)
- account id / alias / environment
- fingerprint of the AccessKey **ID**
- last validation timestamp and status

NPD and PRD remain read-only. Discovery and monitoring only.
