from django.urls import path

from .views import (
    ClientChangeHistoryListView,
    ClientDetailView,
    ClientListCreateView,
)


urlpatterns = [
    path("", ClientListCreateView.as_view(), name="client-list-create"),
    path("<int:pk>/", ClientDetailView.as_view(), name="client-detail"),
    path(
        "<int:pk>/history/",
        ClientChangeHistoryListView.as_view(),
        name="client-change-history",
    ),
]