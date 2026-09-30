from django.urls import path

from .financial_views import OrderFinancialView
from .indicator_views import OperationalIndicatorsView
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
from .viability_views import OrderViabilityView
from .warranty_request_views import (
    WarrantyRequestAdminNoteView,
    WarrantyRequestDetailView,
    WarrantyRequestEvidenceView,
    WarrantyRequestHistoryView,
    WarrantyRequestListCreateView,
    WarrantyRequestProposalView,
    WarrantyRequestResolveView,
    WarrantyRequestReturnView,
    WarrantyRequestsByWarrantyView,
)
from .warranty_summary_views import OrderWarrantySummaryListView
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

    # HU-16: Indicadores operacionales.
    path(
        "indicators/",
        OperationalIndicatorsView.as_view(),
        name="operational-indicators",
    ),

    # TEC-02: Listado general de garantías registradas.
    path(
        "warranties/",
        OrderWarrantySummaryListView.as_view(),
        name="order-warranty-summary-list",
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

    # HU-15 / HU-21: Garantías e historial de revisiones por orden.
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

    # HU-22: Solicitudes/reclamos asociados a garantías.
    path(
        "<int:pk>/warranty-requests/",
        WarrantyRequestListCreateView.as_view(),
        name="warranty-request-list-create",
    ),
    path(
        "<int:pk>/warranty-requests/<int:request_id>/",
        WarrantyRequestDetailView.as_view(),
        name="warranty-request-detail",
    ),
    path(
        "<int:pk>/warranty-requests/<int:request_id>/history/",
        WarrantyRequestHistoryView.as_view(),
        name="warranty-request-history",
    ),
    path(
        "<int:pk>/warranty-requests/<int:request_id>/evidence/",
        WarrantyRequestEvidenceView.as_view(),
        name="warranty-request-evidence",
    ),
    path(
        "<int:pk>/warranties/<int:warranty_id>/requests/",
        WarrantyRequestsByWarrantyView.as_view(),
        name="warranty-requests-by-warranty",
    ),

    # HU-23: Flujo de resolución de solicitudes de garantía.
    path(
        "<int:pk>/warranty-requests/<int:request_id>/proposal/",
        WarrantyRequestProposalView.as_view(),
        name="warranty-request-proposal",
    ),
    path(
        "<int:pk>/warranty-requests/<int:request_id>/return/",
        WarrantyRequestReturnView.as_view(),
        name="warranty-request-return",
    ),
    path(
        "<int:pk>/warranty-requests/<int:request_id>/resolve/",
        WarrantyRequestResolveView.as_view(),
        name="warranty-request-resolve",
    ),
    path(
        "<int:pk>/warranty-requests/<int:request_id>/admin-note/",
        WarrantyRequestAdminNoteView.as_view(),
        name="warranty-request-admin-note",
    ),

    # HU-16: Evaluación e índice de viabilidad.
    path(
        "<int:pk>/viability/",
        OrderViabilityView.as_view(),
        name="order-viability",
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
