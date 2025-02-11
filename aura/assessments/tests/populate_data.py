# myapp/management/commands/populate_data.py
from django.db import transaction


@transaction.atomic()
def handle():
    import random

    from aura.users.tests.factories import PatientFactory
    from aura.users.tests.factories import UserFactory

    from .factories import AssessmentFactory
    from .factories import PatientAssessmentFactory
    from .factories import QuestionFactory
    from .factories import ResponseFactory
    from .factories import RiskPredictionFactory

    options = {
        "assessments": random.randint(1, 100),
        "questions": random.randint(1, 10),
        "responses": random.randint(1, 5),
        "patient_assessments": random.randint(1, 200),
        "risk_predictions": random.randint(1, 3),
        "patients": random.randint(1, 50),
        "users": random.randint(1, 50),
    }

    num_assessments = options["assessments"]
    num_questions = options["questions"]
    num_responses = options["responses"]
    num_patient_assessments = options["patient_assessments"]
    num_risk_predictions = options["risk_predictions"]
    num_patients = options["patients"]
    num_users = options["users"]

    print("Starting data population...")

    # --- Create Users ---
    print(f"Creating {num_users} users...")
    UserFactory.create_batch(num_users)

    # --- Create Patients ---
    print(f"Creating {num_patients} patients...")
    PatientFactory.create_batch(num_patients)

    # --- Create Assessments ---
    print(f"Creating {num_assessments} assessments...")
    assessments = AssessmentFactory.create_batch(num_assessments)

    # --- Create Questions (and link them to Assessments) ---
    print("Creating questions...")
    questions = []
    for assessment in assessments:
        for _ in range(num_questions):
            question = QuestionFactory.create(
                assessment=assessment,
            )  # Pass the assessment
            questions.append(question)

    # --- Create Responses (and link them to Questions) ---
    print("Creating responses...")
    for question in questions:
        ResponseFactory.create_batch(
            num_responses,
            question=question,
        )  # Pass the question.

    # --- Create Patient Assessments ---
    print(f"Creating {num_patient_assessments} patient assessments...")
    patient_assessments = PatientAssessmentFactory.create_batch(num_patient_assessments)

    # --- Create Risk Predictions ---
    print("Creating risk predictions...")
    for pa in patient_assessments:
        RiskPredictionFactory.create_batch(num_risk_predictions, assessment=pa)

    print("Data population complete.")


handle()
