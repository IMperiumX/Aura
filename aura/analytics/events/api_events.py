from aura import analytics


class APIRequestStartedEvent(analytics.Event):
    """Event fired when an API request is initiated."""

    type = "api.request.started"

    attributes = (
        analytics.Attribute("endpoint"),
        analytics.Attribute("method"),
        analytics.Attribute("view_name"),
        analytics.Attribute("action", required=False),
        analytics.Attribute("correlation_id", required=False),
        analytics.Attribute("user_id", required=False),
        analytics.Attribute("ip_address", required=False),
        analytics.Attribute("user_agent", required=False),
    )


class APIRequestCompletedEvent(analytics.Event):
    """Event fired when an API request completes successfully."""

    type = "api.request.completed"

    attributes = (
        analytics.Attribute("endpoint"),
        analytics.Attribute("method"),
        analytics.Attribute("view_name"),
        analytics.Attribute("action", required=False),
        analytics.Attribute("correlation_id", required=False),
        analytics.Attribute("duration_ms", type=int),
        analytics.Attribute("status_code", type=int),
        analytics.Attribute("db_queries", type=int, required=False),
        analytics.Attribute("cache_hits", type=int, required=False),
        analytics.Attribute("cache_misses", type=int, required=False),
        analytics.Attribute("user_id", required=False),
        analytics.Attribute("ip_address", required=False),
    )


class APIRequestErrorEvent(analytics.Event):
    """Event fired when an API request encounters an error."""

    type = "api.request.error"

    attributes = (
        analytics.Attribute("endpoint"),
        analytics.Attribute("method"),
        analytics.Attribute("view_name"),
        analytics.Attribute("action", required=False),
        analytics.Attribute("error_type"),
        analytics.Attribute("error_message"),
        analytics.Attribute("duration_ms", type=int, required=False),
        analytics.Attribute("correlation_id", required=False),
        analytics.Attribute("user_id", required=False),
        analytics.Attribute("ip_address", required=False),
        analytics.Attribute("status_code", type=int, required=False),
    )


class UserProfileCacheHitEvent(analytics.Event):
    """Event fired when user profile data is served from cache."""

    type = "user.profile.cache_hit"

    attributes = (
        analytics.Attribute("user_id"),
        analytics.Attribute("cache_key", required=False),
        analytics.Attribute("ip_address", required=False),
    )


class UserProfileViewedEvent(analytics.Event):
    """Event fired when a user profile is viewed."""

    type = "user.profile.viewed"

    attributes = (
        analytics.Attribute("user_id"),
        analytics.Attribute("viewer_id", required=False),
        analytics.Attribute("profile_completeness", type=float, required=False),
        analytics.Attribute("cache_miss", type=bool, required=False),
        analytics.Attribute("ip_address", required=False),
        analytics.Attribute("user_agent", required=False),
    )


class UserReviewCreatedEvent(analytics.Event):
    """Event fired when a user creates a review."""

    type = "user.review.created"

    attributes = (
        analytics.Attribute("review_id"),
        analytics.Attribute("reviewer_id"),
        analytics.Attribute("reviewed_user_id"),
        analytics.Attribute("rating", type=int),
        analytics.Attribute("review_length", type=int, required=False),
        analytics.Attribute("has_comment", type=bool, required=False),
    )


class ThreadParticipantAddedEvent(analytics.Event):
    """Event fired when a participant is added to a thread."""

    type = "thread.participant_added"

    attributes = (
        analytics.Attribute("thread_id"),
        analytics.Attribute("participant_id"),
        analytics.Attribute("added_by_id"),
        analytics.Attribute("participant_count", type=int, required=False),
        analytics.Attribute("thread_type", required=False),
    )


class MessageReadEvent(analytics.Event):
    """Event fired when a message is marked as read."""

    type = "message.read"

    attributes = (
        analytics.Attribute("message_id"),
        analytics.Attribute("reader_id"),
        analytics.Attribute("thread_id", required=False),
        analytics.Attribute("read_delay_minutes", type=int, required=False),
        analytics.Attribute("sender_id", required=False),
    )


# Register all events
analytics.register(APIRequestStartedEvent)
analytics.register(APIRequestCompletedEvent)
analytics.register(APIRequestErrorEvent)
analytics.register(UserProfileCacheHitEvent)
analytics.register(UserProfileViewedEvent)
analytics.register(UserReviewCreatedEvent)
analytics.register(ThreadParticipantAddedEvent)
analytics.register(MessageReadEvent)
