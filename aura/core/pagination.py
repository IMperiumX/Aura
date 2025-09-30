from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "data": data,
                "pagination": {
                    "count": self.page.paginator.count,
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                    "page_size": self.page_size,
                    "total_pages": self.page.paginator.num_pages,
                },
                "meta": {
                    "timestamp": self.get_timestamp(),
                    "request_id": self.get_request_id(),
                },
            }
        )

    def get_timestamp(self):
        from django.utils import timezone

        return timezone.now().isoformat()

    def get_request_id(self):
        import uuid

        return str(uuid.uuid4())
