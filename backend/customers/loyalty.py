from django.db.models import Count, Max
from django.db.models.functions import Coalesce

from .models import Client


def target_for_cycle(completed_cycles):
    """First six visits, then five, then four on each subsequent cycle."""
    return 6 if completed_cycles == 0 else 5 if completed_cycles == 1 else 4


def with_loyalty_counts(queryset=None):
    """Compute visits from stored service orders, never from public page views."""
    if queryset is None:
        queryset = Client.objects.all()

    return queryset.annotate(
        loyalty_order_count=Count("service_orders", distinct=True),
        loyalty_reviewed_milestone=Coalesce(
            Max("loyalty_reviews__milestone"), 0
        ),
        loyalty_completed_cycles=Count("loyalty_reviews", distinct=True),
    )


def loyalty_summary(client):
    count = getattr(client, "loyalty_order_count", None)
    reviewed = getattr(client, "loyalty_reviewed_milestone", None)
    cycles = getattr(client, "loyalty_completed_cycles", None)

    if count is None:
        count = client.service_orders.count()
    if reviewed is None:
        reviewed = client.loyalty_reviews.aggregate(
            milestone=Max("milestone")
        )["milestone"] or 0
    if cycles is None:
        cycles = client.loyalty_reviews.count()

    target = target_for_cycle(cycles)
    next_milestone = reviewed + target

    pending = (
        next_milestone
        if client.rut and client.is_active and count >= next_milestone
        else None
    )

    return {
        "loyalty_order_count": count,
        "loyalty_pending_milestone": pending,
        "loyalty_next_milestone": next_milestone,
        "loyalty_cycle_target": target,
        "loyalty_cycle_visits": max(0, count - reviewed),
    }
