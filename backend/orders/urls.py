
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
from .warranty_views import (
    OrderWarrantyDetailView,
    OrderWarrantyHistoryView,
    OrderWarrantyListCreateView,
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

    # HU-15: Garantías e historial de revisiones.
    path(
        "<int:pk>/warranties/",
        OrderWarrantyListCreateView.as_view(),
        name="order-warranty-list-create",
    ),
    path(
        "<int:pk>/warranties/<int:warranty_id>/",
        OrderWarrantyDetailView.as_view(),
        name="order-warranty-detail",
    ),
    path(
        "<int:pk>/warranties/<int:warranty_id>/history/",
        OrderWarrantyHistoryView.as_view(),
        name="order-warranty-history",
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