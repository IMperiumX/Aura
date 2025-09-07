"""
Django implementation of ChatbotRepository.
Adapts Django ORM to domain repository interface.
"""

from datetime import datetime

from aura.mentalhealth.domain.entities.chatbot_interaction import ChatbotInteraction
from aura.mentalhealth.domain.repositories.chatbot_repository import ChatbotRepository
from aura.mentalhealth.models import ChatbotInteraction as DjangoChatbotInteraction


class DjangoChatbotRepository(ChatbotRepository):
    """Django ORM implementation of chatbot interaction repository."""

    def save(self, interaction: ChatbotInteraction) -> ChatbotInteraction:
        """Save a chatbot interaction."""
        if interaction.id:
            # Update existing
            django_interaction = DjangoChatbotInteraction.objects.get(id=interaction.id)
            self._update_django_model(django_interaction, interaction)
        else:
            # Create new
            django_interaction = self._create_django_model(interaction)

        django_interaction.save()
        return self._to_domain_entity(django_interaction)

    def find_by_id(self, interaction_id: int) -> ChatbotInteraction | None:
        """Find a chatbot interaction by ID."""
        try:
            django_interaction = DjangoChatbotInteraction.objects.get(id=interaction_id)
            return self._to_domain_entity(django_interaction)
        except DjangoChatbotInteraction.DoesNotExist:
            return None

    def find_by_user_id(self, user_id: int) -> list[ChatbotInteraction]:
        """Find all chatbot interactions for a user."""
        django_interactions = DjangoChatbotInteraction.objects.filter(
            user_id=user_id,
        ).order_by("-interaction_date")

        return [self._to_domain_entity(interaction) for interaction in django_interactions]

    def find_by_session_id(self, session_id: str) -> list[ChatbotInteraction]:
        """Find chatbot interactions by session ID."""
        django_interactions = DjangoChatbotInteraction.objects.filter(
            conversation_log__contains=[{"session_id": session_id}],
        ).order_by("interaction_date")

        return [self._to_domain_entity(interaction) for interaction in django_interactions]

    def find_by_date_range(
        self,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
    ) -> list[ChatbotInteraction]:
        """Find chatbot interactions within a date range for a user."""
        django_interactions = DjangoChatbotInteraction.objects.filter(
            user_id=user_id,
            interaction_date__gte=start_date,
            interaction_date__lte=end_date,
        ).order_by("interaction_date")

        return [self._to_domain_entity(interaction) for interaction in django_interactions]

    def find_recent_by_user(self, user_id: int, limit: int = 10) -> list[ChatbotInteraction]:
        """Find recent chatbot interactions for a user."""
        django_interactions = DjangoChatbotInteraction.objects.filter(
            user_id=user_id,
        ).order_by("-interaction_date")[:limit]

        return [self._to_domain_entity(interaction) for interaction in django_interactions]

    def update(self, interaction: ChatbotInteraction) -> ChatbotInteraction:
        """Update a chatbot interaction."""
        if not interaction.id:
            raise ValueError("Cannot update an interaction without an ID")

        django_interaction = DjangoChatbotInteraction.objects.get(id=interaction.id)
        self._update_django_model(django_interaction, interaction)
        django_interaction.save()

        return self._to_domain_entity(django_interaction)

    def delete(self, interaction_id: int) -> bool:
        """Delete a chatbot interaction."""
        try:
            DjangoChatbotInteraction.objects.get(id=interaction_id).delete()
            return True
        except DjangoChatbotInteraction.DoesNotExist:
            return False

    def delete_by_user_id(self, user_id: int) -> int:
        """Delete all chatbot interactions for a user. Returns count of deleted interactions."""
        deleted_count, _ = DjangoChatbotInteraction.objects.filter(
            user_id=user_id,
        ).delete()
        return deleted_count

    def count_by_user(self, user_id: int) -> int:
        """Count chatbot interactions for a user."""
        return DjangoChatbotInteraction.objects.filter(user_id=user_id).count()

    def get_user_interaction_stats(self, user_id: int) -> dict:
        """Get interaction statistics for a user."""
        interactions = DjangoChatbotInteraction.objects.filter(user_id=user_id)

        if not interactions.exists():
            return {
                "total_interactions": 0,
                "first_interaction": None,
                "last_interaction": None,
                "average_conversation_length": 0,
                "total_messages": 0,
            }

        total_interactions = interactions.count()
        first_interaction = interactions.order_by("interaction_date").first()
        last_interaction = interactions.order_by("-interaction_date").first()

        # Calculate total conversation log entries
        total_messages = 0
        for interaction in interactions:
            total_messages += len(interaction.conversation_log or [])

        average_conversation_length = (
            total_messages / total_interactions if total_interactions > 0 else 0
        )

        return {
            "total_interactions": total_interactions,
            "first_interaction": first_interaction.interaction_date if first_interaction else None,
            "last_interaction": last_interaction.interaction_date if last_interaction else None,
            "average_conversation_length": round(average_conversation_length, 2),
            "total_messages": total_messages,
        }

    def _create_django_model(self, entity: ChatbotInteraction) -> DjangoChatbotInteraction:
        """Create Django model from domain entity."""
        return DjangoChatbotInteraction(
            message=entity.message,
            response=entity.response,
            conversation_log=entity.conversation_log or [],
            interaction_date=entity.interaction_date or datetime.now(),
            user_id=entity.user_id,
        )

    def _update_django_model(
        self,
        django_model: DjangoChatbotInteraction,
        entity: ChatbotInteraction,
    ) -> None:
        """Update Django model with domain entity data."""
        django_model.message = entity.message
        django_model.response = entity.response
        django_model.conversation_log = entity.conversation_log or []
        django_model.interaction_date = entity.interaction_date or datetime.now()
        django_model.user_id = entity.user_id

    def _to_domain_entity(self, django_model: DjangoChatbotInteraction) -> ChatbotInteraction:
        """Convert Django model to domain entity."""
        return ChatbotInteraction(
            id=django_model.id,
            message=django_model.message,
            response=django_model.response,
            conversation_log=django_model.conversation_log or [],
            interaction_date=django_model.interaction_date,
            user_id=django_model.user_id,
            created_at=django_model.created,
            updated_at=django_model.modified,
        )
