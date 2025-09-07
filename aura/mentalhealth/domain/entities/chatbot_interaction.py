"""
Domain entity for Chatbot Interaction.
Contains business logic and rules for chatbot interactions.
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Any

from django.utils import timezone

MAX_CHAR_LENGTH = 2000
MIN_CONVERSATION_LENGHT = 2


@dataclass
class ChatbotInteraction:
    """Domain entity representing a chatbot interaction."""

    id: int | None = None
    message: str = ""
    response: str = ""
    conversation_log: list[dict[str, Any]] = field(default_factory=list)
    interaction_date: datetime | None = field(default_factory=timezone.now)
    user_id: int | None = None
    session_id: str | None = None
    created_at: datetime | None = field(default_factory=timezone.now)
    updated_at: datetime | None = field(default_factory=timezone.now)

    def add_to_conversation_log(self, entry: dict[str, Any]) -> None:
        """Add an entry to the conversation log."""
        if not isinstance(entry, dict):
            msg = "Entry must be a dictionary"
            raise TypeError(msg)

        # Add timestamp if not present
        if "timestamp" not in entry:
            entry["timestamp"] = timezone.now().isoformat()

        self.conversation_log.append(entry)
        self.updated_at = timezone.now()

    def add_user_message(self, message: str, metadata: dict | None = None) -> None:
        """Add a user message to the conversation log."""
        entry = {
            "type": "user_message",
            "content": message,
            "timestamp": timezone.now().isoformat(),
        }

        if metadata:
            entry["metadata"] = metadata

        self.add_to_conversation_log(entry)

    def add_bot_response(
        self,
        response: str,
        confidence: float | None = None,
        intent: str | None = None,
    ) -> None:
        """Add a bot response to the conversation log."""
        entry = {
            "type": "bot_response",
            "content": response,
            "timestamp": timezone.now().isoformat(),
        }

        if confidence is not None:
            entry["confidence"] = confidence

        if intent:
            entry["intent"] = intent

        self.add_to_conversation_log(entry)

    def get_conversation_length(self) -> int:
        """Get the number of entries in the conversation log."""
        return len(self.conversation_log)

    def get_user_messages(self) -> list[dict[str, Any]]:
        """Get all user messages from the conversation log."""
        return [entry for entry in self.conversation_log if entry.get("type") == "user_message"]

    def get_bot_responses(self) -> list[dict[str, Any]]:
        """Get all bot responses from the conversation log."""
        return [entry for entry in self.conversation_log if entry.get("type") == "bot_response"]

    def get_last_user_message(self) -> str | None:
        """Get the last user message."""
        user_messages = self.get_user_messages()
        return user_messages[-1].get("content") if user_messages else None

    def get_last_bot_response(self) -> str | None:
        """Get the last bot response."""
        bot_responses = self.get_bot_responses()
        return bot_responses[-1].get("content") if bot_responses else None

    def clear_conversation_log(self) -> None:
        """Clear the conversation log."""
        self.conversation_log = []
        self.updated_at = timezone.now()

    def get_conversation_summary(self) -> dict[str, Any]:
        """Get a summary of the conversation."""
        user_messages = self.get_user_messages()
        bot_responses = self.get_bot_responses()

        return {
            "total_entries": len(self.conversation_log),
            "user_messages_count": len(user_messages),
            "bot_responses_count": len(bot_responses),
            "session_id": self.session_id,
            "duration_minutes": self._calculate_duration_minutes(),
            "first_message_time": self.conversation_log[0].get("timestamp") if self.conversation_log else None,
            "last_message_time": self.conversation_log[-1].get("timestamp") if self.conversation_log else None,
        }

    def _calculate_duration_minutes(self) -> float | None:
        """Calculate conversation duration in minutes."""
        if len(self.conversation_log) < MIN_CONVERSATION_LENGHT:
            return None

        try:
            first_time = datetime.fromisoformat(
                self.conversation_log[0].get("timestamp", "").replace("Z", "+00:00"),
            )
            last_time = datetime.fromisoformat(
                self.conversation_log[-1].get("timestamp", "").replace("Z", "+00:00"),
            )

            duration = last_time - first_time
            return duration.total_seconds() / 60
        except (ValueError, AttributeError):
            return None

    def validate(self) -> None:
        """Validate the chatbot interaction entity."""
        errors = []

        if not self.message or not self.message.strip():
            errors.append("Message is required")

        if self.user_id is None:
            errors.append("User ID is required")

        if len(self.message) > MAX_CHAR_LENGTH:
            errors.append("Message must be 2000 characters or less")

        if len(self.response) > MAX_CHAR_LENGTH:
            errors.append("Response must be 2000 characters or less")

        if errors:
            msg = f"Validation failed: {', '.join(errors)}"
            raise ValueError(msg)
