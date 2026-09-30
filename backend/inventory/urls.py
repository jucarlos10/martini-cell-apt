from django.urls import path

from .order_views import (
    OrderPartCorrectionHistoryView,
    OrderPartCorrectionView,
    OrderPartsView,
)
from .views import (
    PartDetailView,
    PartListCreateView,
    SupplierDetailView,
    SupplierListCreateView,
)


urlpatterns = [
    path(
        "suppliers/",
        SupplierListCreateView.as_view(),
        name="supplier-list-create",
    ),
    path(
        "suppliers/<int:pk>/",
        SupplierDetailView.as_view(),
        name="supplier-detail",
    ),
    path(
        "parts/",
        PartListCreateView.as_view(),
        name="part-list-create",
    ),
    path(
        "parts/<int:pk>/",
        PartDetailView.as_view(),
        name="part-detail",
    ),

    # HU-13: Repuestos utilizados en una orden.
    path(
        "orders/<int:order_id>/parts/",
        OrderPartsView.as_view(),
        name="order-parts",
    ),

    # HU-24: Corrección de un repuesto registrado.
    path(
        (
            "orders/<int:order_id>/parts/"
            "<int:order_part_id>/correction/"
        ),
        OrderPartCorrectionView.as_view(),
        name="order-part-correction",
    ),
    path(
        (
            "orders/<int:order_id>/parts/"
            "<int:order_part_id>/correction-history/"
        ),
        OrderPartCorrectionHistoryView.as_view(),
        name="order-part-correction-history",
    ),
]
