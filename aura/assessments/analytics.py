from aura import analytics


class PatientAssessmentSubmit(analytics.Event):
    type = "patient.assessment.submit"
    attributes = (
        analytics.Attribute("assessment_id"),
        analytics.Attribute("assessment_name"),
        analytics.Attribute("assessment_type"),
        analytics.Attribute("patient_id"),
    )


analytics.register(PatientAssessmentSubmit)
