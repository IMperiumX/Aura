from aura import analytics


class UserLoginEvent(analytics.Event):
    """Event fired when a user logs in."""

    type = "user.login"

    attributes = (
        analytics.Attribute("user_id"),
        analytics.Attribute("username"),
        analytics.Attribute("ip_address"),
        analytics.Attribute("user_agent", required=False),
        analytics.Attribute("login_method"),  # 'password', 'oauth', 'sso'
        analytics.Attribute("success", type=bool),
        analytics.Attribute("failure_reason", required=False),
    )


class UserLogoutEvent(analytics.Event):
    """Event fired when a user logs out."""

    type = "user.logout"

    attributes = (
        analytics.Attribute("user_id"),
        analytics.Attribute("session_duration_minutes", type=int, required=False),
        analytics.Attribute("logout_type"),  # 'manual', 'timeout', 'forced'
    )


class UserProfileUpdatedEvent(analytics.Event):
    """Event fired when user profile is updated."""

    type = "user.profile_updated"

    attributes = (
        analytics.Attribute("user_id"),
        analytics.Attribute("updated_fields"),  # JSON string of changed fields
        analytics.Attribute("role", required=False),
        analytics.Attribute("clinic_id", required=False),
    )


class AuthenticationFailedEvent(analytics.Event):
    """Event fired when authentication fails."""

    type = "auth.failed"

    attributes = (
        analytics.Attribute("username", required=False),
        analytics.Attribute("ip_address"),
        analytics.Attribute("failure_reason"),
        analytics.Attribute("attempt_count", type=int, required=False),
        analytics.Attribute("user_agent", required=False),
    )


class APIErrorEvent(analytics.Event):
    """Event fired when an API error occurs."""

    type = "api.error"

    attributes = (
        analytics.Attribute("endpoint"),
        analytics.Attribute("method"),
        analytics.Attribute("status_code", type=int),
        analytics.Attribute("error_type"),
        analytics.Attribute("user_id", required=False),
        analytics.Attribute("ip_address", required=False),
        analytics.Attribute("response_time_ms", type=int, required=False),
    )


class BackgroundTaskCompletedEvent(analytics.Event):
    """Event fired when a background task completes."""

    type = "task.completed"

    attributes = (
        analytics.Attribute("task_name"),
        analytics.Attribute("task_id"),
        analytics.Attribute("duration_seconds", type=int),
        analytics.Attribute("success", type=bool),
        analytics.Attribute("error_message", required=False),
        analytics.Attribute("records_processed", type=int, required=False),
    )


class ReportGeneratedEvent(analytics.Event):
    """Event fired when a report is generated."""

    type = "report.generated"

    attributes = (
        analytics.Attribute("report_type"),
        analytics.Attribute("requested_by_user_id"),
        analytics.Attribute("date_range"),
        analytics.Attribute("clinic_id", required=False),
        analytics.Attribute("generation_time_seconds", type=int),
        analytics.Attribute("record_count", type=int),
    )


class DataExportEvent(analytics.Event):
    """Event fired when data is exported."""

    type = "data.export"

    attributes = (
        analytics.Attribute("export_type"),
        analytics.Attribute("requested_by_user_id"),
        analytics.Attribute("record_count", type=int),
        analytics.Attribute("file_size_bytes", type=int),
        analytics.Attribute("export_format"),
        analytics.Attribute("includes_pii", type=bool),
    )


# Register all events
analytics.register(UserLoginEvent)
analytics.register(UserLogoutEvent)
analytics.register(UserProfileUpdatedEvent)
analytics.register(AuthenticationFailedEvent)
analytics.register(APIErrorEvent)
analytics.register(BackgroundTaskCompletedEvent)
analytics.register(ReportGeneratedEvent)
analytics.register(DataExportEvent)
