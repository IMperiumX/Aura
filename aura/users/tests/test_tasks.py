import pytest
from celery.result import EagerResult
from django.test import override_settings

from aura.users.tasks import get_users_count
from aura.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_user_count(settings):
    """A basic test to execute the get_users_count Celery task."""
    batch_size = 3
    UserFactory.create_batch(batch_size)
    task_result = get_users_count.delay()
    assert isinstance(task_result, EagerResult)
    assert task_result.result == batch_size
