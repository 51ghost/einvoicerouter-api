"""
E-Invoice Router API
====================
RapidAPI-ready FastAPI service for EU e-invoicing validation, conversion,
and country-specific rule lookup. Supports all 27 EU member states and
major e-invoicing syntaxes (UBL 2.1, CII, PEPPOL BIS, XRechnung, etc.).

Endpoints:
  GET  /v1/health                   — Health check
  POST /v1/validate                 — Validate an e-invoice
  POST /v1/convert                  — Convert between e-invoice formats
  GET  /v1/country/{code}           — Country-specific e-invoicing rules
  GET  /v1/countries                — List all countries
  GET  /v1/formats                  — List supported formats
  GET  /v1/samples/{format}         — Sample invoice for a format
  GET  /v1/check-vat/{country}/{vat}— Validate VAT format
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Header, Query, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from data_pipeline import (
    EU_COUNTRY_RULES, VALIDATION_RULES, SAMPLE_INVOICES, FORMAT_NAMES,
    get_country_rule, get_all_countries, get_validation_rules,
    get_all_formats, get_format_names, get_sample_invoice,
    get_all_sample_invoices, validate_vat_format,
    validate_invoice_structure, convert_invoice,
    convert_country_rule_to_dict, convert_validation_rule_to_dict,
    convert_sample_to_dict, listify_countries, get_pipeline_summary,
)

# ──────────────────────────────────────────────
# Logging & Config
# ──────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("einvoicerouter")

API_KEY = os.environ.get("EINVOICE_ROUTER_API_KEY", "dev-api-key-change-in-production")
RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT", "60"))

# ──────────────────────────────────────────────
# Request / Response Models
# ──────────────────────────────────────────────

class ValidateRequest(BaseModel):
    invoice: Dict[str, Any] = Field(..., description="Invoice JSON data to validate")
    format: str = Field(..., description="Invoice format (ubl, cii, peppol_bis, fattura_pa, xrechnung, facturae, zugferd)")
    country: Optional[str] = Field(None, description="ISO 3166-1 alpha-2 country code for country-specific validation")


class ValidateResponse(BaseModel):
    valid: bool
    format: str
    format_name: str
    results: List[Dict[str, Any]]
    summary: Dict[str, Any]
    country_check: Optional[Dict[str, Any]] = None


class ConvertRequest(BaseModel):
    invoice: Dict[str, Any] = Field(..., description="Source invoice data")
    source_format: str = Field(..., description="Source format")
    target_format: str = Field(..., description="Target format")


class ConvertResponse(BaseModel):
    status: str
    source_format: str
    target_format: str
    en16931_compliant: bool
    message: str
    mapping: Dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    uptime_seconds: float
    data_pipeline: Dict[str, Any]


class CountryRulesResponse(BaseModel):
    country_code: str
    country_name: str
    vat_format: str
    vat_example: str
    mandatory_since: Optional[str]
    threshold_above: Optional[float]
    preferred_formats: List[str]
    accepted_formats: List[str]
    requires_peppol_id: bool
    requires_qualified_electronic_signature: bool
    central_platform_url: Optional[str]
    additional_requirements: List[str]
    tax_authority_name: Optional[str]


# ──────────────────────────────────────────────
# Rate Limiter (in-memory)
# ──────────────────────────────────────────────

class InMemoryRateLimiter:
    def __init__(self, max_per_minute: int = 60):
        self.max_per_minute = max_per_minute
        self.requests: Dict[str, List[float]] = {}

    def check(self, key: str) -> bool:
        now = time.time()
        window_start = now - 60
        if key not in self.requests:
            self.requests[key] = []
        self.requests[key] = [t for t in self.requests[key] if t > window_start]
        if len(self.requests[key]) >= self.max_per_minute:
            return False
        self.requests[key].append(now)
        return True


rate_limiter = InMemoryRateLimiter(max_per_minute=RATE_LIMIT_PER_MINUTE)

# ──────────────────────────────────────────────
# App Startup
# ──────────────────────────────────────────────

_start_time: float = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — log startup."""
    global _start_time
    _start_time = time.time()
    logger.info(f"E-Invoice Router API starting — {len(EU_COUNTRY_RULES)} countries, {len(FORMAT_NAMES)} formats")
    yield
    logger.info("E-Invoice Router API shutting down")

