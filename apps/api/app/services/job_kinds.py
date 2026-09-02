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
}
