# merit-activa-api

**Python client library for [Merit Aktiva](https://www.merit.ee/) / [360 Księgowość](https://www.360ksiegowosc.pl/) API.**

Create invoices, manage customers, handle payments, integrate with KSeF — all from Python.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/merit-activa-api.svg)](https://pypi.org/project/merit-activa-api/)

---

## Features

- **Full API coverage** — sales invoices, purchase invoices, customers, vendors, payments, items, GL transactions, fixed assets, reports, and more
- **Invoice email delivery** — send invoice PDFs directly from Merit to customers
- **PDF download** — get invoice PDFs as base64
- **Department support** — assign invoices to departments (per project/platform)
- **KSeF ready** — pass KSeF numbers to invoices (Poland)
- **Long period queries** — auto-segments requests into 90-day chunks
- **Convenience methods** — `find_or_create_customer()`, `create_simple_invoice()`, `invoice_full_flow()`
- **Multi-country** — Poland (360 Księgowość), Estonia, Finland
- **Type hints** — full typing for IDE support
- **Zero dependencies** — only `requests`

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

### 2. Initialize client

```python
from merit_activa import MeritClient

client = MeritClient(
    api_id="your_api_id",
    api_key="your_api_key",
    # country="pl"  ← default (Poland)
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
    description="Usługa konsultingowa - kwiecień 2026",
    net_amount=799.00,
    vat_rate=23,
    department_code="MYPROJECT",
)
print(result)  # {"InvoiceId": "...", "InvoiceNo": "FV/2026/001"}
```

### 5. Send invoice by email

```python
client.send_invoice_by_email(result["InvoiceId"])
# Merit sends PDF to customer's email automatically
```

### 6. Full flow (one call)

```python
result = client.invoice_full_flow(
    customer_name="Szpital Miejski",
    customer_nip="6761013717",
    customer_email="faktury@szpital.pl",
    description="Subskrypcja Professional - maj 2026",
    net_amount=799.00,
    department_code="NIS2PILOT",
    send_email=True,
)
# Creates customer (if needed) → creates invoice → sends email
print(result)
# {"customer_id": "...", "invoice_id": "...", "invoice_no": "...", "email_sent": True}
```

## Departments (Działy)

Departments let you track revenue per project/platform:

```python
# List existing departments
departments = client.get_departments()

# Use in invoices
client.create_simple_invoice(
    ...,
    department_code="NIS2PILOT",  # Must exist in Merit
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

## KSeF Integration (Poland)

360 Księgowość has **built-in KSeF integration** (since Feb 2026). When you create an invoice via API, Merit automatically sends it to KSeF (if configured in settings).

```python
# Create invoice — Merit handles KSeF submission automatically
invoice = client.create_simple_invoice(
    customer_name="Firma ABC",
    customer_nip="1234567890",
    description="Usługa NIS2",
    net_amount=299.00,
)

# After KSeF processes it, you can read the KSeF number:
details = client.get_invoice_details(invoice["InvoiceId"])
ksef_number = details.get("KsefNumber")  # e.g. "1234567890-20260403-A1B2C3-..."

# You can also pass KSeF number when creating invoices:
client.create_simple_invoice(
    ...,
    ksef_number="1234567890-20260403-A1B2C3-D4E5F6-AB",
)
```

## Django Integration

```python
# settings.py
MERIT_API_ID = os.environ["MERIT_API_ID"]
MERIT_API_KEY = os.environ["MERIT_API_KEY"]
MERIT_DEPARTMENT = "NIS2PILOT"  # per project

# apps/billing/services.py
from django.conf import settings
from merit_activa import MeritClient

def get_merit_client():
    return MeritClient(
        api_id=settings.MERIT_API_ID,
        api_key=settings.MERIT_API_KEY,
    )
```

See [examples/django_integration.py](examples/django_integration.py) for full example with Celery tasks.

## API Reference

### Client Initialization

```python
MeritClient(api_id, api_key, country="pl", base_url=None, timeout=30)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_id` | str | required | API identifier from Merit settings |
| `api_key` | str | required | API secret key |
| `country` | str | `"pl"` | Country: `"pl"`, `"ee"`, `"fi"` |
| `base_url` | str | None | Override base URL |
| `timeout` | int | 30 | Request timeout (seconds) |

### Customers

| Method | Description |
|--------|-------------|
| `get_customers(name, reg_no, ...)` | List customers with filters |
| `create_customer(name, reg_no, email, ...)` | Create new customer (v2) |
| `update_customer(customer_id, **fields)` | Update customer fields |
| `find_or_create_customer(name, reg_no, ...)` | Find by NIP or create |
| `get_customer_groups()` | List customer groups |
| `create_customer_group(code, name)` | Create customer group |

### Sales Invoices

| Method | Description |
|--------|-------------|
| `get_invoices(start, end, unpaid, department)` | List invoices (max 3 months) |
| `get_invoices_period(start, end, ...)` | List invoices (auto-segments) |
| `get_invoice_details(invoice_id)` | Full invoice details |
| `create_invoice(customer, rows, tax, ...)` | Create invoice (v2) |
| `create_simple_invoice(name, nip, desc, amount, ...)` | One-line invoice (convenience) |
| `invoice_full_flow(name, nip, email, ...)` | Customer + invoice + email |
| `delete_invoice(invoice_id)` | Delete invoice |
| `create_credit_invoice(data)` | Create credit note |
| `send_invoice_by_email(invoice_id)` | Email invoice to customer |
| `get_invoice_pdf(invoice_id)` | Download PDF (base64) |

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

### Payments

| Method | Description |
|--------|-------------|
| `get_payments(start, end)` | List payments |
| `get_payment_types()` | Payment types |
| `send_payment(data)` | Register sales payment |
| `send_purchase_payment(data)` | Register purchase payment |
| `delete_payment(id)` | Delete payment |
| `send_bank_statement(data)` | Import bank statement |
| `send_prepayment(data)` | Register prepayment |

### Items / Products

| Method | Description |
|--------|-------------|
| `get_items()` | List items |
| `get_item_groups()` | List item groups |
| `create_items(items)` | Create items |
| `update_item(data)` | Update item |
| `create_item_groups(groups)` | Create item groups |

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
| `get_taxes()` | Tax rates (VAT) — needed for invoices |
| `get_departments()` | Departments list |
| `get_projects()` | Projects list |
| `get_cost_centers()` | Cost centers |
| `get_accounts()` | Chart of accounts |
| `get_banks()` | Banks list |
| `get_units_of_measure()` | Units of measure |
| `get_financial_years()` | Financial years |
| `get_dimensions()` | Dimensions |
| `add_dimensions(data)` | Add dimensions |
| `add_dimension_values(data)` | Add dimension values |

### Reports

| Method | Description |
|--------|-------------|
| `get_customer_debts_report()` | Receivables |
| `get_customer_payment_report()` | Customer payments |
| `get_profit_loss_statement(start, end)` | P&L |
| `get_balance_sheet(date)` | Balance sheet |

### Vendors

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
| `get_recurring_invoices()` | List templates |
| `get_recurring_invoice_details(id)` | Template details |
| `create_recurring_invoice(data)` | Create template |

## Error Handling

```python
from merit_activa import MeritClient, MeritApiError, MeritAuthError

client = MeritClient(api_id="...", api_key="...")

try:
    invoice = client.create_simple_invoice(...)
except MeritAuthError:
    print("Bad API credentials")
except MeritValidationError as e:
    print(f"Invalid data: {e}")
except MeritNotFoundError:
    print("Resource not found")
except MeritApiError as e:
    print(f"API error {e.status_code}: {e}")
```

## Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
# Now all API requests are logged to merit_activa logger
```

## Official API Documentation

- **Reference Manual**: https://api.merit.ee/connecting-robots/reference-manual/
- **Merit Aktiva API**: https://api.merit.ee/merit-aktiva-api/
- **Polish base URL**: `https://program.360ksiegowosc.pl/api`
- **KSeF info**: https://www.360ksiegowosc.pl/ksef/

## Author

**Marek Zacharewicz**
[Infortel Sp. z o.o.](https://infortel.pl)
Email: marek@infortel.pl

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE) for details.

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/new-endpoint`)
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Run tests: `pytest`
5. Submit a pull request

## Changelog

### 2.0.0 (2026-04-03)
- Complete rewrite as pip-installable library
- Full API coverage (60+ endpoints)
- Convenience methods: `find_or_create_customer()`, `create_simple_invoice()`, `invoice_full_flow()`
- Invoice email delivery and PDF download
- Department support for multi-project setups
- KSeF number support (Poland)
- Auto-segmentation for long period queries
- Type hints and comprehensive documentation

### 1.0.0 (2024-01-10)
- Initial release — tkinter GUI for data retrieval
