from django.urls import path

from .views import (
    OrderEvidenceDownloadView,
    OrderEvidenceListCreateView,
    ServiceOrderDetailView,
    ServiceOrderListCreateView,
)


urlpatterns = [
    path(
        "",
        ServiceOrderListCreateView.as_view(),
        name="service-order-list-create",
    ),
    path(
        "<int:pk>/",
        ServiceOrderDetailView.as_view(),
        name="service-order-detail",
    ),
    path(
        "<int:pk>/evidence/",
        OrderEvidenceListCreateView.as_view(),
        name="order-evidence-list-create",
    ),
    path(
        "<int:pk>/evidence/<int:evidence_id>/download/",
        OrderEvidenceDownloadView.as_view(),
        name="order-evidence-download",
    ),
]