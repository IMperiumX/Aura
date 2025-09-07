"""
Repository interface for ChatbotInteraction entity.
Defines the contract for data persistence operations.
"""

from abc import ABC
from abc import abstractmethod
from datetime import datetime

from aura.mentalhealth.domain.entities.chatbot_interaction import ChatbotInteraction


class ChatbotRepository(ABC):
    """Abstract repository interface for chatbot interactions."""

    @abstractmethod
    def save(self, interaction: ChatbotInteraction) -> ChatbotInteraction:
        """Save a chatbot interaction."""

    @abstractmethod
    def find_by_id(self, interaction_id: int) -> ChatbotInteraction | None:
        """Find a chatbot interaction by ID."""

    @abstractmethod
    def find_by_user_id(self, user_id: int) -> list[ChatbotInteraction]:
        """Find all chatbot interactions for a user."""

    @abstractmethod
    def find_by_session_id(self, session_id: str) -> list[ChatbotInteraction]:
        """Find chatbot interactions by session ID."""

    @abstractmethod
    def find_by_date_range(
        self,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
    ) -> list[ChatbotInteraction]:
        """Find chatbot interactions within a date range for a user."""

    @abstractmethod
    def find_recent_by_user(self, user_id: int, limit: int = 10) -> list[ChatbotInteraction]:
        """Find recent chatbot interactions for a user."""

    @abstractmethod
    def update(self, interaction: ChatbotInteraction) -> ChatbotInteraction:
        """Update a chatbot interaction."""

    @abstractmethod
    def delete(self, interaction_id: int) -> bool:
        """Delete a chatbot interaction."""

    @abstractmethod
    def delete_by_user_id(self, user_id: int) -> int:
        """Delete all chatbot interactions for a user. Returns count of deleted interactions."""

    @abstractmethod
    def count_by_user(self, user_id: int) -> int:
        """Count chatbot interactions for a user."""

    @abstractmethod
    def get_user_interaction_stats(self, user_id: int) -> dict:
        """Get interaction statistics for a user."""
