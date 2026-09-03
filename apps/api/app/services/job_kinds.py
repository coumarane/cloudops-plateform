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
KIND_CLUSTER_HEALTH_SCAN = "cluster-health-scan"
KIND_APPLICATION_HEALTH_SCAN = "application-health-scan"
KIND_HTTP_HEALTH_CHECK = "http-health-check"
KIND_DEPENDENCY_HEALTH_CHECK = "dependency-health-check"
KIND_HEALTH_AGGREGATION = "health-aggregation"
KIND_HEALTH_ALERT_EVALUATION = "health-alert-evaluation"
KIND_HEALTH_RETENTION = "health-retention"
KIND_ALERT_EVALUATE = "alert-evaluate"
KIND_ALERT_NOTIFICATION_DISPATCH = "alert-notification-dispatch"
KIND_ALERT_ESCALATION_CHECK = "alert-escalation-check"
KIND_ALERT_RECOVERY_NOTIFICATION = "alert-recovery-notification"
KIND_ALERT_SUPPRESSION_EXPIRY = "alert-suppression-expiry"
KIND_MAINTENANCE_WINDOW_EXPIRY = "maintenance-window-expiry"

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
    KIND_CLUSTER_HEALTH_SCAN: "Unified cluster health scan",
    KIND_APPLICATION_HEALTH_SCAN: "Application health aggregation",
    KIND_HTTP_HEALTH_CHECK: "HTTP endpoint health check",
    KIND_DEPENDENCY_HEALTH_CHECK: "Application dependency health check",
    KIND_HEALTH_AGGREGATION: "Health aggregation",
    KIND_HEALTH_ALERT_EVALUATION: "Health alert evaluation",
    KIND_HEALTH_RETENTION: "Health history retention",
    KIND_ALERT_EVALUATE: "Central alert evaluation",
    KIND_ALERT_NOTIFICATION_DISPATCH: "Alert notification dispatch",
    KIND_ALERT_ESCALATION_CHECK: "Alert escalation check",
    KIND_ALERT_RECOVERY_NOTIFICATION: "Alert recovery notification",
    KIND_ALERT_SUPPRESSION_EXPIRY: "Alert suppression expiry",
    KIND_MAINTENANCE_WINDOW_EXPIRY: "Maintenance window expiry",
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
    KIND_CLUSTER_HEALTH_SCAN: "AWS",
    KIND_APPLICATION_HEALTH_SCAN: "AWS",
    KIND_HTTP_HEALTH_CHECK: "AWS",
    KIND_DEPENDENCY_HEALTH_CHECK: "AWS",
    KIND_HEALTH_AGGREGATION: "AWS",
    KIND_HEALTH_ALERT_EVALUATION: "AWS",
    KIND_HEALTH_RETENTION: "AWS",
    KIND_ALERT_EVALUATE: "AWS",
    KIND_ALERT_NOTIFICATION_DISPATCH: "AWS",
    KIND_ALERT_ESCALATION_CHECK: "AWS",
    KIND_ALERT_RECOVERY_NOTIFICATION: "AWS",
    KIND_ALERT_SUPPRESSION_EXPIRY: "AWS",
    KIND_MAINTENANCE_WINDOW_EXPIRY: "AWS",
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
    KIND_CLUSTER_HEALTH_SCAN: "tasks.cluster_health_scan.scan_clusters",
    KIND_APPLICATION_HEALTH_SCAN: "tasks.application_health_scan.scan_applications",
    KIND_HTTP_HEALTH_CHECK: "tasks.http_health_check.check_endpoints",
    KIND_DEPENDENCY_HEALTH_CHECK: "tasks.dependency_health_check.check_dependencies",
    KIND_HEALTH_AGGREGATION: "tasks.health_aggregation.aggregate",
    KIND_HEALTH_ALERT_EVALUATION: "tasks.health_alert_evaluation.evaluate",
    KIND_HEALTH_RETENTION: "tasks.health_retention.prune_history",
    KIND_ALERT_EVALUATE: "tasks.alert_evaluate.evaluate",
    KIND_ALERT_NOTIFICATION_DISPATCH: "tasks.alert_notification_dispatch.dispatch",
    KIND_ALERT_ESCALATION_CHECK: "tasks.alert_escalation_check.check",
    KIND_ALERT_RECOVERY_NOTIFICATION: "tasks.alert_recovery_notification.notify",
    KIND_ALERT_SUPPRESSION_EXPIRY: "tasks.alert_suppression_expiry.expire",
    KIND_MAINTENANCE_WINDOW_EXPIRY: "tasks.maintenance_window_expiry.expire",
}
