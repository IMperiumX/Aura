"""
Repository interface for Disorder entity.
Defines the contract for data persistence operations.
"""

from abc import ABC
from abc import abstractmethod

from aura.mentalhealth.domain.entities.disorder import Disorder
from aura.mentalhealth.domain.entities.disorder import DisorderType


class DisorderRepository(ABC):
    """Abstract repository interface for disorders."""

    @abstractmethod
    def save(self, disorder: Disorder) -> Disorder:
        """Save a disorder."""

    @abstractmethod
    def find_by_id(self, disorder_id: int) -> Disorder | None:
        """Find a disorder by ID."""

    @abstractmethod
    def find_by_name(self, name: str) -> Disorder | None:
        """Find a disorder by name."""

    @abstractmethod
    def find_by_type(self, disorder_type: DisorderType) -> list[Disorder]:
        """Find disorders by type."""

    @abstractmethod
    def find_all(self) -> list[Disorder]:
        """Find all disorders."""

    @abstractmethod
    def search_by_symptoms(self, symptoms: list[str]) -> list[Disorder]:
        """Search disorders by symptoms."""

    @abstractmethod
    def search_by_name_or_description(self, query: str) -> list[Disorder]:
        """Search disorders by name or description."""

    @abstractmethod
    def update(self, disorder: Disorder) -> Disorder:
        """Update a disorder."""

    @abstractmethod
    def delete(self, disorder_id: int) -> bool:
        """Delete a disorder."""

    @abstractmethod
    def exists_by_name(self, name: str, exclude_id: int | None = None) -> bool:
        """Check if a disorder with the given name exists."""

    @abstractmethod
    def count_by_type(self, disorder_type: DisorderType) -> int:
        """Count disorders by type."""
