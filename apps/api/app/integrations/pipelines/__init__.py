from __future__ import annotations

from app.core.config import settings
from app.core.logging import get_logger
from app.integrations.pipelines.azure_devops import AzureDevOpsPipelineProvider, MockAzureDevOpsProvider
from app.integrations.pipelines.base import PipelineProvider
from app.integrations.pipelines.github import GitHubActionsPipelineProvider
from app.integrations.pipelines.gitlab import GitLabPipelineProvider
from app.integrations.pipelines.jenkins import JenkinsPipelineProvider
from app.secrets.factory import secret_backend

logger = get_logger(__name__)

_OVERRIDE: list[PipelineProvider] | None = None


def override_pipeline_providers(providers: list[PipelineProvider] | None) -> None:
    global _OVERRIDE
    _OVERRIDE = providers


def azure_devops_configured() -> bool:
    return bool(settings.azure_devops_organization and settings.azure_devops_project and settings.azure_devops_auth_ref)


def get_pipeline_providers(session=None) -> list[PipelineProvider]:
    if _OVERRIDE is not None:
        return list(_OVERRIDE)
    providers: list[PipelineProvider] = []
    if session is not None:
        providers.append(GitHubActionsPipelineProvider(session))
    if azure_devops_configured():
        try:
            token = secret_backend().get_secret(settings.azure_devops_auth_ref)
            providers.append(
                AzureDevOpsPipelineProvider(
                    organization=settings.azure_devops_organization,
                    project=settings.azure_devops_project,
                    base_url=settings.azure_devops_base_url,
                    token=token,
                )
            )
        except Exception:
            logger.exception("Azure DevOps provider could not be constructed")
    elif settings.azure_devops_mock:
        providers.append(MockAzureDevOpsProvider())
    providers.append(GitLabPipelineProvider())
    providers.append(JenkinsPipelineProvider())
    return providers
