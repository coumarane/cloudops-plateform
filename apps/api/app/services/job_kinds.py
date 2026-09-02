KIND_DISCOVERY = "aws-cluster-discovery"
KIND_HEALTH = "aws-health-scan"
KIND_CERTIFICATES = "aws-certificate-scan"
KIND_ALIBABA_VALIDATION = "alibaba-account-validation"
KIND_ALIBABA_DISCOVERY = "alibaba-cluster-discovery"
KIND_ALIBABA_HEALTH = "alibaba-health-scan"
KIND_ALIBABA_CERTIFICATES = "alibaba-certificate-discovery"
KIND_ALIBABA_CERT_EXPIRY = "alibaba-certificate-expiry-scan"
KIND_CREDENTIAL_VALIDATE = "credential-validate"
KIND_CREDENTIAL_ROTATION_SCAN = "credential-rotation-status-scan"
KIND_CERTIFICATE_DISCOVERY = "certificate-discovery"
KIND_CERTIFICATE_EXPIRY = "certificate-expiry-scan"
KIND_CERTIFICATE_ENDPOINT = "certificate-endpoint-validation"
KIND_CERTIFICATE_ALERTS = "certificate-alert-evaluation"
KIND_CERTIFICATE_VALIDATE = "certificate-validate"
KIND_GITHUB_REPOSITORY_SYNC = "github-repository-sync"
KIND_GITHUB_WORKFLOW_SYNC = "github-workflow-sync"
KIND_GITHUB_WORKFLOW_RUN_SYNC = "github-workflow-run-sync"
KIND_GITHUB_VARIABLE_SYNC = "github-variable-sync"
KIND_GITHUB_SECRET_SYNC = "github-secret-metadata-sync"
KIND_GITHUB_WEBHOOK = "github-webhook-process"
KIND_PIPELINE_PROVIDER_SYNC = "pipeline-provider-sync"
KIND_PIPELINE_SYNC = "pipeline-sync"
KIND_PIPELINE_RUN_SYNC = "pipeline-run-sync"
KIND_PIPELINE_RUN_DETAIL_SYNC = "pipeline-run-detail-sync"
KIND_PIPELINE_RETENTION = "pipeline-retention"
KIND_PIPELINE_WEBHOOK = "pipeline-webhook-process"

JOB_NAMES = {
    KIND_DISCOVERY: "AWS multi-account cluster discovery",
    KIND_HEALTH: "AWS multi-account cluster health scan",
    KIND_CERTIFICATES: "AWS multi-account ACM certificate scan",
    KIND_ALIBABA_VALIDATION: "Alibaba China account validation",
    KIND_ALIBABA_DISCOVERY: "Alibaba China ACK cluster discovery",
    KIND_ALIBABA_HEALTH: "Alibaba China ACK health scan",
    KIND_ALIBABA_CERTIFICATES: "Alibaba China certificate discovery",
    KIND_ALIBABA_CERT_EXPIRY: "Alibaba China certificate expiry scan",
    KIND_CREDENTIAL_VALIDATE: "Credential identity validation",
    KIND_CREDENTIAL_ROTATION_SCAN: "Credential rotation status scan",
    KIND_CERTIFICATE_DISCOVERY: "Certificate discovery",
    KIND_CERTIFICATE_EXPIRY: "Certificate expiry scan",
    KIND_CERTIFICATE_ENDPOINT: "Certificate HTTPS endpoint validation",
    KIND_CERTIFICATE_ALERTS: "Certificate alert evaluation",
    KIND_CERTIFICATE_VALIDATE: "Certificate endpoint validation",
    KIND_GITHUB_REPOSITORY_SYNC: "GitHub repository sync",
    KIND_GITHUB_WORKFLOW_SYNC: "GitHub workflow sync",
    KIND_GITHUB_WORKFLOW_RUN_SYNC: "GitHub workflow run sync",
    KIND_GITHUB_VARIABLE_SYNC: "GitHub variable sync",
    KIND_GITHUB_SECRET_SYNC: "GitHub secret metadata sync",
    KIND_GITHUB_WEBHOOK: "GitHub webhook processing",
    KIND_PIPELINE_PROVIDER_SYNC: "Pipeline provider sync",
    KIND_PIPELINE_SYNC: "Pipeline metadata sync",
    KIND_PIPELINE_RUN_SYNC: "Pipeline run sync",
    KIND_PIPELINE_RUN_DETAIL_SYNC: "Pipeline running status sync",
    KIND_PIPELINE_RETENTION: "Pipeline history retention",
    KIND_PIPELINE_WEBHOOK: "Pipeline webhook processing",
}

