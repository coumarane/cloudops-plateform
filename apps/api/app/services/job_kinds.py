KIND_DISCOVERY = "aws-cluster-discovery"
KIND_HEALTH = "aws-health-scan"
KIND_CERTIFICATES = "aws-certificate-scan"

JOB_NAMES = {
    KIND_DISCOVERY: "AWS EMEA DEV cluster discovery",
    KIND_HEALTH: "AWS EMEA DEV cluster health scan",
    KIND_CERTIFICATES: "AWS EMEA DEV ACM certificate scan",
}

TASK_NAMES = {
    KIND_DISCOVERY: "tasks.aws_cluster_discovery.discover_clusters",
    KIND_HEALTH: "tasks.aws_cluster_health.scan_health",
    KIND_CERTIFICATES: "tasks.aws_certificate_scan.scan_certificates",
}
