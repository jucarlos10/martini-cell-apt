from django.urls import path

from .views import (
    ClientChangeHistoryListView,
    ClientDetailView,
    ClientListCreateView,
    ClientLoyaltyAlertsView,
    ClientLoyaltyReviewView,
)


urlpatterns = [
    path("", ClientListCreateView.as_view(), name="client-list-create"),
    path("loyalty/alerts/", ClientLoyaltyAlertsView.as_view(), name="client-loyalty-alerts"),
    path("<int:pk>/", ClientDetailView.as_view(), name="client-detail"),
    path("<int:pk>/loyalty/", ClientLoyaltyReviewView.as_view(), name="client-loyalty-review"),
    path(
        "<int:pk>/history/",
        ClientChangeHistoryListView.as_view(),
        name="client-change-history",
    ),
]
