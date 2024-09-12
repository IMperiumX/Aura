from django.db import models
from django.utils import timezone


class MessageQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(thread__participants=user)

    def for_thread(self, thread):
        return self.filter(thread=thread)

    def unread(self):
        return self.filter(read_at__isnull=True)

    def read(self):
        return self.filter(read_at__isnull=False)

    def sent_by(self, user):
        return self.filter(sender=user)

    def received_by(self, user):
        return self.exclude(sender=user)

    def mark_read(self):
        return self.update(read_at=timezone.now())

    def mark_unread(self):
        return self.update(read_at=None)

    def new_messages_count(self):
        return self.filter(read_at__isnull=True).count()

    def last_message(self):
        return self.last()

    def last_message_sender(self):
        return self.last().sender

    def last_message_date(self):
        return self.last().created


MessageManager = models.Manager.from_queryset(MessageQuerySet)


class ThreadQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(participants=user)

    def with_unread_messages(self, user):
        return self.filter(messages__read_at__isnull=True).exclude(
            messages__sender=user,
        )

    def with_new_messages(self, user):
        return self.filter(messages__read_at__isnull=True).exclude(
            messages__sender=user,
        )

    def with_last_message(self):
        return self.annotate(last_message_date=models.Max("messages__created"))

    def with_last_message_sender(self):
        return self.annotate(last_message_sender=models.Max("messages__sender"))

    def with_last_message_preview(self):
        return self.annotate(last_message_preview=models.Max("messages__text"))

    def with_last_message_sender_name(self):
        return self.annotate(
            last_message_sender_name=models.Max("messages__sender__get_full_name"),
        )

    def with_last_message_sender_avatar(self):
        return self.annotate(
            last_message_sender_avatar=models.Max("messages__sender__get_avatar_url"),
        )

    def with_last_message_sender_url(self):
        return self.annotate(
            last_message_sender_url=models.Max("messages__sender__get_absolute_url"),
        )

    def with_last_message_url(self):
        return self.annotate(last_message_url=models.Max("messages__get_absolute_url"))

    def with_last_message_time(self):
        return self.annotate(last_message_time=models.Max("messages__created"))


ThreadManager = models.Manager.from_queryset(ThreadQuerySet)
