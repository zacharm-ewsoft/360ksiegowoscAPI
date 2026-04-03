# -*- coding: utf-8 -*-
"""
Merit Aktiva / 360 Księgowość API Client.

Full API documentation: https://api.merit.ee/connecting-robots/reference-manual/
Polish base URL: https://program.360ksiegowosc.pl/api

Author: Marek Zacharewicz <marek@infortel.pl>
License: GNU GPL v3.0
"""

from __future__ import annotations

import hashlib
import base64
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import requests

from merit_activa.exceptions import (
    MeritApiError,
    MeritAuthError,
    MeritNotFoundError,
    MeritValidationError,
)

logger = logging.getLogger("merit_activa")

# Country-specific base URLs
BASE_URLS = {
    "pl": "https://program.360ksiegowosc.pl/api",
    "ee": "https://aktiva.merit.ee/api",
    "fi": "https://program.merit.fi/api",
}


class MeritClient:
    """Client for Merit Aktiva / 360 Księgowość REST API.

    Args:
        api_id: API identifier from Merit settings.
        api_key: API secret key from Merit settings.
        country: Country code — "pl" (Poland), "ee" (Estonia), "fi" (Finland).
        base_url: Override base URL (takes precedence over country).
        timeout: Request timeout in seconds (default: 30).

    Example:
        >>> from merit_activa import MeritClient
        >>> client = MeritClient(api_id="abc123", api_key="secret456")
        >>> taxes = client.get_taxes()
        >>> departments = client.get_departments()
    """

    def __init__(
        self,
        api_id: str,
        api_key: str,
        country: str = "pl",
        base_url: str | None = None,
        timeout: int = 30,
    ):
        self.api_id = api_id
        self.api_key = api_key
        self.base_url = (base_url or BASE_URLS.get(country, BASE_URLS["pl"])).rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    # ──────────────────────────────────────────────
    # Auth & request signing
    # ──────────────────────────────────────────────

    def _sign(self, timestamp: str, json_payload: str) -> str:
        """Generate HMAC-SHA256 signature for API request."""
        import hmac as _hmac

        signable = f"{self.api_id}{timestamp}{json_payload}".encode()
        raw_signature = _hmac.new(
            self.api_key.encode(), signable, hashlib.sha256
        ).digest()
        return base64.b64encode(raw_signature).decode()

    def _request(
        self,
        endpoint: str,
        payload: dict | None = None,
        version: str = "v1",
        params: dict | None = None,
    ) -> Any:
        """Execute signed API request.

        Args:
            endpoint: API endpoint name (e.g. "getinvoices").
            payload: Request body (will be JSON-serialized).
            version: API version — "v1" or "v2".
            params: Extra URL query parameters.

        Returns:
            Parsed JSON response.

        Raises:
            MeritAuthError: Invalid credentials.
            MeritNotFoundError: Resource not found.
            MeritValidationError: Payload validation failed.
            MeritApiError: Other API errors.
        """
        if payload is None:
            payload = {}

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        json_payload = json.dumps(payload, default=self._json_serializer)
        signature = self._sign(timestamp, json_payload)

        url = (
            f"{self.base_url}/{version}/{endpoint}"
            f"?ApiId={self.api_id}&timestamp={timestamp}&signature={signature}"
        )

        if params:
            for key, value in params.items():
                url += f"&{key}={value}"

        logger.debug("POST %s payload=%s", url, json_payload)

        try:
            response = self._session.post(url, data=json_payload, timeout=self.timeout)
        except requests.RequestException as e:
            raise MeritApiError(f"Connection error: {e}") from e

        if response.status_code == 401:
            raise MeritAuthError(
                "Authentication failed — check API ID and API Key",
                status_code=401,
                response=response,
            )

        if response.status_code == 404:
            raise MeritNotFoundError(
                f"Resource not found: {endpoint}",
                status_code=404,
                response=response,
            )

        if response.status_code == 400:
            raise MeritValidationError(
                f"Validation error: {response.text}",
                status_code=400,
                response=response,
            )

        if response.status_code != 200:
            raise MeritApiError(
                f"API error {response.status_code}: {response.text}",
                status_code=response.status_code,
                response=response,
            )

        # Some endpoints return plain text (e.g. "OK")
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return response.json()
        return response.text

    @staticmethod
    def _json_serializer(obj):
        """Handle Decimal and datetime serialization."""
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (datetime,)):
            return obj.strftime("%Y%m%d")
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    # ──────────────────────────────────────────────
    # Dictionaries / Configuration
    # ──────────────────────────────────────────────

    def get_taxes(self) -> list[dict]:
        """Get list of tax rates (VAT).

        Returns:
            List of dicts with keys: Id (GUID), Code, Name.
            Use TaxId when creating invoices.

        Example:
            >>> taxes = client.get_taxes()
            >>> vat23 = next(t for t in taxes if "23" in t["Code"])
            >>> tax_id = vat23["Id"]
        """
        return self._request("gettaxes")

    def get_departments(self) -> list[dict]:
        """Get list of departments.

        Returns:
            List of dicts: Code (Str 20), Name (Str 64), NonActive (bool).

        Note:
            Departments must be created manually in Merit UI:
            Menu → Ustawienia → Dodatkowe parametry → Działy
        """
        return self._request("getdepartments")

    def get_projects(self) -> list[dict]:
        """Get list of projects."""
        return self._request("projectlist")

    def get_cost_centers(self) -> list[dict]:
        """Get list of cost centers."""
        return self._request("costcenterslist")

    def get_accounts(self) -> list[dict]:
        """Get chart of accounts."""
        return self._request("accountslist")

    def get_banks(self) -> list[dict]:
        """Get list of banks."""
        return self._request("bankslist")

    def get_units_of_measure(self) -> list[dict]:
        """Get list of units of measure."""
        return self._request("unitsofmeasurelist")

    def get_financial_years(self) -> list[dict]:
        """Get list of financial years."""
        return self._request("getfinancialyears")

    def get_dimensions(self) -> list[dict]:
        """Get list of dimensions."""
        return self._request("getdimensionslist")

    def add_dimensions(self, dimensions: list[dict]) -> Any:
        """Add new dimensions.

        Args:
            dimensions: List of dimension objects.
        """
        return self._request("adddimensions", dimensions)

    def add_dimension_values(self, values: list[dict]) -> Any:
        """Add values to existing dimensions."""
        return self._request("adddimensionvalues", values)

    def send_tax(self, tax_data: dict) -> Any:
        """Create a new tax rate."""
        return self._request("sendtax", tax_data)

    def send_units_of_measure(self, units: list[dict]) -> Any:
        """Create new units of measure."""
        return self._request("sendunitsofmeasure", units)

    # ──────────────────────────────────────────────
    # Customers
    # ──────────────────────────────────────────────

    def get_customers(
        self,
        name: str | None = None,
        reg_no: str | None = None,
        customer_id: str | None = None,
        changed_date: str | None = None,
    ) -> list[dict]:
        """Get list of customers.

        Args:
            name: Filter by name (broad match).
            reg_no: Filter by NIP/RegNo (exact match).
            customer_id: Filter by GUID (exact match).
            changed_date: Filter by last change date (YYYYMMDD).

        Returns:
            List of customer objects.
        """
        payload = {}
        if name:
            payload["Name"] = name
        if reg_no:
            payload["RegNo"] = reg_no
        if customer_id:
            payload["Id"] = customer_id
        if changed_date:
            payload["ChangedDate"] = changed_date
        return self._request("getcustomers", payload)

    def create_customer(
        self,
        name: str,
        country_code: str = "PL",
        is_person: bool = False,
        reg_no: str | None = None,
        vat_reg_no: str | None = None,
        email: str | None = None,
        address: str | None = None,
        city: str | None = None,
        postal_code: str | None = None,
        phone: str | None = None,
        payment_deadline: int | None = None,
        contact: str | None = None,
        **extra,
    ) -> dict:
        """Create a new customer in Merit.

        Args:
            name: Customer name (unique, max 150 chars). **Required.**
            country_code: ISO country code (default: "PL"). **Required.**
            is_person: True for individuals, False for companies.
            reg_no: NIP / registration number.
            vat_reg_no: EU VAT number (e.g. "PL1234567890").
            email: Email address (used for invoice delivery).
            address: Street address.
            city: City name.
            postal_code: Postal code.
            phone: Phone number.
            payment_deadline: Payment term in days.
            contact: Contact person name.
            **extra: Additional fields (see API docs).

        Returns:
            Dict with Id (GUID) and Name of created customer.

        Example:
            >>> result = client.create_customer(
            ...     name="Firma ABC Sp. z o.o.",
            ...     reg_no="1234567890",
            ...     email="faktury@firma.pl",
            ...     city="Warszawa",
            ...     postal_code="00-001",
            ...     address="ul. Przykładowa 1",
            ...     payment_deadline=14,
            ... )
            >>> customer_id = result["Id"]
        """
        payload: dict[str, Any] = {
            "Name": name,
            "NotTDCustomer": is_person,
            "CountryCode": country_code,
        }
        if reg_no:
            payload["RegNo"] = reg_no
        if vat_reg_no:
            payload["VatRegNo"] = vat_reg_no
        if email:
            payload["Email"] = email
        if address:
            payload["Address"] = address
        if city:
            payload["City"] = city
        if postal_code:
            payload["PostalCode"] = postal_code
        if phone:
            payload["PhoneNo"] = phone
        if payment_deadline is not None:
            payload["PaymentDeadLine"] = payment_deadline
        if contact:
            payload["Contact"] = contact
        payload.update(extra)
        return self._request("sendcustomer", payload, version="v2")

    def update_customer(self, customer_id: str, **fields) -> Any:
        """Update an existing customer.

        Args:
            customer_id: GUID of the customer.
            **fields: Fields to update (Name, Email, Address, etc.).

        Example:
            >>> client.update_customer(
            ...     customer_id="abc-123-def",
            ...     Email="nowy@email.pl",
            ...     PaymentDeadLine=30,
            ... )
        """
        fields["Id"] = customer_id
        return self._request("updatecustomer", fields)

    def get_customer_groups(self) -> list[dict]:
        """Get list of customer groups."""
        return self._request("getcustomergroups")

    def create_customer_group(self, code: str, name: str) -> Any:
        """Create a new customer group."""
        return self._request("sendcustomergroup", {"Code": code, "Name": name})

    # ──────────────────────────────────────────────
    # Vendors (suppliers)
    # ──────────────────────────────────────────────

    def get_vendors(
        self,
        name: str | None = None,
        reg_no: str | None = None,
    ) -> list[dict]:
        """Get list of vendors/suppliers."""
        payload = {}
        if name:
            payload["Name"] = name
        if reg_no:
            payload["RegNo"] = reg_no
        return self._request("getvendors", payload)

    def create_vendor(
        self,
        name: str,
        country_code: str = "PL",
        is_person: bool = False,
        reg_no: str | None = None,
        email: str | None = None,
        **extra,
    ) -> dict:
        """Create a new vendor/supplier."""
        payload: dict[str, Any] = {
            "Name": name,
            "NotTDCustomer": is_person,
            "CountryCode": country_code,
        }
        if reg_no:
            payload["RegNo"] = reg_no
        if email:
            payload["Email"] = email
        payload.update(extra)
        return self._request("sendvendor", payload, version="v2")

    def update_vendor(self, vendor_id: str, **fields) -> Any:
        """Update an existing vendor."""
        fields["Id"] = vendor_id
        return self._request("updatevendor", fields)

    def get_vendor_groups(self) -> list[dict]:
        """Get list of vendor groups."""
        return self._request("getvendorgroups")

    def create_vendor_group(self, code: str, name: str) -> Any:
        """Create a new vendor group."""
        return self._request("sendvendorgroup", {"Code": code, "Name": name})

    # ──────────────────────────────────────────────
    # Sales Invoices
    # ──────────────────────────────────────────────

    def get_invoices(
        self,
        period_start: str,
        period_end: str,
        unpaid: bool = False,
        department_code: str | None = None,
    ) -> list[dict]:
        """Get list of sales invoices.

        Args:
            period_start: Start date (YYYYMMDD format).
            period_end: End date (YYYYMMDD format). Max 3 months from start.
            unpaid: If True, return only unpaid invoices.
            department_code: Filter results by department (client-side filter).

        Returns:
            List of invoice objects.

        Note:
            Merit API limits period to 3 months. For longer periods,
            use ``get_invoices_period()`` which handles segmentation automatically.
        """
        payload: dict[str, Any] = {
            "PeriodStart": period_start,
            "PeriodEnd": period_end,
        }
        if unpaid:
            payload["UnPaid"] = True

        result = self._request("getinvoices", payload)

        if department_code and isinstance(result, list):
            result = [
                inv for inv in result if inv.get("DepartmentCode") == department_code
            ]
        return result

    def get_invoices_period(
        self,
        period_start: str,
        period_end: str,
        unpaid: bool = False,
        department_code: str | None = None,
    ) -> list[dict]:
        """Get invoices over a long period (auto-segments into 90-day chunks).

        Same parameters as ``get_invoices()`` but handles periods longer than 3 months.
        """
        all_invoices = []
        start = datetime.strptime(period_start, "%Y%m%d")
        end = datetime.strptime(period_end, "%Y%m%d")

        while start < end:
            chunk_end = min(start + timedelta(days=90), end)
            invoices = self.get_invoices(
                period_start=start.strftime("%Y%m%d"),
                period_end=chunk_end.strftime("%Y%m%d"),
                unpaid=unpaid,
                department_code=department_code,
            )
            if isinstance(invoices, list):
                all_invoices.extend(invoices)
            start = chunk_end

        return all_invoices

    def get_invoice_details(self, invoice_id: str) -> dict:
        """Get full details of a sales invoice.

        Args:
            invoice_id: SIHId (GUID) of the invoice.
        """
        return self._request("getinvoice", {}, params={"InvoiceId": invoice_id})

    def create_invoice(
        self,
        customer: dict,
        invoice_rows: list[dict],
        tax_amount: list[dict],
        total_amount: float | Decimal,
        invoice_no: str | None = None,
        doc_date: str | None = None,
        due_date: str | None = None,
        transaction_date: str | None = None,
        department_code: str | None = None,
        project_code: str | None = None,
        currency_code: str = "PLN",
        accounting_doc: int = 1,
        ksef_number: str | None = None,
        header_comment: str | None = None,
        footer_comment: str | None = None,
        **extra,
    ) -> dict:
        """Create a sales invoice.

        Args:
            customer: Customer object with Name, RegNo, etc.
                If customer doesn't exist in Merit, it will be auto-created.
            invoice_rows: List of row objects (Item, Quantity, Price, TaxId, etc.).
            tax_amount: List of tax amounts [{TaxId, Amount}, ...].
            total_amount: Total amount WITHOUT VAT.
            invoice_no: Invoice number (auto-generated if empty, max 35 chars).
            doc_date: Document date (YYYYMMDD, default: today).
            due_date: Due date (YYYYMMDD).
            transaction_date: Transaction/sale date (YYYYMMDD).
            department_code: Department code (must exist in Merit).
            project_code: Project code (must exist in Merit).
            currency_code: Currency (default: PLN).
            accounting_doc: Document type (1=invoice, 2=receipt, 3=paragon,
                5=credit, 6=prepayment invoice).
            ksef_number: KSeF reference number (Poland only, max 36 chars).
            header_comment: Header comment (max 4000 chars).
            footer_comment: Footer comment (max 4000 chars).
            **extra: Additional fields (see API docs).

        Returns:
            Dict with InvoiceId (GUID) and InvoiceNo.

        Example:
            >>> tax_id = "665f01a4-357a-4a6b-a565-2f17e6e1da13"  # VAT 23%
            >>> result = client.create_invoice(
            ...     customer={
            ...         "Name": "Firma ABC Sp. z o.o.",
            ...         "RegNo": "1234567890",
            ...         "NotTDCustomer": False,
            ...         "CountryCode": "PL",
            ...     },
            ...     invoice_rows=[{
            ...         "Item": {
            ...             "Code": "NIS2-PRO",
            ...             "Description": "NIS2Pilot Professional - subskrypcja miesięczna",
            ...             "Type": 2,  # 2 = service
            ...         },
            ...         "Quantity": 1,
            ...         "Price": 799.00,
            ...         "TaxId": tax_id,
            ...         "DepartmentCode": "NIS2PILOT",
            ...     }],
            ...     tax_amount=[{"TaxId": tax_id, "Amount": 183.77}],
            ...     total_amount=799.00,
            ...     department_code="NIS2PILOT",
            ...     due_date="20260417",
            ... )
            >>> invoice_id = result["InvoiceId"]
        """
        today = datetime.now().strftime("%Y%m%d")

        payload: dict[str, Any] = {
            "Customer": customer,
            "InvoiceRow": invoice_rows,
            "TaxAmount": tax_amount,
            "TotalAmount": float(total_amount) if isinstance(total_amount, Decimal) else total_amount,
            "CurrencyCode": currency_code,
            "AccountingDoc": accounting_doc,
            "DocDate": doc_date or today,
        }

        if invoice_no:
            payload["InvoiceNo"] = invoice_no
        if due_date:
            payload["DueDate"] = due_date
        if transaction_date:
            payload["TransactionDate"] = transaction_date
        if department_code:
            payload["DepartmentCode"] = department_code
        if project_code:
            payload["ProjectCode"] = project_code
        if ksef_number:
            payload["KsefNumber"] = ksef_number
        if header_comment:
            payload["Hcomment"] = header_comment
        if footer_comment:
            payload["Fcomment"] = footer_comment

        payload.update(extra)
        return self._request("sendinvoice", payload, version="v2")

    def delete_invoice(self, invoice_id: str) -> Any:
        """Delete a sales invoice.

        Args:
            invoice_id: SIHId (GUID) of the invoice.
        """
        return self._request("deleteinvoice", {"Id": invoice_id})

    def create_credit_invoice(self, credit_data: dict) -> dict:
        """Create a credit (corrective) invoice.

        Args:
            credit_data: Credit invoice payload (see API docs).
        """
        return self._request("sendcreditinvoice", credit_data)

    # ──────────────────────────────────────────────
    # Invoice delivery (email, PDF)
    # ──────────────────────────────────────────────

    def send_invoice_by_email(
        self, invoice_id: str, delivery_note: bool = False
    ) -> str:
        """Send invoice to customer via email.

        Merit sends the invoice PDF to the email address stored in customer record.

        Args:
            invoice_id: SIHId (GUID) of the invoice.
            delivery_note: If True, sends invoice without prices (as delivery note).

        Returns:
            "OK" on success, or error message from mail server.

        Example:
            >>> client.send_invoice_by_email("abc-123-def")
            'OK'
        """
        payload: dict[str, Any] = {"Id": invoice_id}
        if delivery_note:
            payload["DelivNote"] = True
        return self._request("sendinvoicebyemail", payload, version="v2")

    def get_invoice_pdf(self, invoice_id: str) -> dict:
        """Download invoice as PDF.

        Args:
            invoice_id: SIHId (GUID) of the invoice.

        Returns:
            Dict with FileName (str) and FileContent (base64-encoded PDF).

        Example:
            >>> pdf = client.get_invoice_pdf("abc-123-def")
            >>> import base64
            >>> with open(pdf["FileName"], "wb") as f:
            ...     f.write(base64.b64decode(pdf["FileContent"]))
        """
        return self._request("getsalesinvpdf", {"Id": invoice_id}, version="v2")

    # ──────────────────────────────────────────────
    # Sales Offers
    # ──────────────────────────────────────────────

    def get_offers(self, period_start: str, period_end: str) -> list[dict]:
        """Get list of sales offers."""
        return self._request("getoffers", {
            "PeriodStart": period_start,
            "PeriodEnd": period_end,
        })

    def get_offer_details(self, offer_id: str) -> dict:
        """Get details of a sales offer."""
        return self._request("getofferdetails", {}, params={"OfferId": offer_id})

    def create_offer(self, offer_data: dict) -> dict:
        """Create a new sales offer."""
        return self._request("sendsalesoffer", offer_data)

    def update_offer(self, offer_data: dict) -> Any:
        """Update an existing sales offer."""
        return self._request("updatesalesoffer", offer_data)

    def set_offer_status(self, offer_id: str, status: int) -> Any:
        """Change status of a sales offer."""
        return self._request("setofferstatus", {"Id": offer_id, "Status": status})

    def create_invoice_from_offer(self, offer_id: str) -> dict:
        """Create an invoice from an existing offer."""
        return self._request("createinvoicefromoffer", {"Id": offer_id})

    # ──────────────────────────────────────────────
    # Purchase Invoices
    # ──────────────────────────────────────────────

    def get_purchase_invoices(
        self, period_start: str, period_end: str, unpaid: bool = False
    ) -> list[dict]:
        """Get list of purchase invoices."""
        payload: dict[str, Any] = {
            "PeriodStart": period_start,
            "PeriodEnd": period_end,
        }
        if unpaid:
            payload["UnPaid"] = True
        return self._request("getpurchorders", payload)

    def get_purchase_invoice_details(self, invoice_id: str) -> dict:
        """Get details of a purchase invoice."""
        return self._request(
            "getpurchorder", {}, params={"PurchaseOrderId": invoice_id}
        )

    def create_purchase_invoice(self, invoice_data: dict) -> dict:
        """Create a purchase invoice.

        Args:
            invoice_data: Invoice payload with vendor, rows, taxes, etc.
                Supports DepartmentCode and KsefNumber fields.
        """
        return self._request("sendpurchinvoice", invoice_data, version="v2")

    def delete_purchase_invoice(self, invoice_id: str) -> Any:
        """Delete a purchase invoice."""
        return self._request("deletepurchinvoice", {"Id": invoice_id})

    def create_purchase_order(self, order_data: dict) -> dict:
        """Create a purchase order (waiting for approval)."""
        return self._request("sendpurchorder", order_data, version="v2")

    # ──────────────────────────────────────────────
    # Recurring Invoices
    # ──────────────────────────────────────────────

    def get_recurring_invoices(self) -> list[dict]:
        """Get list of recurring invoices."""
        return self._request("getrecurringinvoices")

    def get_recurring_invoice_details(self, invoice_id: str) -> dict:
        """Get details of a recurring invoice."""
        return self._request(
            "getrecurringinvoicedetails", {}, params={"Id": invoice_id}
        )

    def create_recurring_invoice(self, invoice_data: dict) -> dict:
        """Create a recurring invoice template."""
        return self._request("createrecurringinvoice", invoice_data)

    # ──────────────────────────────────────────────
    # Payments
    # ──────────────────────────────────────────────

    def get_payments(self, period_start: str, period_end: str) -> list[dict]:
        """Get list of payments."""
        return self._request("getpayments", {
            "PeriodStart": period_start,
            "PeriodEnd": period_end,
        })

    def get_payment_types(self) -> list[dict]:
        """Get available payment types."""
        return self._request("getpaymenttypes")

    def send_payment(self, payment_data: dict) -> Any:
        """Register payment for a sales invoice.

        Args:
            payment_data: Payment payload (InvoiceId, Amount, PaymentDate, etc.).
        """
        return self._request("sendpayment", payment_data)

    def send_purchase_payment(self, payment_data: dict) -> Any:
        """Register payment for a purchase invoice."""
        return self._request("sendpurchpayment", payment_data)

    def delete_payment(self, payment_id: str) -> Any:
        """Delete a payment."""
        return self._request("deletepayment", {"Id": payment_id})

    def send_bank_statement(self, statement_data: dict) -> Any:
        """Import bank statement."""
        return self._request("sendbankstatement", statement_data)

    def send_prepayment(self, prepayment_data: dict) -> Any:
        """Register a prepayment."""
        return self._request("sendprepayments", prepayment_data)

    # ──────────────────────────────────────────────
    # Items / Products
    # ──────────────────────────────────────────────

    def get_items(self) -> list[dict]:
        """Get list of items/products."""
        return self._request("itemslist")

    def get_item_groups(self) -> list[dict]:
        """Get list of item groups."""
        return self._request("getitemgroups")

    def create_items(self, items: list[dict]) -> Any:
        """Create new items/products."""
        return self._request("senditems", items)

    def update_item(self, item_data: dict) -> Any:
        """Update an existing item."""
        return self._request("updateitem", item_data)

    def create_item_groups(self, groups: list[dict]) -> Any:
        """Create new item groups."""
        return self._request("senditemgroups", groups)

    # ──────────────────────────────────────────────
    # Inventory / Stock
    # ──────────────────────────────────────────────

    def get_locations(self) -> list[dict]:
        """Get list of warehouse locations."""
        return self._request("getlocations")

    def get_inventory_movements(
        self, period_start: str, period_end: str
    ) -> list[dict]:
        """Get list of inventory movements."""
        return self._request("getinventorymovements", {
            "PeriodStart": period_start,
            "PeriodEnd": period_end,
        })

    def send_inventory_movements(self, movements: list[dict]) -> Any:
        """Create inventory movements."""
        return self._request("sendinventorymovements", movements)

    # ──────────────────────────────────────────────
    # General Ledger / Accounting
    # ──────────────────────────────────────────────

    def get_gl_batches(self, period_start: str, period_end: str) -> list[dict]:
        """Get list of general ledger transactions."""
        return self._request("getglbatches", {
            "PeriodStart": period_start,
            "PeriodEnd": period_end,
        })

    def get_gl_batch_details(self, batch_id: str) -> dict:
        """Get details of a GL transaction."""
        return self._request("getglbatchdetails", {}, params={"Id": batch_id})

    def create_gl_batch(self, batch_data: dict) -> Any:
        """Create a general ledger transaction."""
        return self._request("sendglbatch", batch_data)

    # ──────────────────────────────────────────────
    # Fixed Assets
    # ──────────────────────────────────────────────

    def get_fixed_assets(self) -> list[dict]:
        """Get list of fixed assets."""
        return self._request("getfixedassets")

    def get_fixed_asset_locations(self) -> list[dict]:
        """Get list of fixed asset locations."""
        return self._request("listfixedassetlocations")

    def get_responsible_employees(self) -> list[dict]:
        """Get list of employees responsible for assets."""
        return self._request("getresponsibleemployees")

    def create_fixed_assets(self, assets: list[dict]) -> Any:
        """Create new fixed assets."""
        return self._request("sendfixedassets", assets)

    # ──────────────────────────────────────────────
    # Prices & Discounts
    # ──────────────────────────────────────────────

    def get_prices(self) -> list[dict]:
        """Get price list."""
        return self._request("getprices")

    def get_price(self, item_code: str, customer_id: str | None = None) -> dict:
        """Get price for specific item."""
        payload: dict[str, Any] = {"ItemCode": item_code}
        if customer_id:
            payload["CustId"] = customer_id
        return self._request("getprice", payload)

    def send_prices(self, prices: list[dict]) -> Any:
        """Create/update prices."""
        return self._request("sendprices", prices)

    def get_discounts(self) -> list[dict]:
        """Get discount list."""
        return self._request("getdiscounts")

    def send_discounts(self, discounts: list[dict]) -> Any:
        """Create/update discounts."""
        return self._request("senddiscounts", discounts)

    # ──────────────────────────────────────────────
    # Reports
    # ──────────────────────────────────────────────

    def get_customer_debts_report(self) -> list[dict]:
        """Get customer debts (receivables) report."""
        return self._request("customerdebtsreport")

    def get_customer_payment_report(self) -> list[dict]:
        """Get customer payment report."""
        return self._request("customerpaymentreport")

    def get_profit_loss_statement(
        self, period_start: str, period_end: str
    ) -> dict:
        """Get statement of profit or loss."""
        return self._request("statementofprofitorloss", {
            "PeriodStart": period_start,
            "PeriodEnd": period_end,
        })

    def get_balance_sheet(self, date: str) -> dict:
        """Get statement of financial position (balance sheet)."""
        return self._request("statementoffinancialposition", {"Date": date})

    # ──────────────────────────────────────────────
    # Convenience / high-level methods
    # ──────────────────────────────────────────────

    def find_or_create_customer(
        self,
        name: str,
        reg_no: str,
        **kwargs,
    ) -> dict:
        """Find customer by NIP/RegNo, or create if not exists.

        Args:
            name: Customer name.
            reg_no: NIP / registration number.
            **kwargs: Extra fields for create_customer().

        Returns:
            Customer dict with at least Id and Name.

        Example:
            >>> customer = client.find_or_create_customer(
            ...     name="Urząd Miasta Krakowa",
            ...     reg_no="6761013717",
            ...     email="faktury@krakow.pl",
            ...     payment_deadline=14,
            ... )
        """
        existing = self.get_customers(reg_no=reg_no)
        if existing:
            return existing[0]

        return self.create_customer(name=name, reg_no=reg_no, **kwargs)

    def create_simple_invoice(
        self,
        customer_name: str,
        customer_nip: str,
        description: str,
        net_amount: float | Decimal,
        vat_rate: int = 23,
        department_code: str | None = None,
        due_date: str | None = None,
        invoice_no: str | None = None,
        ksef_number: str | None = None,
        payment_deadline: int = 14,
    ) -> dict:
        """Create a simple single-line invoice (convenience method).

        Handles customer lookup/creation, tax lookup, and invoice creation
        in a single call.

        Args:
            customer_name: Customer company name.
            customer_nip: Customer NIP number.
            description: Invoice line description.
            net_amount: Net amount (without VAT).
            vat_rate: VAT rate percentage (default: 23).
            department_code: Department code in Merit (e.g. "NIS2PILOT").
            due_date: Due date (YYYYMMDD). If not set, calculated from payment_deadline.
            invoice_no: Invoice number (auto-generated if empty).
            ksef_number: KSeF reference number.
            payment_deadline: Days until payment (default: 14).

        Returns:
            Dict with InvoiceId and InvoiceNo.

        Example:
            >>> result = client.create_simple_invoice(
            ...     customer_name="Firma ABC Sp. z o.o.",
            ...     customer_nip="1234567890",
            ...     description="NIS2Pilot Professional - subskrypcja kwiecień 2026",
            ...     net_amount=799.00,
            ...     department_code="NIS2PILOT",
            ... )
        """
        # 1. Find or create customer
        self.find_or_create_customer(
            name=customer_name,
            reg_no=customer_nip,
            payment_deadline=payment_deadline,
        )

        # 2. Find matching tax rate
        taxes = self.get_taxes()
        tax_id = None
        for tax in taxes:
            code = tax.get("Code", "")
            if str(vat_rate) in code:
                tax_id = tax["Id"]
                break
        if not tax_id:
            raise MeritValidationError(
                f"Tax rate {vat_rate}% not found in Merit. "
                f"Available: {[t.get('Code') for t in taxes]}"
            )

        # 3. Calculate amounts
        net = float(net_amount) if isinstance(net_amount, Decimal) else net_amount
        vat_amount = round(net * vat_rate / 100, 2)

        # 4. Calculate due date
        if not due_date:
            due = datetime.now() + timedelta(days=payment_deadline)
            due_date = due.strftime("%Y%m%d")

        # 5. Create invoice
        row: dict[str, Any] = {
            "Item": {
                "Code": "SVC",
                "Description": description,
                "Type": 2,  # service
            },
            "Quantity": 1,
            "Price": net,
            "TaxId": tax_id,
        }
        if department_code:
            row["DepartmentCode"] = department_code

        return self.create_invoice(
            customer={
                "Name": customer_name,
                "RegNo": customer_nip,
                "NotTDCustomer": False,
                "CountryCode": "PL",
            },
            invoice_rows=[row],
            tax_amount=[{"TaxId": tax_id, "Amount": vat_amount}],
            total_amount=net,
            department_code=department_code,
            due_date=due_date,
            invoice_no=invoice_no,
            ksef_number=ksef_number,
        )

    def invoice_full_flow(
        self,
        customer_name: str,
        customer_nip: str,
        customer_email: str,
        description: str,
        net_amount: float | Decimal,
        department_code: str | None = None,
        send_email: bool = True,
        **kwargs,
    ) -> dict:
        """Complete invoice flow: create customer → invoice → email.

        This is the highest-level method — does everything in one call.

        Args:
            customer_name: Company name.
            customer_nip: NIP number.
            customer_email: Email for invoice delivery.
            description: Invoice line description.
            net_amount: Net amount.
            department_code: Department code (e.g. "NIS2PILOT", "CLIPFORGE").
            send_email: If True, send invoice by email after creation.
            **kwargs: Extra args passed to create_simple_invoice().

        Returns:
            Dict with keys:
                - customer_id: GUID
                - invoice_id: GUID
                - invoice_no: str
                - email_sent: bool

        Example:
            >>> result = client.invoice_full_flow(
            ...     customer_name="Szpital Miejski w Krakowie",
            ...     customer_nip="6761013717",
            ...     customer_email="faktury@szpital.krakow.pl",
            ...     description="NIS2Pilot Starter - subskrypcja kwiecień 2026",
            ...     net_amount=299.00,
            ...     department_code="NIS2PILOT",
            ...     payment_deadline=14,
            ... )
            >>> print(result)
            {'customer_id': '...', 'invoice_id': '...', 'invoice_no': 'FV/2026/...', 'email_sent': True}
        """
        # 1. Ensure customer exists with correct email
        customer = self.find_or_create_customer(
            name=customer_name,
            reg_no=customer_nip,
            email=customer_email,
        )
        customer_id = customer.get("Id") or customer.get("id", "")

        # Update email if customer already existed
        if customer.get("Email") != customer_email and customer_id:
            try:
                self.update_customer(customer_id, Email=customer_email)
            except MeritApiError:
                logger.warning("Could not update customer email for %s", customer_nip)

        # 2. Create invoice
        invoice_result = self.create_simple_invoice(
            customer_name=customer_name,
            customer_nip=customer_nip,
            description=description,
            net_amount=net_amount,
            department_code=department_code,
            **kwargs,
        )

        invoice_id = invoice_result.get("InvoiceId", "")
        invoice_no = invoice_result.get("InvoiceNo", "")

        # 3. Send by email
        email_sent = False
        if send_email and invoice_id:
            try:
                result = self.send_invoice_by_email(invoice_id)
                email_sent = result == "OK" or "OK" in str(result)
            except MeritApiError as e:
                logger.warning("Could not send invoice email: %s", e)

        return {
            "customer_id": customer_id,
            "invoice_id": invoice_id,
            "invoice_no": invoice_no,
            "email_sent": email_sent,
        }
