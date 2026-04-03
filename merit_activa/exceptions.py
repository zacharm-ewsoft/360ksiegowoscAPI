# -*- coding: utf-8 -*-
"""Exceptions for Merit Aktiva API client."""


class MeritApiError(Exception):
    """Base exception for all Merit API errors."""

    def __init__(self, message: str, status_code: int | None = None, response=None):
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class MeritAuthError(MeritApiError):
    """Authentication failed — invalid API ID or API Key."""


class MeritNotFoundError(MeritApiError):
    """Requested resource not found (e.g. invoice, customer)."""


class MeritValidationError(MeritApiError):
    """Request payload validation failed on Merit side."""
