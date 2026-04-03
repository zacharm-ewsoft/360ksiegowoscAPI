# -*- coding: utf-8 -*-
"""
Example: Integration with Django project (e.g. NIS2Pilot, ClipForge).

Add to your Django settings.py:
    MERIT_API_ID = env("MERIT_API_ID")
    MERIT_API_KEY = env("MERIT_API_KEY")
    MERIT_DEPARTMENT = "NIS2PILOT"  # or "CLIPFORGE", "BOJAR", etc.

Author: Marek Zacharewicz <marek@infortel.pl>
"""

# ── Django settings integration ────────────────────

# settings.py
# MERIT_API_ID = os.environ.get("MERIT_API_ID", "")
# MERIT_API_KEY = os.environ.get("MERIT_API_KEY", "")
# MERIT_DEPARTMENT = os.environ.get("MERIT_DEPARTMENT", "DEFAULT")

# ── Service layer (e.g. apps/billing/merit_service.py) ──

from django.conf import settings
from merit_activa import MeritClient, MeritApiError


def get_merit_client() -> MeritClient:
    """Get configured Merit API client."""
    return MeritClient(
        api_id=settings.MERIT_API_ID,
        api_key=settings.MERIT_API_KEY,
    )


def issue_invoice_for_subscription(subscription) -> dict:
    """Issue invoice in Merit Aktiva after payment.

    Args:
        subscription: Django Subscription model instance.

    Returns:
        Dict with invoice_id, invoice_no, email_sent.
    """
    client = get_merit_client()
    org = subscription.organization

    result = client.invoice_full_flow(
        customer_name=org.name,
        customer_nip=org.nip,
        customer_email=subscription.invoice_email or org.user.email,
        description=f"{settings.MERIT_DEPARTMENT} {subscription.get_plan_display()} — "
                     f"subskrypcja {subscription.get_billing_cycle_display()}",
        net_amount=subscription.price_net,
        department_code=settings.MERIT_DEPARTMENT,
        payment_deadline=subscription.payment_term_days or 14,
        send_email=True,
    )

    # Save Merit invoice ID to Django model
    from apps.billing.models import Invoice as DjangoInvoice

    django_invoice = DjangoInvoice.objects.filter(
        subscription=subscription,
        status="draft",
    ).first()

    if django_invoice:
        django_invoice.merit_invoice_id = result["invoice_id"]
        django_invoice.status = "issued"
        django_invoice.save(update_fields=["merit_invoice_id", "status"])

    return result


# ── Celery task example ────────────────────────────

# from celery import shared_task
#
# @shared_task(bind=True, max_retries=3)
# def issue_merit_invoice(self, subscription_id: int):
#     """Celery task: issue invoice in Merit after PayU payment."""
#     from apps.billing.models import Subscription
#     subscription = Subscription.objects.get(id=subscription_id)
#     try:
#         result = issue_invoice_for_subscription(subscription)
#         logger.info("Merit invoice %s created for %s",
#                     result["invoice_no"], subscription.organization.name)
#     except MeritApiError as e:
#         logger.error("Merit API error: %s", e)
#         raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
