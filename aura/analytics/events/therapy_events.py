from aura import analytics


class TherapySessionCreatedEvent(analytics.Event):
    """Event fired when a therapy session is scheduled."""
    type = "therapy_session.created"

    attributes = (
        analytics.Attribute("session_id"),
        analytics.Attribute("therapist_id"),
        analytics.Attribute("patient_id"),
        analytics.Attribute("session_type"),
        analytics.Attribute("target_audience"),
        analytics.Attribute("scheduled_at"),
        analytics.Attribute("recurrence_pattern", required=False),
    )


class TherapySessionStartedEvent(analytics.Event):
    """Event fired when a therapy session starts."""
    type = "therapy_session.started"

    attributes = (
        analytics.Attribute("session_id"),
        analytics.Attribute("therapist_id"),
        analytics.Attribute("patient_id"),
        analytics.Attribute("session_type"),
        analytics.Attribute("actual_start_time"),
        analytics.Attribute("scheduled_start_time"),
        analytics.Attribute("delay_minutes", type=int, required=False),
    )


class TherapySessionCompletedEvent(analytics.Event):
    """Event fired when a therapy session is completed."""
    type = "therapy_session.completed"

    attributes = (
        analytics.Attribute("session_id"),
        analytics.Attribute("therapist_id"),
        analytics.Attribute("patient_id"),
        analytics.Attribute("session_type"),
        analytics.Attribute("duration_minutes", type=int),
        analytics.Attribute("has_notes", type=bool),
        analytics.Attribute("has_summary", type=bool),
    )


class TherapySessionCancelledEvent(analytics.Event):
    """Event fired when a therapy session is cancelled."""
    type = "therapy_session.cancelled"

    attributes = (
        analytics.Attribute("session_id"),
        analytics.Attribute("therapist_id"),
        analytics.Attribute("patient_id"),
        analytics.Attribute("cancelled_by"),  # 'therapist' or 'patient'
        analytics.Attribute("notice_hours", type=int, required=False),
        analytics.Attribute("reason", required=False),
    )


class ChatbotInteractionEvent(analytics.Event):
    """Event fired when patient interacts with chatbot."""
    type = "chatbot.interaction"

    attributes = (
        analytics.Attribute("interaction_id"),
        analytics.Attribute("patient_id"),
        analytics.Attribute("message_count", type=int),
        analytics.Attribute("session_duration_seconds", type=int, required=False),
        analytics.Attribute("satisfaction_score", type=int, required=False),
    )


# Register all events
analytics.register(TherapySessionCreatedEvent)
analytics.register(TherapySessionStartedEvent)
analytics.register(TherapySessionCompletedEvent)
analytics.register(TherapySessionCancelledEvent)
analytics.register(ChatbotInteractionEvent)
