KIND_DISCOVERY = "aws-cluster-discovery"
KIND_HEALTH = "aws-health-scan"
KIND_CERTIFICATES = "aws-certificate-scan"

JOB_NAMES = {
    KIND_DISCOVERY: "AWS multi-account cluster discovery",
    KIND_HEALTH: "AWS multi-account cluster health scan",
    KIND_CERTIFICATES: "AWS multi-account ACM certificate scan",
}

TASK_NAMES = {
    KIND_DISCOVERY: "tasks.aws_cluster_discovery.discover_clusters",
    KIND_HEALTH: "tasks.aws_cluster_health.scan_health",
    KIND_CERTIFICATES: "tasks.aws_certificate_scan.scan_certificates",
}
