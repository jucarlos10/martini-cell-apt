
"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views.
"""

from django.contrib import admin
from django.urls import include, path

from accounts.views import UserDetailView, UserListCreateView


urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/auth/", include("accounts.urls")),

    path(
        "api/users/",
        UserListCreateView.as_view(),
        name="user-list-create",
    ),
    path(
        "api/users/<int:pk>/",
        UserDetailView.as_view(),
        name="user-detail",
    ),

    path("api/clients/", include("customers.urls")),
    path("api/devices/", include("devices.urls")),
    path("api/orders/", include("orders.urls")),

    # HU-13: Proveedores y repuestos
    path("api/inventory/", include("inventory.urls")),
]