# -*- coding: utf-8 -*-
"""Tests for MeritClient."""

import json
import pytest
import responses

from merit_activa import MeritClient, MeritAuthError, MeritValidationError, MeritApiError


BASE_URL = "https://program.360ksiegowosc.pl/api"


@pytest.fixture
def client():
    return MeritClient(api_id="test_id", api_key="test_key")


@responses.activate
def test_get_taxes(client):
    taxes = [{"Id": "abc-123", "Code": "VAT23", "Name": "VAT 23%"}]
    responses.add(
        responses.POST,
        url=f"{BASE_URL}/v1/gettaxes",
        json=taxes,
        status=200,
    )
    result = client.get_taxes()
    assert result == taxes
    assert result[0]["Code"] == "VAT23"


@responses.activate
def test_get_departments(client):
    departments = [
        {"Code": "NIS2PILOT", "Name": "NIS2Pilot", "NonActive": False},
        {"Code": "CLIPFORGE", "Name": "ClipForge", "NonActive": False},
    ]
    responses.add(
        responses.POST,
        url=f"{BASE_URL}/v1/getdepartments",
        json=departments,
        status=200,
        match_querystring=False,
    )
    result = client.get_departments()
    assert len(result) == 2
    assert result[0]["Code"] == "NIS2PILOT"


@responses.activate
def test_create_customer(client):
    response_data = {"Id": "cust-123", "Name": "Firma Test"}
    responses.add(
        responses.POST,
        url=f"{BASE_URL}/v2/sendcustomer",
        json=response_data,
        status=200,
        match_querystring=False,
    )
    result = client.create_customer(
        name="Firma Test",
        reg_no="1234567890",
        email="test@firma.pl",
    )
    assert result["Id"] == "cust-123"

    # Verify payload
    body = json.loads(responses.calls[0].request.body)
    assert body["Name"] == "Firma Test"
    assert body["RegNo"] == "1234567890"
    assert body["Email"] == "test@firma.pl"
    assert body["NotTDCustomer"] is False
    assert body["CountryCode"] == "PL"


@responses.activate
def test_create_simple_invoice(client):
    # Mock get_taxes
    responses.add(
        responses.POST,
        url=f"{BASE_URL}/v1/gettaxes",
        json=[{"Id": "tax-23", "Code": "23%", "Name": "Stawka VAT 23%", "TaxPct": 23.0}],
        status=200,
        match_querystring=False,
    )
    # Mock get_customers (not found → will create)
    responses.add(
        responses.POST,
        url=f"{BASE_URL}/v1/getcustomers",
        json=[],
        status=200,
        match_querystring=False,
    )
    # Mock create customer
    responses.add(
        responses.POST,
        url=f"{BASE_URL}/v2/sendcustomer",
        json={"Id": "cust-new", "Name": "Test"},
        status=200,
        match_querystring=False,
    )
    # Mock getinvoices (for _next_invoice_number)
    responses.add(
        responses.POST,
        url=f"{BASE_URL}/v1/getinvoices",
        json=[],
        status=200,
        match_querystring=False,
    )
    # Mock create invoice
    responses.add(
        responses.POST,
        url=f"{BASE_URL}/v2/sendinvoice",
        json={"InvoiceId": "inv-123", "InvoiceNo": "FV/2026/001"},
        status=200,
        match_querystring=False,
    )

    result = client.create_simple_invoice(
        customer_name="Test Sp. z o.o.",
        customer_nip="9999999999",
        description="Test service",
        net_amount=100.00,
        department_code="TEST",
    )

    assert result["InvoiceId"] == "inv-123"
    assert result["InvoiceNo"] == "FV/2026/001"


@responses.activate
def test_auth_error(client):
    responses.add(
        responses.POST,
        url=f"{BASE_URL}/v1/gettaxes",
        status=401,
        match_querystring=False,
    )
    with pytest.raises(MeritAuthError):
        client.get_taxes()


@responses.activate
def test_validation_error(client):
    responses.add(
        responses.POST,
        url=f"{BASE_URL}/v2/sendinvoice",
        body="Invalid InvoiceNo",
        status=400,
        match_querystring=False,
    )
    with pytest.raises(MeritValidationError):
        client.create_invoice(
            customer={"Name": "X"},
            invoice_rows=[],
            tax_amount=[],
            total_amount=0,
        )


@responses.activate
def test_get_invoices_with_department_filter(client):
    invoices = [
        {"InvoiceNo": "1", "DepartmentCode": "NIS2PILOT", "TotalAmount": 799},
        {"InvoiceNo": "2", "DepartmentCode": "CLIPFORGE", "TotalAmount": 499},
        {"InvoiceNo": "3", "DepartmentCode": "NIS2PILOT", "TotalAmount": 299},
    ]
    responses.add(
        responses.POST,
        url=f"{BASE_URL}/v1/getinvoices",
        json=invoices,
        status=200,
        match_querystring=False,
    )
    result = client.get_invoices(
        period_start="20260401",
        period_end="20260430",
        department_code="NIS2PILOT",
    )
    assert len(result) == 2
    assert all(inv["DepartmentCode"] == "NIS2PILOT" for inv in result)


@responses.activate
def test_send_invoice_by_email(client):
    responses.add(
        responses.POST,
        url=f"{BASE_URL}/v2/sendinvoicebyemail",
        body='"OK"',
        status=200,
        content_type="application/json",
        match_querystring=False,
    )
    result = client.send_invoice_by_email("inv-123")
    assert result == "OK"


def test_country_urls():
    pl = MeritClient("id", "key", country="pl")
    assert "360ksiegowosc.pl" in pl.base_url

    ee = MeritClient("id", "key", country="ee")
    assert "merit.ee" in ee.base_url

    fi = MeritClient("id", "key", country="fi")
    assert "merit.fi" in fi.base_url


def test_custom_base_url():
    client = MeritClient("id", "key", base_url="https://custom.example.com/api")
    assert client.base_url == "https://custom.example.com/api"
