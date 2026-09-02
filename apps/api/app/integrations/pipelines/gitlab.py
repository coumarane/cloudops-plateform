from __future__ import annotations

from datetime import datetime

from app.integrations.pipelines.base import (
    PipelineProvider,
    ProviderPipeline,
    ProviderPipelineJob,
    ProviderPipelineRun,
    ProviderPipelineStage,
)


class GitLabPipelineProvider(PipelineProvider):
    """Stub adapter reserved for a later GitLab integration."""

    key = "gitlab"
    display_name = "GitLab"

    def list_pipelines(self) -> list[ProviderPipeline]:
        return []

    def get_pipeline(self, external_id: str) -> ProviderPipeline | None:
        return None

    def list_runs(
        self,
        pipeline: ProviderPipeline,
        *,
        since: datetime | None = None,
        running_only: bool = False,
    ) -> list[ProviderPipelineRun]:
        return []

    def get_run(self, pipeline: ProviderPipeline, external_run_id: str) -> ProviderPipelineRun | None:
        return None

    def list_stages(self, run: ProviderPipelineRun) -> list[ProviderPipelineStage]:
        return []

    def list_jobs(self, run: ProviderPipelineRun) -> list[ProviderPipelineJob]:
        return []
