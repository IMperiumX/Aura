from aura import analytics


class MessageSentEvent(analytics.Event):
    """Event fired when a message is sent."""

    type = "message.sent"

    attributes = (
        analytics.Attribute("message_id"),
        analytics.Attribute("thread_id"),
        analytics.Attribute("sender_id"),
        analytics.Attribute("sender_type"),  # 'patient', 'therapist', 'admin'
        analytics.Attribute("recipient_count", type=int),
        analytics.Attribute("message_length", type=int),
        analytics.Attribute("has_attachments", type=bool),
        analytics.Attribute("thread_type", required=False),
    )


class ThreadCreatedEvent(analytics.Event):
    """Event fired when a new conversation thread is created."""

    type = "thread.created"

    attributes = (
        analytics.Attribute("thread_id"),
        analytics.Attribute("created_by_id"),
        analytics.Attribute("thread_type"),
        analytics.Attribute("participant_count", type=int),
        analytics.Attribute("therapy_session_id", required=False),
    )


class VideoCallStartedEvent(analytics.Event):
    """Event fired when a video call is initiated."""

    type = "video_call.started"

    attributes = (
        analytics.Attribute("call_id"),
        analytics.Attribute("initiator_id"),
        analytics.Attribute("participant_count", type=int),
        analytics.Attribute("call_type"),  # 'therapy', 'consultation', 'group'
        analytics.Attribute("therapy_session_id", required=False),
    )


class VideoCallEndedEvent(analytics.Event):
    """Event fired when a video call ends."""

    type = "video_call.ended"

    attributes = (
        analytics.Attribute("call_id"),
        analytics.Attribute("duration_minutes", type=int),
        analytics.Attribute("participant_count", type=int),
        analytics.Attribute("ended_by_id"),
        analytics.Attribute("quality_rating", type=int, required=False),
    )


class AttachmentUploadedEvent(analytics.Event):
    """Event fired when a file attachment is uploaded."""

    type = "attachment.uploaded"

    attributes = (
        analytics.Attribute("attachment_id"),
        analytics.Attribute("uploader_id"),
        analytics.Attribute("file_size_bytes", type=int),
        analytics.Attribute("file_type"),
        analytics.Attribute("thread_id", required=False),
        analytics.Attribute("message_id", required=False),
    )


class NotificationSentEvent(analytics.Event):
    """Event fired when a notification is sent to a user."""

    type = "notification.sent"

    attributes = (
        analytics.Attribute("notification_id"),
        analytics.Attribute("recipient_id"),
        analytics.Attribute("notification_type"),
        analytics.Attribute("delivery_method"),  # 'email', 'sms', 'push', 'in_app'
        analytics.Attribute("related_object_type", required=False),
        analytics.Attribute("related_object_id", required=False),
        analytics.Attribute("success", type=bool),
    )


# Register all events
analytics.register(MessageSentEvent)
analytics.register(ThreadCreatedEvent)
analytics.register(VideoCallStartedEvent)
analytics.register(VideoCallEndedEvent)
analytics.register(AttachmentUploadedEvent)
analytics.register(NotificationSentEvent)
