from __future__ import annotations

from .models import LogEntry, ServiceContext


def log_stage(context: ServiceContext, stage: str, message: str, **details: str) -> None:
    context.logs.append(LogEntry(stage=stage, message=message, details=details))
