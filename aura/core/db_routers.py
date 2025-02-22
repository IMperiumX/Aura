from django.conf import settings


class PrimaryReplicaRouter:
    """
    A router to control all database operations on models in the
    auth and contenttypes applications.
    """

    def db_for_write(self, model, **hints):
        """Write only to primary."""
        return settings.DATABASE_CONNECTION_DEFAULT_NAME

    def allow_relation(self, obj1, obj2, **hints):
        """All relations are allowed as we don't have pool separation. And if a model in the auth or contenttypes apps is
        involved. It should be in the primary."""
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Only migrate on primary."""
        return db == settings.DATABASE_CONNECTION_DEFAULT_NAME
