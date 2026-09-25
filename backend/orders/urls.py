
from django.urls import path

from .financial_views import OrderFinancialView
from .public_tracking import PublicOrderStatusView
from .views import (
    OrderEvidenceDownloadView,
    OrderEvidenceListCreateView,
    OrderStatusHistoryView,
    OrderStatusView,
    OrderTechnicalReportHistoryView,
    OrderTechnicalReportView,
    OrderTimesView,
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
        "public/<str:tracking_code>/",
        PublicOrderStatusView.as_view(),
        name="public-order-status",
    ),
    path(
        "<int:pk>/",
        ServiceOrderDetailView.as_view(),
        name="service-order-detail",
    ),
    path(
        "<int:pk>/status/",
        OrderStatusView.as_view(),
        name="order-status",
    ),
    path(
        "<int:pk>/status/history/",
        OrderStatusHistoryView.as_view(),
        name="order-status-history",
    ),
    path(
        "<int:pk>/times/",
        OrderTimesView.as_view(),
        name="order-times",
    ),

    # HU-14: Costos, precios y margen estimado.
    path(
        "<int:pk>/financial/",
        OrderFinancialView.as_view(),
        name="order-financial",
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
    path(
        "<int:pk>/technical-report/",
        OrderTechnicalReportView.as_view(),
        name="order-technical-report",
    ),
    path(
        "<int:pk>/technical-report/history/",
        OrderTechnicalReportHistoryView.as_view(),
        name="order-technical-report-history",
    ),
]