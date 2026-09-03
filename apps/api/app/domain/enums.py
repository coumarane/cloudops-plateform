from typing import Literal

Provider = Literal["AWS", "Alibaba", "Azure", "GCP"]
Region = Literal["AMER", "EMEA", "APAC", "China"]
Environment = Literal["DEV", "INT/TST", "UAT", "NPD", "PRD"]
Platform = Literal["EKS", "ACK", "AKS", "GKE"]
AccountClass = Literal["Production", "Non-production"]
ClusterStatus = Literal["Healthy", "Degraded", "Unreachable"]
HealthStatus = Literal["Passing", "Warning", "Failing"]
RunResult = Literal["Succeeded", "Failed", "Running"]
AlertSeverity = Literal["critical", "warning", "info"]
SecretRotationStatus = Literal["OK", "Overdue", "Due soon"]
RenewalStatus = Literal["OK", "Expiring", "Renewing", "Expired"]
FailureKind = Literal["deployment", "github", "pipeline"]
SecretAction = Literal["Update", "Rotate", "Validate", "Replace"]
CredentialStatus = Literal["HEALTHY", "ROTATION_DUE", "OVERDUE", "INVALID", "DISABLED"]
CredentialType = Literal["iam_role", "sts_assume_role", "access_key", "application", "ram_role", "sts", "service_principal", "service_account"]

PROVIDERS: tuple[Provider, ...] = ("AWS", "Alibaba", "Azure", "GCP")
REGIONS: tuple[Region, ...] = ("AMER", "EMEA", "APAC", "China")
ENVIRONMENTS: tuple[Environment, ...] = ("DEV", "INT/TST", "UAT", "NPD", "PRD")
NON_PRODUCTION: tuple[Environment, ...] = ("DEV", "INT/TST", "UAT")
PRODUCTION: tuple[Environment, ...] = ("NPD", "PRD")
AWS_REGIONS: tuple[Region, ...] = ("AMER", "EMEA", "APAC")
ALIBABA_REGIONS: tuple[Region, ...] = ("China",)
AZURE_REGIONS: tuple[Region, ...] = ("AMER", "EMEA", "APAC")
GCP_REGIONS: tuple[Region, ...] = ("AMER", "EMEA", "APAC")

CLOUD_REGIONS: dict[str, str] = {
    "AWS-AMER": "us-east-1",
    "AWS-EMEA": "eu-west-1",
    "AWS-APAC": "ap-southeast-1",
    "Alibaba-China": "cn-hangzhou",
    "Azure-AMER": "eastus",
    "Azure-EMEA": "westeurope",
    "Azure-APAC": "southeastasia",
    "GCP-AMER": "us-central1",
    "GCP-EMEA": "europe-west1",
    "GCP-APAC": "asia-southeast1",
}


def is_production(environment: Environment) -> bool:
    return environment in PRODUCTION


def regions_for(provider: Provider) -> tuple[Region, ...]:
    if provider == "AWS":
        return AWS_REGIONS
    if provider == "Alibaba":
        return ALIBABA_REGIONS
    if provider == "Azure":
        return AZURE_REGIONS
    return GCP_REGIONS


def platform_for(provider: Provider) -> Platform:
    if provider == "Alibaba":
        return "ACK"
    if provider == "Azure":
        return "AKS"
    if provider == "GCP":
        return "GKE"
    return "EKS"


def cloud_region(provider: Provider, region: Region) -> str:
    return CLOUD_REGIONS[f"{provider}-{region}"]


def account_name(provider: Provider, region: Region, environment: Environment) -> str:
    klass = "prod" if is_production(environment) else "nonprod"
    if provider == "Alibaba":
        return f"alibaba-china-{klass}"
    if provider == "Azure":
        return f"azure-{region.lower()}-{klass}"
    if provider == "GCP":
        return f"gcp-{region.lower()}-{klass}"
    return f"aws-{region.lower()}-{klass}"


def cluster_name(provider: Provider, region: Region, environment: Environment) -> str:
    cloud = cloud_region(provider, region)
    env = "int" if environment == "INT/TST" else environment.lower()
    suffix = {"Alibaba": "ack", "Azure": "aks", "GCP": "gke"}.get(provider, "k8s")
    return f"{cloud}-{env}-{suffix}"


def environment_namespace(environment: Environment) -> str:
    return "int-tst" if environment == "INT/TST" else environment.lower()
