KIND_DISCOVERY = "aws-cluster-discovery"
KIND_HEALTH = "aws-health-scan"
KIND_CERTIFICATES = "aws-certificate-scan"
KIND_ALIBABA_VALIDATION = "alibaba-account-validation"
KIND_ALIBABA_DISCOVERY = "alibaba-cluster-discovery"
KIND_ALIBABA_HEALTH = "alibaba-health-scan"
KIND_ALIBABA_CERTIFICATES = "alibaba-certificate-discovery"
KIND_ALIBABA_CERT_EXPIRY = "alibaba-certificate-expiry-scan"

JOB_NAMES = {
    KIND_DISCOVERY: "AWS multi-account cluster discovery",
    KIND_HEALTH: "AWS multi-account cluster health scan",
    KIND_CERTIFICATES: "AWS multi-account ACM certificate scan",
    KIND_ALIBABA_VALIDATION: "Alibaba China account validation",
    KIND_ALIBABA_DISCOVERY: "Alibaba China ACK cluster discovery",
    KIND_ALIBABA_HEALTH: "Alibaba China ACK health scan",
    KIND_ALIBABA_CERTIFICATES: "Alibaba China certificate discovery",
    KIND_ALIBABA_CERT_EXPIRY: "Alibaba China certificate expiry scan",
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
}