JOB_PROVIDERS = {
    KIND_DISCOVERY: "AWS",
    KIND_HEALTH: "AWS",
    KIND_CERTIFICATES: "AWS",
    KIND_ALIBABA_VALIDATION: "Alibaba",
    KIND_ALIBABA_DISCOVERY: "Alibaba",
    KIND_ALIBABA_HEALTH: "Alibaba",
    KIND_ALIBABA_CERTIFICATES: "Alibaba",
    KIND_ALIBABA_CERT_EXPIRY: "Alibaba",
    KIND_CREDENTIAL_VALIDATE: "AWS",
    KIND_CREDENTIAL_ROTATION_SCAN: "AWS",
    KIND_CERTIFICATE_DISCOVERY: "AWS",
    KIND_CERTIFICATE_EXPIRY: "AWS",
    KIND_CERTIFICATE_ENDPOINT: "AWS",
    KIND_CERTIFICATE_ALERTS: "AWS",
    KIND_CERTIFICATE_VALIDATE: "AWS",
    KIND_GITHUB_REPOSITORY_SYNC: "AWS",
    KIND_GITHUB_WORKFLOW_SYNC: "AWS",
    KIND_GITHUB_WORKFLOW_RUN_SYNC: "AWS",
    KIND_GITHUB_VARIABLE_SYNC: "AWS",
    KIND_GITHUB_SECRET_SYNC: "AWS",
    KIND_GITHUB_WEBHOOK: "AWS",
    KIND_PIPELINE_PROVIDER_SYNC: "AWS",
    KIND_PIPELINE_SYNC: "AWS",
    KIND_PIPELINE_RUN_SYNC: "AWS",
    KIND_PIPELINE_RUN_DETAIL_SYNC: "AWS",
    KIND_PIPELINE_RETENTION: "AWS",
    KIND_PIPELINE_WEBHOOK: "AWS",
}

TASK_NAMES = {
    KIND_DISCOVERY: "tasks.aws_cluster_discovery.discover_clusters",
    KIND_HEALTH: "tasks.aws_cluster_health.scan_health",
    KIND_CERTIFICATES: "tasks.aws_certificate_scan.scan_certificates",
    KIND_ALIBABA_VALIDATION: "tasks.alibaba_account_validation.validate_accounts",
    KIND_ALIBABA_DISCOVERY: "tasks.alibaba_cluster_discovery.discover_clusters",
    KIND_ALIBABA_HEALTH: "tasks.alibaba_cluster_health.scan_health",
    KIND_ALIBABA_CERTIFICATES: "tasks.alibaba_certificate_scan.scan_certificates",
    KIND_ALIBABA_CERT_EXPIRY: "tasks.alibaba_certificate_expiry.scan_expiry",
    KIND_CREDENTIAL_VALIDATE: "tasks.credential_validate.validate_credential",
    KIND_CREDENTIAL_ROTATION_SCAN: "tasks.credential_rotation_scan.scan_rotation_status",
    KIND_CERTIFICATE_DISCOVERY: "tasks.certificate_discovery.discover_certificates",
    KIND_CERTIFICATE_EXPIRY: "tasks.certificate_expiry.scan_expiry",
    KIND_CERTIFICATE_ENDPOINT: "tasks.certificate_endpoint.validate_endpoints",
    KIND_CERTIFICATE_ALERTS: "tasks.certificate_alerts.evaluate_alerts",
    KIND_CERTIFICATE_VALIDATE: "tasks.certificate_validate.validate_certificate",
    KIND_GITHUB_REPOSITORY_SYNC: "tasks.github_repository_sync.sync_repositories",
    KIND_GITHUB_WORKFLOW_SYNC: "tasks.github_workflow_sync.sync_workflows",
    KIND_GITHUB_WORKFLOW_RUN_SYNC: "tasks.github_workflow_run_sync.sync_runs",
    KIND_GITHUB_VARIABLE_SYNC: "tasks.github_variable_sync.sync_variables",
    KIND_GITHUB_SECRET_SYNC: "tasks.github_secret_sync.sync_secrets",
    KIND_GITHUB_WEBHOOK: "tasks.github_webhook.process_delivery",
    KIND_PIPELINE_PROVIDER_SYNC: "tasks.pipeline_provider_sync.sync_providers",
    KIND_PIPELINE_SYNC: "tasks.pipeline_sync.sync_pipelines",
    KIND_PIPELINE_RUN_SYNC: "tasks.pipeline_run_sync.sync_runs",
    KIND_PIPELINE_RUN_DETAIL_SYNC: "tasks.pipeline_run_detail_sync.sync_details",
    KIND_PIPELINE_RETENTION: "tasks.pipeline_retention.prune_history",
    KIND_PIPELINE_WEBHOOK: "tasks.pipeline_webhook.process_delivery",
}