app = FastAPI(
    title="E-Invoice Router API",
    description="EU e-invoicing validation, conversion, and country rule lookup. "
                "Supports all 27 EU member states and 7 invoice syntax formats "
                "(UBL 2.1, CII, PEPPOL BIS Billing 3.0, XRechnung, FatturaPA, Facturae, ZUGFeRD).",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ──────────────────────────────────────────────
# CORS
# ──────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# Auth Middleware (api-key via X-API-Key header)
# ──────────────────────────────────────────────


async def verify_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """Verify API key from header or query parameter."""
    api_key = x_api_key
    if api_key is None:
        raise HTTPException(
            status_code=401,
            detail="API key required. Provide via X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    if api_key != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key.",
        )
    return api_key


async def rate_limit_check(request: Request):
    """Check rate limit for the requesting IP."""
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.check(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Max %d requests per minute." % RATE_LIMIT_PER_MINUTE,
        )
    return True


# ──────────────────────────────────────────────
# ENDPOINTS
# ──────────────────────────────────────────────

@app.get("/v1/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint — returns system status and data pipeline summary."""
    global _start_time
    uptime = time.time() - _start_time
    return HealthResponse(
        status="ok",
        version="1.0.0",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        uptime_seconds=round(uptime, 2),
        data_pipeline=get_pipeline_summary(),
    )


@app.post("/v1/validate", response_model=ValidateResponse, tags=["Validation"])
async def validate_invoice(
    req: ValidateRequest,
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Validate an e-invoice against format-specific and country-specific rules.

    Accepts JSON invoice data and runs structural validation checks
    for the specified format. Optionally validates against the
    e-invoicing rules of a specific EU country.
    """
    await verify_api_key(x_api_key)
    await rate_limit_check(request)

    fmt = req.format.lower().strip()
    fmt_name = FORMAT_NAMES.get(fmt, fmt)
    invoice_data = req.invoice

    results = validate_invoice_structure(invoice_data, fmt)

    errors = sum(1 for r in results if not r.get("passed", False) and r.get("severity") == "error")
    warnings = sum(1 for r in results if not r.get("passed", False) and r.get("severity") == "warning")
    passed = sum(1 for r in results if r.get("passed", False))
    total = len(results)

    country_check = None
    if req.country:
        country_rule = get_country_rule(req.country)
        if country_rule:
            seller_vat = ""
            if "AccountingSupplierParty" in invoice_data:
                seller_vat = invoice_data["AccountingSupplierParty"].get("VATID", "")
            vat_valid = validate_vat_format(req.country, seller_vat) if seller_vat else None
            country_check = {
                "country_code": country_rule.country_code,
                "country_name": country_rule.country_name,
                "mandatory_since": country_rule.mandatory_since,
                "threshold_above": country_rule.threshold_above,
                "preferred_formats": country_rule.preferred_formats,
                "vat_check": {
                    "vat_number": seller_vat,
                    "format_valid": vat_valid,
                } if seller_vat else None,
                "compliant_with_country": errors == 0,
            }

    is_valid = errors == 0

    return ValidateResponse(
        valid=is_valid,
        format=fmt,
        format_name=fmt_name,
        results=results,
        summary={
            "total_rules": total,
            "passed": passed,
            "errors": errors,
            "warnings": warnings,
            "valid": is_valid,
        },
        country_check=country_check,
    )


@app.post("/v1/convert", tags=["Conversion"])
async def convert_invoice_endpoint(
    req: ConvertRequest,
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Convert an invoice between supported e-invoice formats.

    Uses EN 16931 semantic mapping as the intermediate model.
    Returns a conversion report with mapping details.
    """
    await verify_api_key(x_api_key)
    await rate_limit_check(request)

    result = convert_invoice(req.invoice, req.source_format.lower(), req.target_format.lower())

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@app.get("/v1/country/{code}", response_model=CountryRulesResponse, tags=["Countries"])
async def get_country_rules(
    code: str,
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Get e-invoicing rules for a specific EU country (ISO 3166-1 alpha-2 code).

    Returns VAT format, mandatory dates, accepted invoice formats,
    platform URLs, and additional compliance requirements.
    """
    await verify_api_key(x_api_key)
    await rate_limit_check(request)

    rule = get_country_rule(code.upper())
    if not rule:
        raise HTTPException(status_code=404, detail=f"Country '{code.upper()}' not found. Supported: {', '.join(EU_COUNTRIES.keys())}")

    return convert_country_rule_to_dict(rule)


@app.get("/v1/countries", tags=["Countries"])
async def list_countries(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    List all 27 EU countries with their e-invoicing rules.
    """
    await verify_api_key(x_api_key)
    await rate_limit_check(request)

    return {"countries": listify_countries(), "total": len(EU_COUNTRY_RULES)}


@app.get("/v1/formats", tags=["Formats"])
async def list_formats(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    List supported e-invoice formats and their validation rules.
    """
    await verify_api_key(x_api_key)
    await rate_limit_check(request)

    formats = {}
    for fmt_key, fmt_name in FORMAT_NAMES.items():
        rules = get_validation_rules(fmt_key)
        formats[fmt_key] = {
            "name": fmt_name,
            "rules_count": len(rules),
            "rules": [convert_validation_rule_to_dict(r) for r in rules],
        }

    return {"formats": formats, "total": len(FORMAT_NAMES)}


@app.get("/v1/samples/{format_name}", tags=["Samples"])
async def get_sample_invoice_endpoint(
    format_name: str,
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Get a sample invoice for a specific format.
    """
    await verify_api_key(x_api_key)
    await rate_limit_check(request)

    sample = get_sample_invoice(format_name.lower())
    if not sample:
        raise HTTPException(
            status_code=404,
            detail=f"No sample invoice for format '{format_name}'. Supported: {', '.join(get_format_names())}",
        )

    return convert_sample_to_dict(sample)


@app.get("/v1/samples", tags=["Samples"])
async def list_all_samples(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    List all sample invoices available across all formats.
    """
    await verify_api_key(x_api_key)
    await rate_limit_check(request)

    samples = [convert_sample_to_dict(s) for s in SAMPLE_INVOICES]
    return {"samples": samples, "total": len(samples)}


@app.get("/v1/check-vat/{country}/{vat}", tags=["Validation"])
async def check_vat(
    country: str,
    vat: str,
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Validate a VAT number format against a specific country's rules.
    """
    await verify_api_key(x_api_key)
    await rate_limit_check(request)

    country_upper = country.upper()
    rule = get_country_rule(country_upper)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Country '{country_upper}' not found.")

    valid = validate_vat_format(country_upper, vat)
    return {
        "country_code": country_upper,
        "country_name": rule.country_name,
        "vat_number": vat,
        "format": rule.vat_format,
        "valid": valid,
    }


# ──────────────────────────────────────────────
# Error Handlers
# ──────────────────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": True, "detail": exc.detail, "status_code": exc.status_code},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": True, "detail": "Internal server error", "status_code": 500},
    )


# ──────────────────────────────────────────────
# Main Entry
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
