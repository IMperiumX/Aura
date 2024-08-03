from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from llama_index.core import Document

from aura.core.services import RecommendationEngine


@pytest.fixture()
def recommendation_engine():
    return RecommendationEngine()


@pytest.fixture()
def mock_db_reader():
    with patch("aura.core.services.DatabaseReader") as mock:
        yield mock


def test_fetch_documents_from_storage_initializes_db_reader_correctly(
    recommendation_engine,
    mock_db_reader,
):
    query = 'SELECT "assessments_healthassessment"."id", "assessments_healthassessment"."recommendations", "assessments_healthassessment"."responses", "assessments_healthassessment"."result" FROM "assessments_healthassessment"'

    db_url = settings.DATABASES["default"]

    recommendation_engine.fetch_documents_from_storage(query)

    mock_db_reader.assert_called_once_with(
        scheme="postgresql",
        host=db_url["HOST"],
        port=db_url["PORT"],
        user=db_url["USER"],
        password=db_url["PASSWORD"],
        dbname=db_url["NAME"],
    )


def test_fetch_documents_from_storage_calls_load_data_with_correct_query(
    recommendation_engine,
    mock_db_reader,
):
    query = 'SELECT "assessments_healthassessment"."id", "assessments_healthassessment"."recommendations", "assessments_healthassessment"."responses", "assessments_healthassessment"."result" FROM "assessments_healthassessment"'

    mock_instance = mock_db_reader.return_value
    mock_instance.load_data = MagicMock(return_value=[])

    recommendation_engine.fetch_documents_from_storage(query)

    mock_instance.load_data.assert_called_once_with(query=query)


def test_fetch_documents_from_storage_returns_expected_documents(
    recommendation_engine,
    mock_db_reader,
):
    query = 'SELECT "assessments_healthassessment"."id", "assessments_healthassessment"."recommendations", "assessments_healthassessment"."responses", "assessments_healthassessment"."result" FROM "assessments_healthassessment"'

    expected_documents = [Document(text="doc1"), Document(text="doc2")]
    mock_instance = mock_db_reader.return_value
    mock_instance.load_data = MagicMock(return_value=expected_documents)

    documents = recommendation_engine.fetch_documents_from_storage(query)

    assert documents == expected_documents
