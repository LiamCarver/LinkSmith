from __future__ import annotations

from typing import Mapping, Protocol

from .models import LoadedArtifact, ProducedArtifact, ServiceContext, ServiceContract


class LinkSmithService(Protocol):
    contract: ServiceContract

    def execute(
        self,
        inputs: Mapping[str, tuple[LoadedArtifact, ...]],
        context: ServiceContext,
    ) -> Mapping[str, ProducedArtifact | tuple[ProducedArtifact, ...]]:
        ...
