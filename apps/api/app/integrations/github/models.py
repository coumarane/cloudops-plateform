"""Normalized GitHub/SCM dataclasses. Provider-neutral types live in integrations.scm.base."""

from app.integrations.scm.base import (
    ScmJob,
    ScmOrganization,
    ScmPublicKey,
    ScmRepository,
    ScmSecret,
    ScmVariable,
    ScmWorkflow,
    ScmWorkflowRun,
)

__all__ = [
    "ScmJob",
    "ScmOrganization",
    "ScmPublicKey",
    "ScmRepository",
    "ScmSecret",
    "ScmVariable",
    "ScmWorkflow",
    "ScmWorkflowRun",
]
