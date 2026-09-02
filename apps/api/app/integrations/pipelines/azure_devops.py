from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any, Callable

from app.core.logging import get_logger
from app.integrations.github.mapper import parse_datetime
from app.integrations.pipelines.base import (
    PipelineProvider,
    ProviderPipeline,
    ProviderPipelineJob,
    ProviderPipelineRun,
    ProviderPipelineStage,
)
from app.integrations.pipelines.exceptions import PipelineAuthError, PipelineProviderError

logger = get_logger(__name__)

HttpFn = Callable[[str, str, dict[str, str], bytes | None], tuple[int, dict[str, str], bytes]]


def _default_http(method: str, url: str, headers: dict[str, str], body: bytes | None) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, {key.lower(): value for key, value in response.headers.items()}, response.read()
    except urllib.error.HTTPError as error:
        payload = error.read() if error.fp else b""
        return error.code, {key.lower(): value for key, value in error.headers.items()}, payload


class AzureDevOpsPipelineProvider(PipelineProvider):
    key = "azure-devops"
    display_name = "Azure DevOps"

    def __init__(
        self,
        *,
        organization: str,
        project: str,
        base_url: str,
        token: str,
        http: HttpFn | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self.organization = organization
        self.project = project
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._http = http or _default_http
        self._sleep = sleep or time.sleep
        self.api_version = "7.1"

    def list_pipelines(self) -> list[ProviderPipeline]:
        payload = self._get(f"/{self.organization}/{self.project}/_apis/pipelines", {"api-version": self.api_version})
        return [self._pipeline(item) for item in payload.get("value") or []]

    def get_pipeline(self, external_id: str) -> ProviderPipeline | None:
        payload = self._get(
            f"/{self.organization}/{self.project}/_apis/pipelines/{external_id}",
            {"api-version": self.api_version},
        )
        return self._pipeline(payload) if payload else None

    def list_runs(
        self,
        pipeline: ProviderPipeline,
        *,
        since: datetime | None = None,
        running_only: bool = False,
    ) -> list[ProviderPipelineRun]:
        payload = self._get(
            f"/{self.organization}/{self.project}/_apis/pipelines/{pipeline.external_id}/runs",
            {"api-version": self.api_version},
        )
        runs = [self._run(item, pipeline.external_id) for item in payload.get("value") or []]
        if since is not None:
            runs = [
                item
                for item in runs
                if (item.started_at or item.completed_at) and (item.started_at or item.completed_at) >= since
            ]
        if running_only:
            runs = [item for item in runs if (item.status or "").lower() in {"inprogress", "in_progress", "running", "notstarted", "queued"}]
        return runs

    def get_run(self, pipeline: ProviderPipeline, external_run_id: str) -> ProviderPipelineRun | None:
        payload = self._get(
            f"/{self.organization}/{self.project}/_apis/pipelines/{pipeline.external_id}/runs/{external_run_id}",
            {"api-version": self.api_version},
        )
        return self._run(payload, pipeline.external_id) if payload else None

    def list_stages(self, run: ProviderPipelineRun) -> list[ProviderPipelineStage]:
        records = self._timeline(run)
        stages = [item for item in records if item.get("type") == "Stage"]
        if not stages:
            return [
                ProviderPipelineStage(
                    external_id="jobs",
                    run_external_id=run.external_id,
                    name="Jobs",
                    status=run.status,
                    result=run.result,
                    html_url=run.html_url,
                    started_at=run.started_at,
                    completed_at=run.completed_at,
                    sort_order=0,
                )
            ]
        return [
            ProviderPipelineStage(
                external_id=str(item.get("id") or item.get("identifier") or item.get("name")),
                run_external_id=run.external_id,
                name=str(item.get("name") or "stage"),
                status=str(item.get("state") or item.get("result") or ""),
                result=str(item.get("result") or ""),
                html_url=run.html_url,
                started_at=parse_datetime(item.get("startTime") or item.get("start_time")),
                completed_at=parse_datetime(item.get("finishTime") or item.get("finish_time")),
                sort_order=int(item.get("order") or 0),
            )
            for item in stages
        ]

    def list_jobs(self, run: ProviderPipelineRun) -> list[ProviderPipelineJob]:
        records = self._timeline(run)
        jobs = [item for item in records if item.get("type") in {"Job", "Phase"}]
        return [
            ProviderPipelineJob(
                external_id=str(item.get("id") or item.get("identifier") or item.get("name")),
                run_external_id=run.external_id,
                name=str(item.get("name") or "job"),
                status=str(item.get("state") or ""),
                result=str(item.get("result") or ""),
                html_url=run.html_url,
                stage_external_id=str(item.get("parentId") or item.get("parent_id") or ""),
                started_at=parse_datetime(item.get("startTime") or item.get("start_time")),
                completed_at=parse_datetime(item.get("finishTime") or item.get("finish_time")),
            )
            for item in jobs
        ]

    def _timeline(self, run: ProviderPipelineRun) -> list[dict]:
        try:
            payload = self._get(
                f"/{self.organization}/{self.project}/_apis/build/builds/{run.external_id}/timeline",
                {"api-version": self.api_version},
            )
        except PipelineProviderError:
            logger.info("Azure DevOps timeline unavailable run=%s", run.external_id)
            return []
        return list(payload.get("records") or [])

    def _pipeline(self, item: dict) -> ProviderPipeline:
        folder = str(item.get("folder") or "")
        html = str((item.get("_links") or {}).get("web", {}).get("href") or "")
        if not html:
            html = f"{self.base_url}/{self.organization}/{self.project}/_build?definitionId={item.get('id')}"
        return ProviderPipeline(
            external_id=str(item.get("id")),
            name=str(item.get("name") or "pipeline"),
            default_branch=str((item.get("configuration") or {}).get("path") or ""),
            enabled=True,
            html_url=html,
            metadata={"folder": folder, "revision": item.get("revision")},
        )

    def _run(self, item: dict, pipeline_external_id: str) -> ProviderPipelineRun:
        resources = item.get("resources") or {}
        repositories = resources.get("repositories") or {}
        self_repo = repositories.get("self") or {}
        html = str((item.get("_links") or {}).get("web", {}).get("href") or "")
        if not html:
            html = f"{self.base_url}/{self.organization}/{self.project}/_build/results?buildId={item.get('id')}"
        return ProviderPipelineRun(
            external_id=str(item.get("id")),
            pipeline_external_id=str(item.get("pipeline", {}).get("id") or pipeline_external_id),
            branch=str(self_repo.get("refName") or item.get("sourceBranch") or "").removeprefix("refs/heads/"),
            commit_sha=str(self_repo.get("version") or item.get("sourceVersion") or ""),
            version=str(item.get("name") or item.get("buildNumber") or ""),
            trigger=str((item.get("templateParameters") or {}).get("reason") or item.get("reason") or ""),
            actor=str((item.get("requestedBy") or item.get("requestedFor") or {}).get("displayName") or ""),
            status=str(item.get("state") or item.get("status") or ""),
            result=str(item.get("result") or ""),
            html_url=html,
            started_at=parse_datetime(item.get("createdDate") or item.get("startTime")),
            completed_at=parse_datetime(item.get("finishedDate") or item.get("finishTime")),
            environment_name=str((item.get("templateParameters") or {}).get("environment") or ""),
        )

    def _get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        url = f"{url}?{urllib.parse.urlencode(params)}"
        token = base64.b64encode(f":{self.token}".encode()).decode()
        headers = {
            "Authorization": f"Basic {token}",
            "Accept": "application/json",
            "User-Agent": "cloudops-platform",
        }
        status, response_headers, body = self._http("GET", url, headers, None)
        remaining = response_headers.get("retry-after")
        if status in {429, 503}:
            wait = min(float(remaining or 5), 30)
            self._sleep(wait)
            status, response_headers, body = self._http("GET", url, headers, None)
        if status in {401, 403}:
            raise PipelineAuthError("Azure DevOps authentication failed")
        if status >= 400:
            raise PipelineProviderError(f"Azure DevOps API {status}")
        if not body:
            return {}
        return json.loads(body.decode("utf-8"))


class MockAzureDevOpsProvider(PipelineProvider):
    """In-memory Azure DevOps adapter for tests when no PAT is configured."""

    key = "azure-devops"
    display_name = "Azure DevOps"

    def __init__(self, pipelines: list[ProviderPipeline] | None = None, runs: list[ProviderPipelineRun] | None = None) -> None:
        self._pipelines = pipelines or []
        self._runs = runs or []
        self._stages: dict[str, list[ProviderPipelineStage]] = {}
        self._jobs: dict[str, list[ProviderPipelineJob]] = {}
        self.fail_list = False

    def list_pipelines(self) -> list[ProviderPipeline]:
        if self.fail_list:
            raise PipelineProviderError("azure-devops-unavailable")
        return list(self._pipelines)

    def get_pipeline(self, external_id: str) -> ProviderPipeline | None:
        return next((item for item in self._pipelines if item.external_id == external_id), None)

    def list_runs(
        self,
        pipeline: ProviderPipeline,
        *,
        since: datetime | None = None,
        running_only: bool = False,
    ) -> list[ProviderPipelineRun]:
        runs = [item for item in self._runs if item.pipeline_external_id == pipeline.external_id]
        if since is not None:
            runs = [item for item in runs if (item.started_at or datetime.min) >= since]
        if running_only:
            runs = [item for item in runs if (item.status or "").lower() in {"inprogress", "running", "queued"}]
        return runs

    def get_run(self, pipeline: ProviderPipeline, external_run_id: str) -> ProviderPipelineRun | None:
        return next((item for item in self._runs if item.external_id == external_run_id), None)

    def list_stages(self, run: ProviderPipelineRun) -> list[ProviderPipelineStage]:
        return list(self._stages.get(run.external_id, []))

    def list_jobs(self, run: ProviderPipelineRun) -> list[ProviderPipelineJob]:
        return list(self._jobs.get(run.external_id, []))
