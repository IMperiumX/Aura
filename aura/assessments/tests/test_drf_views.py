import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from aura.assessments.models import HealthAssessment
from aura.assessments.tests.factories import HealthAssessmentFactory
from aura.users.tests.factories import PatientFactory
from aura.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestHealthAssessmentViewSet:
    @pytest.fixture()
    def api_client(self):
        return APIClient()

    @pytest.fixture()
    def user(self):
        return UserFactory()

    @pytest.fixture()
    def patient_profile(self, user):
        return PatientFactory(user=user)

    @pytest.fixture()
    def health_assessment(self, patient_profile):
        return HealthAssessmentFactory(patient=patient_profile)

    def test_list_health_assessments(self, api_client, health_assessment, user):
        api_client.force_authenticate(user=user)
        url = reverse("api:assessments-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["id"] == health_assessment.id

    def test_list_health_assessments_of_other_user(self, api_client, user):
        api_client.force_authenticate(user=user)
        url = reverse("api:assessments-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0

    def test_retrieve_health_assessment(self, api_client, health_assessment, user):
        api_client.force_authenticate(user=user)
        url = reverse("api:assessments-detail", args=[health_assessment.id])
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == health_assessment.id

    def test_create_health_assessment(self, api_client, user):
        api_client.force_authenticate(user=user)
        url = reverse("api:assessments-list")
        data = {
            "assessment_type": "general",
            "risk_level": "low",
            "recommendations": "string",
            "responses": {},
            "result": "string",
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert HealthAssessment.objects.count() == 1
        assert response.data["patient"]["id"] == user.patient_profile.id
        assert response.data["status"] == "draft"
        assert response.data["assessment_type"] == "general"

    def test_update_health_assessment(self, api_client, health_assessment, user):
        api_client.force_authenticate(user=user)
        url = reverse("api:assessments-detail", args=[health_assessment.id])
        data = {
            "status": "in_progress",
        }
        response = api_client.patch(url, data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "in_progress"
        url = reverse("api:assessments-detail", args=[health_assessment.id])
        response = api_client.get(url)
        assert response.data["status"] == "in_progress"

    def test_delete_health_assessment(self, api_client, health_assessment, user):
        api_client.force_authenticate(user=user)
        url = reverse("api:assessments-detail", args=[health_assessment.id])
        response = api_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        url = reverse("api:assessments-list")
        response = api_client.get(url)
        assert len(response.data) == 0
