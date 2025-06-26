from aura import analytics


class PatientCreatedEvent(analytics.Event):
    """Event fired when a new patient is created."""
    type = "patient.created"

    attributes = (
        analytics.Attribute("patient_id"),
        analytics.Attribute("clinic_id"),
        analytics.Attribute("first_name"),
        analytics.Attribute("last_name"),
        analytics.Attribute("email", required=False),
        analytics.Attribute("created_by_user_id"),
    )


class PatientUpdatedEvent(analytics.Event):
    """Event fired when patient information is updated."""
    type = "patient.updated"

    attributes = (
        analytics.Attribute("patient_id"),
        analytics.Attribute("clinic_id"),
        analytics.Attribute("updated_fields"),  # JSON string of changed fields
        analytics.Attribute("updated_by_user_id"),
    )


class AppointmentCreatedEvent(analytics.Event):
    """Event fired when a new appointment is scheduled."""
    type = "appointment.created"

    attributes = (
        analytics.Attribute("appointment_id"),
        analytics.Attribute("patient_id"),
        analytics.Attribute("clinic_id"),
        analytics.Attribute("provider_id", required=False),
        analytics.Attribute("scheduled_time"),
        analytics.Attribute("created_by_user_id"),
        analytics.Attribute("external_id", required=False),
    )


class AppointmentStatusChangedEvent(analytics.Event):
    """Event fired when appointment status changes."""
    type = "appointment.status_changed"

    attributes = (
        analytics.Attribute("appointment_id"),
        analytics.Attribute("patient_id"),
        analytics.Attribute("clinic_id"),
        analytics.Attribute("old_status", required=False),
        analytics.Attribute("new_status"),
        analytics.Attribute("changed_by_user_id", required=False),
        analytics.Attribute("duration_in_status_minutes", type=int, required=False),
    )


class AppointmentCancelledEvent(analytics.Event):
    """Event fired when an appointment is cancelled."""
    type = "appointment.cancelled"

    attributes = (
        analytics.Attribute("appointment_id"),
        analytics.Attribute("patient_id"),
        analytics.Attribute("clinic_id"),
        analytics.Attribute("reason", required=False),
        analytics.Attribute("cancelled_by_user_id"),
        analytics.Attribute("notice_hours", type=int, required=False),  # How much notice was given
    )


class AssessmentCompletedEvent(analytics.Event):
    """Event fired when a patient assessment is completed."""
    type = "assessment.completed"

    attributes = (
        analytics.Attribute("assessment_id"),
        analytics.Attribute("patient_id"),
        analytics.Attribute("assessment_type"),
        analytics.Attribute("risk_level"),
        analytics.Attribute("completion_time_minutes", type=int, required=False),
        analytics.Attribute("num_questions", type=int, required=False),
    )


class RiskPredictionGeneratedEvent(analytics.Event):
    """Event fired when a risk prediction is generated."""
    type = "risk_prediction.generated"

    attributes = (
        analytics.Attribute("prediction_id"),
        analytics.Attribute("patient_id"),
        analytics.Attribute("assessment_id"),
        analytics.Attribute("confidence_level", type=float),
        analytics.Attribute("risk_factors"),  # JSON string of risk factors
    )


# Register all events
analytics.register(PatientCreatedEvent)
analytics.register(PatientUpdatedEvent)
analytics.register(AppointmentCreatedEvent)
analytics.register(AppointmentStatusChangedEvent)
analytics.register(AppointmentCancelledEvent)
analytics.register(AssessmentCompletedEvent)
analytics.register(RiskPredictionGeneratedEvent)
