from __future__ import annotations


class PipelineProviderError(Exception):
    pass


class PipelineNotConfigured(PipelineProviderError):
    pass


class PipelineWebhookError(PipelineProviderError):
    pass


class PipelineAuthError(PipelineProviderError):
    pass
