# -*- coding: utf-8 -*-
"""
Merit Aktiva / 360 Księgowość API Client Library.

Author: Marek Zacharewicz <marek@infortel.pl>
Company: Infortel Sp. z o.o. (https://infortel.pl)
License: GNU GPL v3.0

Usage:
    from merit_activa import MeritClient

    client = MeritClient(api_id="your_id", api_key="your_key")
    departments = client.get_departments()
    customers = client.get_customers()
"""

from merit_activa.client import MeritClient
from merit_activa.exceptions import (
    MeritApiError,
    MeritAuthError,
    MeritNotFoundError,
    MeritValidationError,
)

__version__ = "2.1.0"
__author__ = "Marek Zacharewicz"
__email__ = "marek@infortel.pl"
__license__ = "GPL-3.0-or-later"

__all__ = [
    "MeritClient",
    "MeritApiError",
    "MeritAuthError",
    "MeritNotFoundError",
    "MeritValidationError",
]
