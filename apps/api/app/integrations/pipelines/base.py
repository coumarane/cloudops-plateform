from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ProviderPipeline:
    external_id: str
    name: str
    repository_external_id: str = ""
    default_branch: str = ""
    enabled: bool = True
    html_url: str = ""
    application_external_id: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class ProviderPipelineRun:
    external_id: str
    pipeline_external_id: str
    branch: str = ""
    commit_sha: str = ""
    version: str = ""
    trigger: str = ""
    actor: str = ""
    status: str = ""
    result: str = ""
    html_url: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    environment_name: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class ProviderPipelineStage:
    external_id: str
    run_external_id: str
    name: str
    status: str = ""
    result: str = ""
    html_url: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    sort_order: int = 0


@dataclass
class ProviderPipelineJob:
    external_id: str
    run_external_id: str
    name: str
    status: str = ""
    result: str = ""
    html_url: str = ""
    stage_external_id: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None


class PipelineProvider(ABC):
    """Provider-neutral DevOps pipeline integration."""

    key: str
    display_name: str

    @abstractmethod
    def list_pipelines(self) -> list[ProviderPipeline]: ...

    @abstractmethod
    def get_pipeline(self, external_id: str) -> ProviderPipeline | None: ...

    @abstractmethod
    def list_runs(
        self,
        pipeline: ProviderPipeline,
        *,
        since: datetime | None = None,
        running_only: bool = False,
    ) -> list[ProviderPipelineRun]: ...

    @abstractmethod
    def get_run(self, pipeline: ProviderPipeline, external_run_id: str) -> ProviderPipelineRun | None: ...

    @abstractmethod
    def list_stages(self, run: ProviderPipelineRun) -> list[ProviderPipelineStage]: ...

    @abstractmethod
    def list_jobs(self, run: ProviderPipelineRun) -> list[ProviderPipelineJob]: ...
