# -*- coding: utf-8 -*-
"""
Basic usage examples for merit-activa-api library.

Author: Marek Zacharewicz <marek@infortel.pl>
"""

from merit_activa import MeritClient

# ── Initialize client ──────────────────────────────
client = MeritClient(
    api_id="YOUR_API_ID",
    api_key="YOUR_API_KEY",
    # country="pl" is default (Poland / 360 Księgowość)
    # country="ee" for Estonia, "fi" for Finland
)


# ── 1. List departments ────────────────────────────
departments = client.get_departments()
for dept in departments:
    print(f"  {dept['Code']}: {dept['Name']} (active: {not dept['NonActive']})")


# ── 2. List tax rates (VAT) ────────────────────────
taxes = client.get_taxes()
for tax in taxes:
    print(f"  {tax['Code']}: {tax['Name']} (ID: {tax['Id']})")


# ── 3. Create a customer ───────────────────────────
customer = client.create_customer(
    name="Firma Testowa Sp. z o.o.",
    reg_no="1234567890",           # NIP
    email="faktury@firma-testowa.pl",
    address="ul. Testowa 1",
    city="Warszawa",
    postal_code="00-001",
    payment_deadline=14,           # 14 days to pay
)
print(f"Customer created: {customer['Id']} — {customer['Name']}")


# ── 4. Find or create customer (idempotent) ────────
customer = client.find_or_create_customer(
    name="Urząd Miasta Krakowa",
    reg_no="6761013717",
    email="faktury@krakow.pl",
    payment_deadline=14,
)


# ── 5. Create a simple invoice ─────────────────────
invoice = client.create_simple_invoice(
    customer_name="Firma Testowa Sp. z o.o.",
    customer_nip="1234567890",
    description="Usługa konsultingowa NIS2 - kwiecień 2026",
    net_amount=799.00,
    vat_rate=23,
    department_code="NIS2PILOT",   # Department must exist in Merit
)
print(f"Invoice created: {invoice['InvoiceNo']} (ID: {invoice['InvoiceId']})")


# ── 6. Full invoice flow (create + email) ──────────
result = client.invoice_full_flow(
    customer_name="Szpital Miejski",
    customer_nip="6761013717",
    customer_email="faktury@szpital.pl",
    description="NIS2Pilot Professional - subskrypcja maj 2026",
    net_amount=799.00,
    department_code="NIS2PILOT",
    send_email=True,
)
print(f"Invoice: {result['invoice_no']}, email sent: {result['email_sent']}")


# ── 7. Send invoice PDF by email ───────────────────
client.send_invoice_by_email(invoice["InvoiceId"])


# ── 8. Download invoice as PDF ─────────────────────
import base64

pdf_data = client.get_invoice_pdf(invoice["InvoiceId"])
with open(pdf_data["FileName"], "wb") as f:
    f.write(base64.b64decode(pdf_data["FileContent"]))
print(f"PDF saved: {pdf_data['FileName']}")


# ── 9. List invoices (with department filter) ──────
invoices = client.get_invoices(
    period_start="20260401",
    period_end="20260430",
    department_code="NIS2PILOT",   # Client-side filter
)
for inv in invoices:
    print(f"  {inv.get('InvoiceNo')}: {inv.get('TotalAmount')} PLN")


# ── 10. Long period (auto-segmented) ───────────────
all_invoices = client.get_invoices_period(
    period_start="20260101",
    period_end="20261231",
    department_code="NIS2PILOT",
)
print(f"Total invoices in 2026: {len(all_invoices)}")


# ── 11. Payments ────────────────────────────────────
payment_types = client.get_payment_types()
print(f"Payment types: {[pt.get('Name') for pt in payment_types]}")


# ── 12. Reports ─────────────────────────────────────
debts = client.get_customer_debts_report()
print(f"Outstanding debts: {len(debts)} customers")

pnl = client.get_profit_loss_statement("20260101", "20260331")
print(f"P&L Q1 2026: {pnl}")
