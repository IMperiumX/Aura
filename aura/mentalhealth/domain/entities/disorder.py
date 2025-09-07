"""
Domain entity for Disorder.
Contains business logic and rules for mental health disorders.
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import Enum

from django.utils import timezone

MAX_CHAR_LENGTH = 255


class DisorderType(Enum):
    MENTAL = "mental"
    PHYSICAL = "physical"
    GENETIC = "genetic"
    EMOTIONAL = "emotional"
    BEHAVIORAL = "behavioral"
    FUNCTIONAL = "functional"


@dataclass
class Disorder:
    """Domain entity representing a mental health disorder."""

    id: int | None = None
    name: str = ""
    type: DisorderType = DisorderType.MENTAL
    description: str = ""
    signs_and_symptoms: str = ""
    treatment: str = ""
    prevention: str = ""
    symptoms: list[str] = field(default_factory=list)
    causes: list[str] = field(default_factory=list)
    created_at: datetime | None = field(default_factory=datetime.now)
    updated_at: datetime | None = field(default_factory=datetime.now)

    def add_symptom(self, symptom: str) -> None:
        """Add a symptom to the disorder."""
        if not symptom or symptom in self.symptoms:
            return

        self.symptoms.append(symptom)
        self.updated_at = timezone.now()

    def remove_symptom(self, symptom: str) -> None:
        """Remove a symptom from the disorder."""
        if symptom in self.symptoms:
            self.symptoms.remove(symptom)
            self.updated_at = timezone.now()

    def add_cause(self, cause: str) -> None:
        """Add a cause to the disorder."""
        if not cause or cause in self.causes:
            return

        self.causes.append(cause)
        self.updated_at = timezone.now()

    def remove_cause(self, cause: str) -> None:
        """Remove a cause from the disorder."""
        if cause in self.causes:
            self.causes.remove(cause)
            self.updated_at = timezone.now()

    def update_description(self, description: str) -> None:
        """Update the disorder description."""
        self.description = description
        self.updated_at = timezone.now()

    def update_treatment(self, treatment: str) -> None:
        """Update the disorder treatment information."""
        self.treatment = treatment
        self.updated_at = timezone.now()

    def update_prevention(self, prevention: str) -> None:
        """Update the disorder prevention information."""
        self.prevention = prevention
        self.updated_at = timezone.now()

    def get_symptom_count(self) -> int:
        """Get the number of symptoms."""
        return len(self.symptoms)

    def get_cause_count(self) -> int:
        """Get the number of causes."""
        return len(self.causes)

    def has_symptom(self, symptom: str) -> bool:
        """Check if the disorder has a specific symptom."""
        return symptom in self.symptoms

    def has_cause(self, cause: str) -> bool:
        """Check if the disorder has a specific cause."""
        return cause in self.causes

    def validate(self) -> None:
        """Validate the disorder entity."""
        errors = []

        if not self.name or not self.name.strip():
            errors.append("Name is required")

        if not self.description or not self.description.strip():
            errors.append("Description is required")

        if not self.signs_and_symptoms or not self.signs_and_symptoms.strip():
            errors.append("Signs and symptoms are required")

        if len(self.name) > MAX_CHAR_LENGTH:
            errors.append(f"Name must be {MAX_CHAR_LENGTH} characters or less")

        if errors:
            msg = f"Validation failed: {', '.join(errors)}"
            raise ValueError(msg)
