# merit-activa-api

**Python client library for [Merit Aktiva](https://www.merit.ee/) / [360 Księgowość](https://www.360ksiegowosc.pl/) API.**

Create invoices, manage customers, register payments, integrate with KSeF — all from Python. Perfect for SaaS platforms, e-commerce, and any system that needs automated invoicing through Merit Aktiva accounting software.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/merit-activa-api.svg)](https://pypi.org/project/merit-activa-api/)

---

## Why this library?

[Merit Aktiva](https://www.merit.ee/) (known as [360 Księgowość](https://www.360ksiegowosc.pl/) in Poland) is a popular cloud accounting software in the Baltic region and Poland. This library provides a clean Python interface to its REST API, so you can automate your accounting workflows:

- **SaaS billing** — automatically create invoices when customers pay via PayU, Stripe, etc.
- **Multi-project accounting** — track revenue per project/platform using departments
- **KSeF compliance** — Merit handles mandatory KSeF submission in Poland automatically
- **Customer management** — sync customers from your app to accounting
- **Payment tracking** — register payments and mark invoices as paid programmatically

## Features

- **Full API coverage** — 60+ endpoints: sales/purchase invoices, customers, vendors, payments, items, GL transactions, fixed assets, reports
- **Payment registration** — `register_payu_payment()` marks invoices as paid with payment gateway reference
- **One-call invoicing** — `invoice_and_pay()` does everything: customer → invoice → payment → KSeF → email
- **Invoice email delivery** — send invoice PDFs directly from Merit to customers
- **PDF download** — get invoice PDFs as base64
- **Department support** — assign invoices to departments (per project/platform)
- **KSeF ready** — Poland's mandatory e-invoicing system, handled automatically by Merit
- **Long period queries** — auto-segments requests into 90-day chunks (API limit)
- **Service items** — create products/services via API for consistent invoicing
- **Multi-country** — Poland (360 Księgowość), Estonia, Finland
- **Type hints** — full typing for IDE support
- **Minimal dependencies** — only `requests`

## Installation

```bash
pip install merit-activa-api
```

Or install from source:

```bash
git clone https://github.com/zacharm-ewsoft/360ksiegowoscAPI.git
cd 360ksiegowoscAPI
pip install -e .
```

## Quick Start

### 1. Get API credentials

In 360 Księgowość / Merit Aktiva:
**Ustawienia → Główne ustawienia → API → Wygeneruj klucze**

You'll get an `API ID` (UUID) and `API Key` (base64 string).

### 2. Initialize client

```python
from merit_activa import MeritClient

client = MeritClient(
    api_id="your_api_id",
    api_key="your_api_key",
    # country="pl"  ← default (Poland / 360 Księgowość)
    # country="ee"  ← Estonia
    # country="fi"  ← Finland
)
```

### 3. Create a customer

```python
customer = client.create_customer(
    name="Firma ABC Sp. z o.o.",
    reg_no="1234567890",           # NIP
    email="faktury@firma.pl",
    address="ul. Przykładowa 1",
    city="Warszawa",
    postal_code="00-001",
    payment_deadline=14,
)
print(customer)  # {"Id": "abc-123-...", "Name": "Firma ABC Sp. z o.o."}
```

### 4. Create an invoice

```python
result = client.create_simple_invoice(
    customer_name="Firma ABC Sp. z o.o.",
    customer_nip="1234567890",
    description="SaaS subscription - April 2026",
    net_amount=799.00,
    vat_rate=23,
    department_code="MYPROJECT",
)
print(result)  # {"InvoiceId": "...", "InvoiceNo": "FV/2026/001"}
```

### 5. Register payment (e.g. after PayU/Stripe webhook)

```python
client.register_payu_payment(
    invoice_id=result["InvoiceId"],
    amount=982.77,  # gross amount (799 + 23% VAT)
    payu_order_id="WZHF5FFDRJ140731GUEST000P01",
)
# Invoice is now marked as paid in Merit
```

### 6. Send invoice by email

```python
client.send_invoice_by_email(result["InvoiceId"])
# Merit sends PDF to customer's email automatically
```

### 7. Full flow — one call does everything

```python
result = client.invoice_and_pay(
    customer_name="Firma ABC Sp. z o.o.",
    customer_nip="1234567890",
    customer_email="faktury@firma.pl",
    description="Professional subscription - May 2026",
    net_amount=799.00,
    department_code="MYPROJECT",
    payu_order_id="WZHF5FFDRJ140731GUEST000P01",
)
# Creates customer (if needed) → creates invoice → registers payment → sends email
# Merit automatically submits to KSeF (Poland)
print(result)
# {
#     "customer_id": "...",
#     "invoice_id": "...",
#     "invoice_no": "FV/2026/...",
#     "email_sent": True,
#     "payment_registered": True
# }
```

## Departments (Działy)

Departments let you track revenue per project/platform in a single Merit account:

```python
# List existing departments
departments = client.get_departments()

# Use in invoices — each project gets its own department
client.create_simple_invoice(
    ...,
    department_code="NIS2PILOT",  # or "CLIPFORGE", "SHOPIFY", etc.
)

# Filter invoices by department
invoices = client.get_invoices(
    period_start="20260401",
    period_end="20260430",
    department_code="NIS2PILOT",
)
```

> **Note:** Departments must be created manually in Merit UI:
> **Menu → Ustawienia → Dodatkowe parametry → Działy**

## Service Items (Artykuły)

Create reusable service/product items for consistent invoicing:

```python
# Get VAT rate ID (needed for items)
taxes = client.get_taxes()
vat23_id = next(t["Id"] for t in taxes if "23" in t["Code"])

# Create service items
client.create_items([
    {
        "Code": "SVC-PRO-M",
        "Description": "Professional Plan — monthly subscription",
        "Type": 2,          # 2 = service
        "Usage": 1,         # 1 = sales
        "TaxId": vat23_id,
        "UOMName": "szt.",
        "SalesAccCode": "700",
    },
])

# List all items
items = client.get_items()
```

## KSeF Integration (Poland)

[KSeF](https://www.podatki.gov.pl/ksef/) (Krajowy System e-Faktur) is Poland's mandatory e-invoicing system, required for all businesses since April 2026.

360 Księgowość has **built-in KSeF integration**. When you create an invoice via this library, Merit automatically submits it to KSeF — no extra code needed.

```python
# Create invoice — Merit handles KSeF automatically
invoice = client.create_simple_invoice(
    customer_name="Firma ABC",
    customer_nip="1234567890",
    description="Consulting service",
    net_amount=299.00,
)

# After KSeF processes it, the KSeF number is stored in Merit:
details = client.get_invoice_details(invoice["InvoiceId"])
ksef_number = details.get("KsefNumber")
# e.g. "1234567890-20260403-A1B2C3-D4E5F6-AB"

# You can also pass a KSeF number when creating invoices:
client.create_simple_invoice(
    ...,
    ksef_number="1234567890-20260403-A1B2C3-D4E5F6-AB",
)
```

## Django / Celery Integration

Ideal for SaaS platforms — trigger invoicing from payment webhooks:

```python
# settings.py
MERIT_API_ID = os.environ["MERIT_API_ID"]
MERIT_API_KEY = os.environ["MERIT_API_KEY"]
MERIT_DEPARTMENT = "MYPROJECT"

# apps/billing/services.py
from django.conf import settings
from merit_activa import MeritClient

def get_merit_client():
    return MeritClient(
        api_id=settings.MERIT_API_ID,
        api_key=settings.MERIT_API_KEY,
    )

# apps/billing/tasks.py (Celery)
@shared_task(bind=True, max_retries=3)
def issue_invoice_after_payment(self, subscription_id, payu_order_id):
    """Called from PayU webhook after COMPLETED status."""
    from apps.billing.models import Subscription
    sub = Subscription.objects.get(id=subscription_id)
    client = get_merit_client()

    result = client.invoice_and_pay(
        customer_name=sub.organization.name,
        customer_nip=sub.organization.nip,
        customer_email=sub.invoice_email,
        description=f"{settings.MERIT_DEPARTMENT} {sub.plan} — {sub.billing_cycle}",
        net_amount=sub.price_net,
        department_code=settings.MERIT_DEPARTMENT,
        payu_order_id=payu_order_id,
    )
    sub.merit_invoice_id = result["invoice_id"]
    sub.save()
```

See [examples/django_integration.py](examples/django_integration.py) for more details.

## API Reference

### Client Initialization

```python
MeritClient(api_id, api_key, country="pl", base_url=None, timeout=30)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_id` | str | required | API identifier (UUID) from Merit settings |
| `api_key` | str | required | API secret key (base64 string) |
| `country` | str | `"pl"` | Country: `"pl"` (Poland), `"ee"` (Estonia), `"fi"` (Finland) |
| `base_url` | str | None | Override base URL (takes precedence over country) |
| `timeout` | int | 30 | Request timeout in seconds |

### High-Level Convenience Methods

| Method | Description |
|--------|-------------|
| `find_or_create_customer(name, reg_no, ...)` | Find customer by NIP, create if not exists |
| `create_simple_invoice(name, nip, desc, amount, ...)` | Create a single-line invoice with auto tax lookup |
| `invoice_full_flow(name, nip, email, ...)` | Customer → invoice → email in one call |
| `invoice_and_pay(name, nip, email, ..., payu_order_id)` | Customer → invoice → payment → email in one call |
| `register_payu_payment(invoice_id, amount, payu_order_id)` | Register payment from PayU/Stripe/etc. |

### Customers

| Method | Description |
|--------|-------------|
| `get_customers(name, reg_no, ...)` | List customers with filters |
| `create_customer(name, reg_no, email, ...)` | Create new customer |
| `update_customer(customer_id, **fields)` | Update customer fields |
| `get_customer_groups()` | List customer groups |
| `create_customer_group(code, name)` | Create customer group |

### Sales Invoices

| Method | Description |
|--------|-------------|
| `get_invoices(start, end, unpaid, department)` | List invoices (max 3 months) |
| `get_invoices_period(start, end, ...)` | List invoices (auto-segments long periods) |
| `get_invoice_details(invoice_id)` | Full invoice details |
| `create_invoice(customer, rows, tax, ...)` | Create invoice with full control |
| `delete_invoice(invoice_id)` | Delete invoice |
| `create_credit_invoice(data)` | Create credit/corrective note |
| `send_invoice_by_email(invoice_id)` | Email invoice PDF to customer |
| `get_invoice_pdf(invoice_id)` | Download PDF (base64) |

### Payments

| Method | Description |
|--------|-------------|
| `get_payments(start, end)` | List payments |
| `get_payment_types()` | Available payment types |
| `send_payment(data)` | Register sales invoice payment |
| `send_purchase_payment(data)` | Register purchase invoice payment |
| `delete_payment(id)` | Delete payment |
| `send_bank_statement(data)` | Import bank statement |
| `send_prepayment(data)` | Register prepayment |

### Items / Services

| Method | Description |
|--------|-------------|
| `get_items()` | List all items/services |
| `create_items(items)` | Create items (wrap in `{Items: [...]}` automatically) |
| `update_item(data)` | Update item |
| `get_item_groups()` | List item groups |
| `create_item_groups(groups)` | Create item groups |

### Purchase Invoices

| Method | Description |
|--------|-------------|
| `get_purchase_invoices(start, end)` | List purchase invoices |
| `get_purchase_invoice_details(id)` | Purchase invoice details |
| `create_purchase_invoice(data)` | Create purchase invoice |
| `delete_purchase_invoice(id)` | Delete purchase invoice |
| `create_purchase_order(data)` | Create purchase order |

### Sales Offers

| Method | Description |
|--------|-------------|
| `get_offers(start, end)` | List offers |
| `get_offer_details(id)` | Offer details |
| `create_offer(data)` | Create offer |
| `update_offer(data)` | Update offer |
| `set_offer_status(id, status)` | Change offer status |
| `create_invoice_from_offer(id)` | Convert offer to invoice |

### Inventory

| Method | Description |
|--------|-------------|
| `get_locations()` | List warehouses |
| `get_inventory_movements(start, end)` | List movements |
| `send_inventory_movements(data)` | Create movements |

### General Ledger

| Method | Description |
|--------|-------------|
| `get_gl_batches(start, end)` | List GL transactions |
| `get_gl_batch_details(id)` | GL transaction details |
| `create_gl_batch(data)` | Create GL transaction |

### Fixed Assets

| Method | Description |
|--------|-------------|
| `get_fixed_assets()` | List fixed assets |
| `get_fixed_asset_locations()` | Asset locations |
| `get_responsible_employees()` | Responsible employees |
| `create_fixed_assets(data)` | Create assets |

### Prices & Discounts

| Method | Description |
|--------|-------------|
| `get_prices()` | Price list |
| `get_price(item_code)` | Item price |
| `send_prices(data)` | Create/update prices |
| `get_discounts()` | Discount list |
| `send_discounts(data)` | Create/update discounts |

### Dictionaries / Configuration

| Method | Description |
|--------|-------------|
| `get_taxes()` | Tax rates (VAT) — TaxId needed for invoices and items |
| `get_departments()` | Departments list |
| `get_projects()` | Projects list |
| `get_cost_centers()` | Cost centers |
| `get_accounts()` | Chart of accounts |
| `get_banks()` | Banks / bank accounts |
| `get_units_of_measure()` | Units of measure |
| `get_financial_years()` | Financial years |
| `get_dimensions()` | Dimensions |
| `add_dimensions(data)` | Add dimensions |
| `add_dimension_values(data)` | Add dimension values |

### Reports

| Method | Description |
|--------|-------------|
| `get_customer_debts_report()` | Receivables / outstanding debts |
| `get_customer_payment_report()` | Customer payments |
| `get_profit_loss_statement(start, end)` | Profit & Loss |
| `get_balance_sheet(date)` | Balance sheet |

### Vendors (Suppliers)

| Method | Description |
|--------|-------------|
| `get_vendors(name, reg_no)` | List vendors |
| `create_vendor(name, ...)` | Create vendor |
| `update_vendor(id, **fields)` | Update vendor |
| `get_vendor_groups()` | Vendor groups |
| `create_vendor_group(code, name)` | Create vendor group |

### Recurring Invoices

| Method | Description |
|--------|-------------|
| `get_recurring_invoices()` | List recurring templates |
| `get_recurring_invoice_details(id)` | Template details |
| `create_recurring_invoice(data)` | Create recurring template |

## Error Handling

```python
from merit_activa import (
    MeritClient, MeritApiError, MeritAuthError,
    MeritValidationError, MeritNotFoundError,
)

client = MeritClient(api_id="...", api_key="...")

try:
    invoice = client.create_simple_invoice(...)
except MeritAuthError:
    print("Bad API credentials — check API ID and API Key")
except MeritValidationError as e:
    print(f"Invalid data: {e}")
except MeritNotFoundError:
    print("Resource not found")
except MeritApiError as e:
    print(f"API error {e.status_code}: {e}")
```

## Logging

Enable debug logging to see all API requests and responses:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
# All API calls are logged to the "merit_activa" logger
```

## Merit Aktiva Setup Checklist

Before using this library, configure these in Merit Aktiva UI:

1. **Generate API keys**: Ustawienia → Główne ustawienia → API
2. **Create departments** (optional): Ustawienia → Dodatkowe parametry → Działy
3. **Add bank account for payments** (optional): Ustawienia → Konta bankowe → e.g. "PayU"
4. **Configure KSeF** (Poland): Ustawienia → KSeF → token/certyfikat

Service items can be created via API using `create_items()`.

## Official API Documentation

- **Reference Manual**: https://api.merit.ee/connecting-robots/reference-manual/
- **Merit Aktiva API overview**: https://api.merit.ee/merit-aktiva-api/
- **Polish base URL**: `https://program.360ksiegowosc.pl/api`
- **KSeF info (Poland)**: https://www.360ksiegowosc.pl/ksef/

## Author

**Marek Zacharewicz**
[Infortel Sp. z o.o.](https://infortel.pl)
Email: marek@infortel.pl
GitHub: [@zacharm-ewsoft](https://github.com/zacharm-ewsoft)

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Here's how:

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/new-endpoint`)
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Run tests: `pytest`
5. Submit a pull request

## Changelog

### 2.0.0 (2026-04-03)
- Complete rewrite as pip-installable library
- Full API coverage (60+ endpoints)
- HMAC-SHA256 request signing (verified against live API)
- Payment registration: `register_payu_payment()`, `invoice_and_pay()`
- Convenience methods: `find_or_create_customer()`, `create_simple_invoice()`, `invoice_full_flow()`
- Service item creation via `create_items()` with correct `{Items: [...]}` format
- Invoice email delivery (`send_invoice_by_email()`) and PDF download (`get_invoice_pdf()`)
- Department support for multi-project revenue tracking
- KSeF number support (Poland's mandatory e-invoicing)
- Auto-segmentation for long period queries (90-day API limit)
- Type hints, comprehensive docstrings, and error hierarchy
- 10 unit tests with full mock coverage

### 1.0.0 (2024-01-10)
- Initial release — tkinter GUI for data retrieval only
