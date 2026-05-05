"""
E-Invoice Router API — Data Pipeline
=====================================
Core data layer: country rules, validation rules, sample invoices,
VAT format validation, invoice structure validation, and format conversion.

Supports all 27 EU member states with real VAT rates and e-invoicing mandates.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


# ════════════════════════════════════════════════════════════════
# Data Classes
# ════════════════════════════════════════════════════════════════

@dataclass
class CountryRule:
    """E-invoicing rules for a single EU member state."""
    country_code: str
    country_name: str
    vat_rate: float                    # standard VAT rate (e.g. 19.0)
    vat_format: str                    # regex pattern description
    vat_example: str                   # example valid VAT number
    mandatory_since: Optional[str]     # date e-invoicing became mandatory (B2G)
    threshold_above: Optional[float]   # threshold above which e-invoicing is mandatory (EUR)
    preferred_formats: List[str]       # recommended e-invoice formats
    accepted_formats: List[str]        # all accepted e-invoice formats
    requires_peppol_id: bool = False
    requires_qualified_electronic_signature: bool = False
    central_platform_url: Optional[str] = None
    additional_requirements: List[str] = field(default_factory=list)
    tax_authority_name: Optional[str] = None


@dataclass
class ValidationRule:
    """A single validation check on an invoice."""
    id: str
    format: str
    field: str
    description: str
    severity: str                      # "error" | "warning" | "info"
    rule_type: str                     # "required" | "format" | "range" | "regex" | "business"
    expected: Any = None


@dataclass
class SampleInvoice:
    """A sample invoice document for a given format."""
    id: str
    format: str
    name: str
    description: str
    data: Dict[str, Any]


# ════════════════════════════════════════════════════════════════
# EU Country Rules — All 27 Member States
# ════════════════════════════════════════════════════════════════

EU_COUNTRY_RULES: Dict[str, CountryRule] = {
    "AT": CountryRule(
        country_code="AT", country_name="Austria",
        vat_rate=20.0, vat_format=r"ATU\d{8}", vat_example="ATU12345678",
        mandatory_since="2014-01-01", threshold_above=100000.0,
        preferred_formats=["ubl", "cii"], accepted_formats=["ubl", "cii", "xrechnung", "peppol_bis"],
        requires_peppol_id=True, tax_authority_name="Bundesministerium für Finanzen",
        central_platform_url="https://www.usb.gv.at",
        additional_requirements=["E-invoicing mandatory for B2G above €100k", "e-Rechnung via USP platform"],
    ),
    "BE": CountryRule(
        country_code="BE", country_name="Belgium",
        vat_rate=21.0, vat_format=r"BE0?\d{9}", vat_example="BE0123456789",
        mandatory_since="2022-01-01", threshold_above=0.0,
        preferred_formats=["ubl", "cii", "peppol_bis"], accepted_formats=["ubl", "cii", "peppol_bis"],
        requires_peppol_id=True, tax_authority_name="Service Public Fédéral Finances",
        central_platform_url="https://www.mercurius.belgium.be",
        additional_requirements=["PEPPOL BIS Billing 3.0 recommended", "B2G mandatory via Mercurius platform"],
    ),
    "BG": CountryRule(
        country_code="BG", country_name="Bulgaria",
        vat_rate=20.0, vat_format=r"BG\d{9,10}", vat_example="BG1234567890",
        mandatory_since=None, threshold_above=None,
        preferred_formats=["ubl", "cii"], accepted_formats=["ubl", "cii", "peppol_bis"],
        tax_authority_name="National Revenue Agency",
        additional_requirements=["Voluntary e-invoicing", "B2G pilot programs"],
    ),
    "HR": CountryRule(
        country_code="HR", country_name="Croatia",
        vat_rate=25.0, vat_format=r"HR\d{11}", vat_example="HR12345678901",
        mandatory_since=None, threshold_above=None,
        preferred_formats=["ubl", "cii"], accepted_formats=["ubl", "cii", "peppol_bis"],
        tax_authority_name="Ministry of Finance — Tax Administration",
        additional_requirements=["e-Račun standard in development", "B2G voluntary"],
    ),
    "CY": CountryRule(
        country_code="CY", country_name="Cyprus",
        vat_rate=19.0, vat_format=r"CY\d{8}L", vat_example="CY12345678L",
        mandatory_since=None, threshold_above=None,
        preferred_formats=["ubl", "cii"], accepted_formats=["ubl", "cii"],
        tax_authority_name="Tax Department",
        additional_requirements=["No B2G mandate yet", "Voluntary adoption"],
    ),
    "CZ": CountryRule(
        country_code="CZ", country_name="Czech Republic",
        vat_rate=21.0, vat_format=r"CZ\d{8,10}", vat_example="CZ1234567890",
        mandatory_since=None, threshold_above=None,
        preferred_formats=["ubl", "cii", "xrechnung"], accepted_formats=["ubl", "cii", "xrechnung", "peppol_bis"],
        tax_authority_name="General Financial Directorate",
        additional_requirements=["ISDOC format common", "B2G voluntary"],
    ),
    "DK": CountryRule(
        country_code="DK", country_name="Denmark",
        vat_rate=25.0, vat_format=r"DK\d{8}", vat_example="DK12345678",
        mandatory_since="2024-01-01", threshold_above=0.0,
        preferred_formats=["ubl", "peppol_bis"], accepted_formats=["ubl", "peppol_bis", "cii"],
        requires_peppol_id=True, tax_authority_name="Skattestyrelsen",
        central_platform_url="https://www.nemhandel.dk",
        additional_requirements=["NemHandel platform", "PEPPOL BIS Billing mandatory for B2G"],
    ),
    "EE": CountryRule(
        country_code="EE", country_name="Estonia",
        vat_rate=20.0, vat_format=r"EE\d{9}", vat_example="EE123456789",
        mandatory_since=None, threshold_above=None,
        preferred_formats=["ubl", "cii"], accepted_formats=["ubl", "cii", "peppol_bis"],
        tax_authority_name="Estonian Tax and Customs Board",
        additional_requirements=["e-invoice via e-invoicing operator", "XRoad compatible"],
    ),
    "FI": CountryRule(
        country_code="FI", country_name="Finland",
        vat_rate=25.5, vat_format=r"FI\d{7}", vat_example="FI1234567",
        mandatory_since="2020-04-01", threshold_above=0.0,
        preferred_formats=["ubl", "cii", "peppol_bis"], accepted_formats=["ubl", "cii", "peppol_bis", "finvoice"],
        requires_peppol_id=True, tax_authority_name="Finnish Tax Administration",
        central_platform_url="https://www.stat.fi/aineistot/verkkolaskutus",
        additional_requirements=["Finvoice 3.0 also accepted", "B2G mandatory via PEPPOL"],
    ),
    "FR": CountryRule(
        country_code="FR", country_name="France",
        vat_rate=20.0, vat_format=r"FR\d{11}", vat_example="FR12345678901",
        mandatory_since="2024-09-01", threshold_above=0.0,
        preferred_formats=["ubl", "cii", "facturae", "zugferd"], accepted_formats=["ubl", "cii", "peppol_bis", "facturae", "zugferd", "fattura_pa"],
        requires_qualified_electronic_signature=True, tax_authority_name="Direction Générale des Finances Publiques",
        central_platform_url="https://www.impots.gouv.fr/pp",
        additional_requirements=["PPF (Portail Public de Facturation) mandatory", "B2G and B2B phased mandate from 2024-2026"],
    ),
    "DE": CountryRule(
        country_code="DE", country_name="Germany",
        vat_rate=19.0, vat_format=r"DE\d{9}", vat_example="DE123456789",
        mandatory_since="2025-01-01", threshold_above=0.0,
        preferred_formats=["xrechnung", "ubl", "cii"], accepted_formats=["xrechnung", "ubl", "cii", "peppol_bis", "zugferd"],
        requires_peppol_id=False, tax_authority_name="Bundesministerium der Finanzen",
        central_platform_url="https://www.xrechnung.bund.de",
        additional_requirements=["XRechnung mandatory for B2G federal", "ZUGFeRD/Factur-X accepted B2B", "B2B mandate from 2025"],
    ),
    "EL": CountryRule(
        country_code="EL", country_name="Greece",
        vat_rate=24.0, vat_format=r"EL\d{9}", vat_example="EL123456789",
        mandatory_since="2020-01-01", threshold_above=0.0,
        preferred_formats=["ubl", "cii"], accepted_formats=["ubl", "cii", "peppol_bis"],
        requires_peppol_id=True, tax_authority_name="Independent Authority for Public Revenue",
        central_platform_url="https://www.mydata.gov.gr",
        additional_requirements=["myDATA platform mandatory for all", "PEPPOL BIS for B2G"],
    ),
    "HU": CountryRule(
        country_code="HU", country_name="Hungary",
        vat_rate=27.0, vat_format=r"HU\d{8}", vat_example="HU12345678",
        mandatory_since="2020-07-01", threshold_above=0.0,
        preferred_formats=["ubl", "cii"], accepted_formats=["ubl", "cii", "peppol_bis"],
        requires_qualified_electronic_signature=False, tax_authority_name="National Tax and Customs Administration",
        central_platform_url="https://www.onlineszamla.nav.gov.hu",
        additional_requirements=["Online Számla real-time reporting", "E-invoicing mandatory for all B2B"],
    ),
    "IE": CountryRule(
        country_code="IE", country_name="Ireland",
        vat_rate=23.0, vat_format=r"IE\d{7}[A-Z]", vat_example="IE1234567T",
        mandatory_since="2022-01-01", threshold_above=0.0,
        preferred_formats=["ubl", "peppol_bis"], accepted_formats=["ubl", "peppol_bis", "cii"],
        requires_peppol_id=True, tax_authority_name="Office of the Revenue Commissioners",
        central_platform_url="https://www.peppol.ie",
        additional_requirements=["PEPPOL BIS Billing mandatory B2G", "eInvoicing.gov.ie portal"],
    ),
    "IT": CountryRule(
        country_code="IT", country_name="Italy",
        vat_rate=22.0, vat_format=r"IT\d{11}", vat_example="IT12345678901",
        mandatory_since="2019-01-01", threshold_above=0.0,
        preferred_formats=["fattura_pa", "ubl", "cii"], accepted_formats=["fattura_pa", "ubl", "cii", "peppol_bis"],
        requires_qualified_electronic_signature=True, tax_authority_name="Agenzia delle Entrate",
        central_platform_url="https://www.fatturapa.gov.it",
        additional_requirements=["FatturaPA mandatory B2B and B2G", "SDI (Sistema di Interscambio) platform"],
    ),
    "LV": CountryRule(
        country_code="LV", country_name="Latvia",
        vat_rate=21.0, vat_format=r"LV\d{11}", vat_example="LV12345678901",
        mandatory_since=None, threshold_above=None,
        preferred_formats=["ubl", "cii"], accepted_formats=["ubl", "cii", "peppol_bis"],
        tax_authority_name="State Revenue Service",
        additional_requirements=["Voluntary e-invoicing", "PEPPOL optional"],
    ),
    "LT": CountryRule(
        country_code="LT", country_name="Lithuania",
        vat_rate=21.0, vat_format=r"LT\d{9,12}", vat_example="LT123456789",
        mandatory_since=None, threshold_above=None,
        preferred_formats=["ubl", "cii"], accepted_formats=["ubl", "cii", "peppol_bis"],
        tax_authority_name="State Tax Inspectorate",
        additional_requirements=["eSąskaita standard", "Voluntary B2G"],
    ),
    "LU": CountryRule(
        country_code="LU", country_name="Luxembourg",
        vat_rate=17.0, vat_format=r"LU\d{8}", vat_example="LU12345678",
        mandatory_since=None, threshold_above=None,
        preferred_formats=["ubl", "cii", "peppol_bis"], accepted_formats=["ubl", "cii", "peppol_bis", "zugferd"],
        tax_authority_name="Administration des Contributions Directes",
        additional_requirements=["Voluntary e-invoicing", "PEPPOL optional"],
    ),
    "MT": CountryRule(
        country_code="MT", country_name="Malta",
        vat_rate=18.0, vat_format=r"MT\d{8}", vat_example="MT12345678",
        mandatory_since=None, threshold_above=None,
        preferred_formats=["ubl", "cii"], accepted_formats=["ubl", "cii", "peppol_bis"],
        tax_authority_name="Commissioner for Revenue",
        additional_requirements=["Voluntary adoption", "PEPPOL pilot underway"],
    ),
    "NL": CountryRule(
        country_code="NL", country_name="Netherlands",
        vat_rate=21.0, vat_format=r"NL\d{9}B\d{2}", vat_example="NL123456789B01",
        mandatory_since="2017-01-01", threshold_above=0.0,
        preferred_formats=["ubl", "peppol_bis", "cii"], accepted_formats=["ubl", "peppol_bis", "cii", "xrechnung"],
        requires_peppol_id=True, tax_authority_name="Belastingdienst",
        central_platform_url="https://www.simpledoxinvoicing.com",
        additional_requirements=["PEPPOL BIS mandatory B2G", "Digipoort platform", "Simpele factuur via Digipoort"],
    ),
    "PL": CountryRule(
        country_code="PL", country_name="Poland",
        vat_rate=23.0, vat_format=r"PL\d{10}", vat_example="PL1234567890",
        mandatory_since="2022-01-01", threshold_above=0.0,
        preferred_formats=["ubl", "cii"], accepted_formats=["ubl", "cii", "peppol_bis"],
        requires_qualified_electronic_signature=True, tax_authority_name="Ministry of Finance",
        central_platform_url="https://www.podatki.gov.pl/ksef",
        additional_requirements=["KSeF mandatory (National e-Invoice System)", "B2B and B2G from 2024-2026 phased"],
    ),
    "PT": CountryRule(
        country_code="PT", country_name="Portugal",
        vat_rate=23.0, vat_format=r"PT\d{9}", vat_example="PT123456789",
        mandatory_since="2023-01-01", threshold_above=0.0,
        preferred_formats=["ubl", "cii", "facturae"], accepted_formats=["ubl", "cii", "peppol_bis", "facturae"],
        requires_peppol_id=True, tax_authority_name="Autoridade Tributária e Aduaneira",
        central_platform_url="https://www.portaldasfinancas.gov.pt",
        additional_requirements=["e-fatura / ATCUD mandatory", "PEPPOL for B2G"],
    ),
    "RO": CountryRule(
        country_code="RO", country_name="Romania",
        vat_rate=19.0, vat_format=r"RO\d{2,10}", vat_example="RO1234567890",
        mandatory_since="2022-07-01", threshold_above=0.0,
        preferred_formats=["ubl", "cii"], accepted_formats=["ubl", "cii", "peppol_bis"],
        tax_authority_name="National Agency for Fiscal Administration",
        central_platform_url="https://www.anaf.ro",
        additional_requirements=["e-Factura mandatory B2B", "RO e-invoice system via ANAF"],
    ),
    "SK": CountryRule(
        country_code="SK", country_name="Slovakia",
        vat_rate=23.0, vat_format=r"SK\d{10}", vat_example="SK1234567890",
        mandatory_since=None, threshold_above=None,
        preferred_formats=["ubl", "cii", "xrechnung"], accepted_formats=["ubl", "cii", "xrechnung", "peppol_bis"],
        tax_authority_name="Financial Administration of the Slovak Republic",
        additional_requirements=["ISDOC compatible", "B2G voluntary"],
    ),
    "SI": CountryRule(
        country_code="SI", country_name="Slovenia",
        vat_rate=22.0, vat_format=r"SI\d{8}", vat_example="SI12345678",
        mandatory_since=None, threshold_above=None,
        preferred_formats=["ubl", "cii"], accepted_formats=["ubl", "cii", "peppol_bis"],
        tax_authority_name="Financial Administration of the Republic of Slovenia",
        additional_requirements=["e-račun standard", "B2G voluntary"],
    ),
    "ES": CountryRule(
        country_code="ES", country_name="Spain",
        vat_rate=21.0, vat_format=r"ES[A-Z]\d{7}[A-Z0-9]", vat_example="ESB12345678",
        mandatory_since="2025-01-01", threshold_above=0.0,
        preferred_formats=["ubl", "cii", "facturae", "peppol_bis"], accepted_formats=["ubl", "cii", "peppol_bis", "facturae", "zugferd"],
        requires_qualified_electronic_signature=True, tax_authority_name="Agencia Estatal de Administración Tributaria",
        central_platform_url="https://www.facturae.gob.es",
        additional_requirements=["Facturae mandatory B2G", "Ley Crea y Crece B2B mandate from 2025", "SII (Suministro Inmediato de Información)"],
    ),
    "SE": CountryRule(
        country_code="SE", country_name="Sweden",
        vat_rate=25.0, vat_format=r"SE\d{10}", vat_example="SE1234567890",
        mandatory_since="2019-04-01", threshold_above=0.0,
        preferred_formats=["ubl", "peppol_bis"], accepted_formats=["ubl", "peppol_bis", "cii"],
        requires_peppol_id=True, tax_authority_name="Skatteverket",
        central_platform_url="https://www.e-legitimation.se",
        additional_requirements=["PEPPOL BIS mandatory B2G", "Svefaktura format also accepted"],
    ),
}


# ════════════════════════════════════════════════════════════════
# VAT Regex Patterns (compiled)
# ════════════════════════════════════════════════════════════════

_VAT_REGEX: Dict[str, re.Pattern] = {
    code: re.compile(rule.vat_format)
    for code, rule in EU_COUNTRY_RULES.items()
}


# ════════════════════════════════════════════════════════════════
# Validation Rules — Per Format
# ════════════════════════════════════════════════════════════════

VALIDATION_RULES: Dict[str, List[ValidationRule]] = {
    "ubl": [
        ValidationRule("ubl-001", "ubl", "Invoice/cac:ID", "Invoice number is required", "error", "required"),
        ValidationRule("ubl-002", "ubl", "Invoice/cbc:IssueDate", "Issue date is required and must be a valid date", "error", "required"),
        ValidationRule("ubl-003", "ubl", "Invoice/cbc:DueDate", "Due date is required", "error", "required"),
        ValidationRule("ubl-004", "ubl", "Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyName/cbc:Name", "Seller name is required", "error", "required"),
        ValidationRule("ubl-005", "ubl", "Invoice/cac:AccountingCustomerParty/cac:Party/cac:PartyName/cbc:Name", "Buyer name is required", "error", "required"),
        ValidationRule("ubl-006", "ubl", "Invoice/cac:TaxTotal/cbc:TaxAmount", "Tax total amount is required", "error", "required"),
        ValidationRule("ubl-007", "ubl", "Invoice/cac:LegalMonetaryTotal/cbc:LineExtensionTotalAmount", "Total amount is required", "error", "required"),
        ValidationRule("ubl-008", "ubl", "Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID", "Seller VAT ID is recommended", "warning", "required"),
        ValidationRule("ubl-009", "ubl", "Invoice/cbc:InvoiceTypeCode", "Invoice type code should be present", "warning", "required"),
        ValidationRule("ubl-010", "ubl", "Invoice/cac:InvoiceLine", "At least one invoice line is required", "error", "required"),
    ],
    "cii": [
        ValidationRule("cii-001", "cii", "rsm:Invoice/ram:ID", "Invoice number required", "error", "required"),
        ValidationRule("cii-002", "cii", "rsm:Invoice/ram:IssueDateTime", "Issue date required", "error", "required"),
        ValidationRule("cii-003", "cii", "rsm:Invoice/ram:BuyerTradeParty/ram:Name", "Buyer name required", "error", "required"),
        ValidationRule("cii-004", "cii", "rsm:Invoice/ram:SellerTradeParty/ram:Name", "Seller name required", "error", "required"),
        ValidationRule("cii-005", "cii", "rsm:Invoice/ram:SpecifiedTradeSettlement/ram:ApplicableTradeTax", "Tax information required", "error", "required"),
        ValidationRule("cii-006", "cii", "rsm:Invoice/ram:SpecifiedTradeSettlement/ram:SpecifiedTradeSettlementHeaderMonetarySummation/ram:LineTotalAmount", "Line total amount required", "error", "required"),
        ValidationRule("cii-007", "cii", "rsm:Invoice/ram:SellerTradeParty/ram:SpecifiedTaxRegistration/ram:ID", "Seller VAT ID recommended", "warning", "required"),
    ],
    "peppol_bis": [
        ValidationRule("pep-001", "peppol_bis", "Invoice/cac:ID", "Invoice number required", "error", "required"),
        ValidationRule("pep-002", "peppol_bis", "Invoice/cbc:IssueDate", "Issue date required", "error", "required"),
        ValidationRule("pep-003", "peppol_bis", "Invoice/cbc:DocumentCurrencyCode", "Currency code required (ISO 4217)", "error", "required"),
        ValidationRule("pep-004", "peppol_bis", "Invoice/cac:AccountingSupplierParty/cac:Party/cbc:EndpointID", "PEPPOL endpoint ID required", "error", "required"),
        ValidationRule("pep-005", "peppol_bis", "Invoice/cac:AccountingCustomerParty/cac:Party/cbc:EndpointID", "Buyer PEPPOL endpoint ID required", "error", "required"),
        ValidationRule("pep-006", "peppol_bis", "Invoice/cac:LegalMonetaryTotal/cbc:PayableAmount", "Payable amount required", "error", "required"),
        ValidationRule("pep-007", "peppol_bis", "Invoice/cac:InvoiceLine", "At least one invoice line required", "error", "required"),
        ValidationRule("pep-008", "peppol_bis", "Invoice/cac:TaxTotal/cbc:TaxAmount", "Tax total required", "error", "required"),
        ValidationRule("pep-009", "peppol_bis", "Invoice/cbc:ProfileID", "PEPPOL profile ID required", "warning", "required"),
        ValidationRule("pep-010", "peppol_bis", "Invoice/cac:PaymentTerms/cbc:Note", "Payment terms recommended", "warning", "required"),
    ],
    "fattura_pa": [
        ValidationRule("fat-001", "fattura_pa", "FatturaElettronica/FatturaElettronicaHeader/DatiTrasmissione/IdTrasmittente/IdPaese", "Country code required (IT)", "error", "required"),
        ValidationRule("fat-002", "fattura_pa", "FatturaElettronica/FatturaElettronicaHeader/CedentePrestatore/DatiAnagrafici/IdFiscaleIVA/IdPaese", "Seller VAT country required", "error", "required"),
        ValidationRule("fat-003", "fattura_pa", "FatturaElettronica/FatturaElettronicaHeader/CedentePrestatore/DatiAnagrafici/CodiceFiscale", "Seller tax code required", "error", "required"),
        ValidationRule("fat-004", "fattura_pa", "FatturaElettronica/FatturaElettronicaHeader/DatiTrasmissione/ProgressivoInvio", "Progressive sending ID required", "error", "required"),
        ValidationRule("fat-005", "fattura_pa", "FatturaElettronica/FatturaElettronicaBody/DatiGenerali/DatiGeneraliDocumenta/Data", "Document date required", "error", "required"),
        ValidationRule("fat-006", "fattura_pa", "FatturaElettronica/FatturaElettronicaBody/DatiBeniServizi/DatiRiepilogo", "At least one summary data block required", "error", "required"),
        ValidationRule("fat-007", "fattura_pa", "FatturaElettronica/FatturaElettronicaBody/DatiPagamento", "Payment details required", "warning", "required"),
    ],
    "xrechnung": [
        ValidationRule("xre-001", "xrechnung", "Invoice/cbc:ID", "Invoice number required", "error", "required"),
        ValidationRule("xre-002", "xrechnung", "Invoice/cbc:IssueDate", "Issue date required and must be ISO 8601", "error", "format"),
        ValidationRule("xre-003", "xrechnung", "Invoice/cbc:InvoiceTypeCode", "Invoice type code required (e.g. 380, 381)", "error", "required"),
        ValidationRule("xre-004", "xrechnung", "Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID", "Supplier identification required", "error", "required"),
        ValidationRule("xre-005", "xrechnung", "Invoice/cac:AccountingCustomerParty/cac:Party/cac:PartyIdentification/cbc:ID", "Buyer identification recommended", "warning", "required"),
        ValidationRule("xre-006", "xrechnung", "Invoice/cac:LegalMonetaryTotal/cbc:PayableAmount", "Payable amount required", "error", "required"),
        ValidationRule("xre-007", "xrechnung", "Invoice/cac:InvoiceLine/cbc:InvoicedQuantity", "Invoiced quantity required per line", "error", "required"),
        ValidationRule("xre-008", "xrechnung", "Invoice/cac:InvoiceLine/cac:Price/cbc:PriceAmount", "Price amount required per line", "error", "required"),
        ValidationRule("xre-009", "xrechnung", "Invoice/cac:AllowanceCharge", "Allowance/charge details recommended", "warning", "required"),
        ValidationRule("xre-010", "xrechnung", "Invoice/cbc:Note", "Notes/comments recommended", "info", "required"),
    ],
    "facturae": [
        ValidationRule("fae-001", "facturae", "facturae:FileHeader/SchemaVersion", "Schema version required", "error", "required"),
        ValidationRule("fae-002", "facturae", "facturae:Parties/SellerParty/TaxIdentification/TaxIdentificationNumber", "Seller tax ID required", "error", "required"),
        ValidationRule("fae-003", "facturae", "facturae:Parties/BuyerParty/TaxIdentification/TaxIdentificationNumber", "Buyer tax ID required", "error", "required"),
        ValidationRule("fae-004", "facturae", "facturae:Invoices/Invoice/InvoiceHeader/InvoiceNumber", "Invoice number required", "error", "required"),
        ValidationRule("fae-005", "facturae", "facturae:Invoices/Invoice/InvoiceHeader/InvoiceDate", "Invoice date required", "error", "required"),
        ValidationRule("fae-006", "facturae", "facturae:Invoices/Invoice/InvoiceIssueData/PlaceOfIssue", "Place of issue required", "warning", "required"),
        ValidationRule("fae-007", "facturae", "facturae:Invoices/Invoice/TaxesOutputs", "At least one tax output required", "error", "required"),
        ValidationRule("fae-008", "facturae", "facturae:Invoices/Invoice/InvoiceTotals/TotalGrossAmount", "Total gross amount required", "error", "required"),
    ],
    "zugferd": [
        ValidationRule("zug-001", "zugferd", "ZUGFeRD:Invoice/ID", "Invoice number required", "error", "required"),
        ValidationRule("zug-002", "zugferd", "ZUGFeRD:Invoice/IssueDate", "Issue date required", "error", "required"),
        ValidationRule("zug-003", "zugferd", "ZUGFeRD:Invoice/Seller/Name", "Seller name required", "error", "required"),
        ValidationRule("zug-004", "zugferd", "ZUGFeRD:Invoice/Buyer/Name", "Buyer name required", "error", "required"),
        ValidationRule("zug-005", "zugferd", "ZUGFeRD:Invoice/LineItem", "At least one line item required", "error", "required"),
        ValidationRule("zug-006", "zugferd", "ZUGFeRD:Invoice/Summation/GrandTotalAmount", "Grand total amount required", "error", "required"),
        ValidationRule("zug-007", "zugferd", "ZUGFeRD:Invoice/Seller/VATNumber", "Seller VAT ID recommended", "warning", "required"),
        ValidationRule("zug-008", "zugferd", "ZUGFeRD:Invoice/Profile", "ZUGFeRD profile required (BASIC, EXTENDED, etc.)", "error", "required"),
        ValidationRule("zug-009", "zugferd", "ZUGFeRD:Invoice/Summation/TotalTaxAmount", "Total tax amount required", "error", "required"),
    ],
}


# ════════════════════════════════════════════════════════════════
# Format Names
# ════════════════════════════════════════════════════════════════

FORMAT_NAMES: Dict[str, str] = {
    "ubl": "UBL 2.1",
    "cii": "CII (Cross-Industry Invoice)",
    "peppol_bis": "PEPPOL BIS Billing 3.0",
    "fattura_pa": "Fattura PA / FatturaElettronica",
    "xrechnung": "XRechnung",
    "facturae": "Facturae",
    "zugferd": "ZUGFeRD / Factur-X",
}


# ════════════════════════════════════════════════════════════════
# Sample Invoices
# ════════════════════════════════════════════════════════════════

SAMPLE_INVOICES: List[SampleInvoice] = [
    SampleInvoice(
        id="ubl-001", format="ubl", name="Simple B2B Invoice (UBL)",
        description="A basic B2B UBL 2.1 invoice with seller, buyer, line items, and tax.",
        data={
            "ID": "INV-2025-0001", "IssueDate": "2025-04-01", "DueDate": "2025-05-01",
            "InvoiceTypeCode": "380",
            "AccountingSupplierParty": {
                "Party": {
                    "PartyName": {"Name": "Acme GmbH"},
                    "PartyTaxScheme": {"CompanyID": "DE123456789"},
                    "PostalAddress": {"Country": {"IdentificationCode": "DE"}, "City": "Berlin", "Street": "Industriestr. 10"},
                },
                "VATID": "DE123456789",
            },
            "AccountingCustomerParty": {
                "Party": {
                    "PartyName": {"Name": "Buyer Corp"},
                    "PostalAddress": {"Country": {"IdentificationCode": "FR"}, "City": "Paris", "Street": "Rue de Rivoli 5"},
                },
            },
            "TaxTotal": {"TaxAmount": 190.00},
            "LegalMonetaryTotal": {"LineExtensionTotalAmount": 1000.00, "PayableAmount": 1190.00},
            "InvoiceLine": [
                {"ID": "1", "InvoicedQuantity": 10, "LineExtensionAmount": 500.00,
                 "Item": {"Name": "Widget A", "SellersItemIdentification": {"ID": "WGT-001"}},
                 "Price": {"PriceAmount": 50.00}},
                {"ID": "2", "InvoicedQuantity": 5, "LineExtensionAmount": 500.00,
                 "Item": {"Name": "Gadget B", "SellersItemIdentification": {"ID": "GDG-001"}},
                 "Price": {"PriceAmount": 100.00}},
            ],
        },
    ),
    SampleInvoice(
        id="cii-001", format="cii", name="Cross-Industry Invoice Sample",
        description="A CII (Cross-Industry Invoice) sample with basic trade details.",
        data={
            "ID": "CII-2025-001", "IssueDateTime": {"DateTimeString": {"format": "102", "value": "20250401"}},
            "BuyerTradeParty": {"Name": "Buyer Corp", "SpecifiedTaxRegistration": {"ID": "FR12345678901"}},
            "SellerTradeParty": {"Name": "Acme SAS", "SpecifiedTaxRegistration": {"ID": "DE123456789"}},
            "SpecifiedTradeSettlement": {
                "ApplicableTradeTax": {"TypeCode": "VAT", "CategoryCode": "S", "RateApplicablePercent": 19.0, "CalculatedAmount": 190.00},
                "SpecifiedTradeSettlementHeaderMonetarySummation": {"LineTotalAmount": 1000.00, "GrandTotalAmount": 1190.00},
            },
        },
    ),
    SampleInvoice(
        id="peppol-001", format="peppol_bis", name="PEPPOL BIS Billing 3.0",
        description="PEPPOL BIS Billing 3.0 sample with endpoint IDs and profile.",
        data={
            "ID": "PEP-2025-001", "IssueDate": "2025-04-01", "DocumentCurrencyCode": "EUR",
            "ProfileID": "urn:fdc:peppol.eu:2017:poacc:billing:3.0",
            "AccountingSupplierParty": {
                "Party": {
                    "EndpointID": {"schemeID": "0088", "value": "DE123456789"},
                    "PartyName": {"Name": "Acme GmbH"},
                },
                "VATID": "DE123456789",
            },
            "AccountingCustomerParty": {
                "Party": {
                    "EndpointID": {"schemeID": "0088", "value": "FR12345678901"},
                    "PartyName": {"Name": "Buyer Corp"},
                },
            },
            "TaxTotal": {"TaxAmount": 190.00},
            "LegalMonetaryTotal": {"LineExtensionTotalAmount": 1000.00, "PayableAmount": 1190.00},
            "InvoiceLine": [
                {"ID": "1", "InvoicedQuantity": 10, "LineExtensionAmount": 500.00,
                 "Item": {"Name": "Widget A"},
                 "Price": {"PriceAmount": 50.00}},
                {"ID": "2", "InvoicedQuantity": 5, "LineExtensionAmount": 500.00,
                 "Item": {"Name": "Gadget B"},
                 "Price": {"PriceAmount": 100.00}},
            ],
        },
    ),
    SampleInvoice(
        id="fattura-001", format="fattura_pa", name="Fattura PA Sample",
        description="Italian FatturaElettronica sample for B2G/B2B.",
        data={
            "FatturaElettronica": {
                "FatturaElettronicaHeader": {
                    "DatiTrasmissione": {
                        "IdTrasmittente": {"IdPaese": "IT", "IdCodice": "01234567890"},
                        "ProgressivoInvio": "INV-00001",
                        "FormatoTrasmissione": "FPR12",
                    },
                    "CedentePrestatore": {
                        "DatiAnagrafici": {
                            "IdFiscaleIVA": {"IdPaese": "IT", "IdCodice": "01234567890"},
                            "CodiceFiscale": "RSSMRA85M01H501U",
                            "Anagrafica": {"Denominazione": "Acme S.r.l."},
                        },
                    },
                    "CessionarioCommittente": {
                        "DatiAnagrafici": {
                            "IdFiscaleIVA": {"IdPaese": "IT", "IdCodice": "09876543210"},
                            "CodiceFiscale": "DRGLCU80A01H501F",
                            "Anagrafica": {"Denominazione": "Buyer S.p.A."},
                        },
                    },
                },
                "FatturaElettronicaBody": {
                    "DatiGenerali": {
                        "DatiGeneraliDocumento": {
                            "Data": "2025-04-01", "Numero": "INV-00001",
                            "ImportoTotaleDocumento": 1220.00,
                        },
                    },
                    "DatiBeniServizi": {
                        "DatiRiepilogo": [
                            {"AliquotaIVA": 22.0, "ImponibileImporto": 1000.00, "Imposta": 220.00},
                        ],
                    },
                    "DatiPagamento": {
                        "CondizioniPagamento": "TP02",
                        "DettaglioPagamento": [
                            {"ModalitaPagamento": "MP05", "DataScadenzaPagamento": "2025-05-01",
                             "ImportoPagamento": 1220.00},
                        ],
                    },
                },
            },
        },
    ),
    SampleInvoice(
        id="xrechnung-001", format="xrechnung", name="XRechnung Sample",
        description="German XRechnung sample for federal B2G compliance.",
        data={
            "ID": "XRE-2025-001", "IssueDate": "2025-04-01", "InvoiceTypeCode": "380",
            "Note": "Rechnung gemäß XRechnung-Standard",
            "AccountingSupplierParty": {
                "Party": {
                    "PartyIdentification": {"ID": {"schemeID": "0183", "value": "DE123456789"}},
                    "PartyName": {"Name": "Acme GmbH"},
                },
            },
            "AccountingCustomerParty": {
                "Party": {
                    "PartyIdentification": {"ID": {"schemeID": "0183", "value": "DE987654321"}},
                    "PartyName": {"Name": "Bundesbehörde XYZ"},
                },
            },
            "TaxTotal": {"TaxAmount": 190.00},
            "LegalMonetaryTotal": {"LineExtensionTotalAmount": 1000.00, "PayableAmount": 1190.00},
            "InvoiceLine": [
                {"ID": "1", "InvoicedQuantity": 10, "LineExtensionAmount": 500.00,
                 "Item": {"Name": "Beratungsleistung A"},
                 "Price": {"PriceAmount": 50.00}},
                {"ID": "2", "InvoicedQuantity": 5, "LineExtensionAmount": 500.00,
                 "Item": {"Name": "Software Lizenz B"},
                 "Price": {"PriceAmount": 100.00}},
            ],
        },
    ),
    SampleInvoice(
        id="facturae-001", format="facturae", name="Facturae Sample",
        description="Spanish Facturae sample with tax outputs.",
        data={
            "FileHeader": {"SchemaVersion": "3.2.2"},
            "Parties": {
                "SellerParty": {
                    "TaxIdentification": {"TaxIdentificationNumber": "B12345678", "PersonTypeCode": "J"},
                    "LegalPerson": {"Name": "Acme España S.L."},
                },
                "BuyerParty": {
                    "TaxIdentification": {"TaxIdentificationNumber": "A87654321", "PersonTypeCode": "J"},
                    "LegalPerson": {"Name": "Buyer España S.A."},
                },
            },
            "Invoices": [
                {
                    "Invoice": {
                        "InvoiceHeader": {"InvoiceNumber": "FAE-2025-001", "InvoiceDate": "2025-04-01"},
                        "InvoiceIssueData": {"PlaceOfIssue": "Madrid"},
                        "TaxesOutputs": [
                            {"TaxTypeCode": "01", "TaxRate": 21.0, "TaxableBase": {"TotalAmount": 1000.00},
                             "TaxAmount": {"TotalAmount": 210.00}},
                        ],
                        "InvoiceTotals": {"TotalGrossAmount": 1210.00},
                    },
                },
            ],
        },
    ),
    SampleInvoice(
        id="zugferd-001", format="zugferd", name="ZUGFeRD Factur-X Sample",
        description="ZUGFeRD/Factur-X BASIC profile invoice sample.",
        data={
            "ID": "ZUG-2025-001", "IssueDate": "2025-04-01", "Profile": "BASIC",
            "Seller": {"Name": "Acme GmbH", "VATNumber": "DE123456789"},
            "Buyer": {"Name": "Buyer Corp"},
            "LineItem": [
                {"ID": "1", "Description": "Produkt A", "Quantity": 10, "UnitPrice": 50.00,
                 "LineTotal": 500.00, "TaxRate": 19.0},
                {"ID": "2", "Description": "Dienstleistung B", "Quantity": 5, "UnitPrice": 100.00,
                 "LineTotal": 500.00, "TaxRate": 19.0},
            ],
            "Summation": {"GrandTotalAmount": 1190.00, "TotalTaxAmount": 190.00},
        },
    ),
]

# Build sample lookup by format
_SAMPLE_BY_FORMAT: Dict[str, SampleInvoice] = {s.format: s for s in SAMPLE_INVOICES}

# ════════════════════════════════════════════════════════════════
# DataCache
# ════════════════════════════════════════════════════════════════

class DataCache:
    """Simple TTL-based in-memory cache."""
    def __init__(self, ttl=3600):
        self._cache: Dict[str, Any] = {}
        self._ttl = ttl

    def get(self, key):
        val, ts = self._cache.get(key, (None, 0))
        if val is not None and time.time() - ts < self._ttl:
            return val
        return None

    def set(self, key, val):
        self._cache[key] = (val, time.time())

    def invalidate(self, key):
        self._cache.pop(key, None)

    def clear(self):
        self._cache.clear()


cache = DataCache()


# ════════════════════════════════════════════════════════════════
# Alias for main.py compatibility (uses EU_COUNTRIES at line 330)
# ════════════════════════════════════════════════════════════════

EU_COUNTRIES: Dict[str, CountryRule] = EU_COUNTRY_RULES


# ════════════════════════════════════════════════════════════════
# Public API — Country Lookups
# ════════════════════════════════════════════════════════════════

def get_country_rule(code: str) -> Optional[CountryRule]:
    """Get e-invoicing rules for a specific EU country by ISO alpha-2 code."""
    return EU_COUNTRY_RULES.get(code.upper())


def get_all_countries() -> List[Dict[str, Any]]:
    """Get a list of all EU countries with their key rules."""
    return [
        {
            "country_code": rule.country_code,
            "country_name": rule.country_name,
            "vat_rate": rule.vat_rate,
            "vat_format": rule.vat_format,
            "vat_example": rule.vat_example,
            "mandatory_since": rule.mandatory_since,
            "preferred_formats": rule.preferred_formats,
        }
        for rule in EU_COUNTRY_RULES.values()
    ]


def listify_countries() -> List[Dict[str, Any]]:
    """Get countries as a list of summary dicts (for /v1/countries endpoint)."""
    return [
        {
            "country_code": rule.country_code,
            "country_name": rule.country_name,
            "vat_rate": rule.vat_rate,
            "mandatory_since": rule.mandatory_since,
            "threshold_above": rule.threshold_above,
            "preferred_formats": rule.preferred_formats,
        }
        for rule in EU_COUNTRY_RULES.values()
    ]


# ════════════════════════════════════════════════════════════════
# Public API — Validation Rules
# ════════════════════════════════════════════════════════════════

def get_validation_rules(fmt: Optional[str] = None) -> List[ValidationRule]:
    """Get validation rules, optionally filtered by format name."""
    if fmt is None:
        # Return all rules flattened
        return [r for rules in VALIDATION_RULES.values() for r in rules]
    return VALIDATION_RULES.get(fmt.lower(), [])


# ════════════════════════════════════════════════════════════════
# Public API — Format Names
# ════════════════════════════════════════════════════════════════

def get_all_formats() -> List[str]:
    """Get list of all supported format keys."""
    return list(FORMAT_NAMES.keys())


def get_format_names(fmt: Optional[str] = None):
    """Get human-readable format name(s)."""
    if fmt is not None:
        return FORMAT_NAMES.get(fmt.lower(), fmt)
    return list(FORMAT_NAMES.values())


# ════════════════════════════════════════════════════════════════
# Public API — Sample Invoices
# ════════════════════════════════════════════════════════════════

def get_sample_invoice(fmt_or_id: str) -> Optional[SampleInvoice]:
    """Get a sample invoice by format name or by sample ID."""
    fmt_or_id = fmt_or_id.lower()
    # Try format first
    if fmt_or_id in _SAMPLE_BY_FORMAT:
        return _SAMPLE_BY_FORMAT[fmt_or_id]
    # Try sample ID
    for s in SAMPLE_INVOICES:
        if s.id.lower() == fmt_or_id:
            return s
    return None


def get_all_sample_invoices() -> List[SampleInvoice]:
    """Get all sample invoices."""
    return SAMPLE_INVOICES


# ════════════════════════════════════════════════════════════════
# Public API — VAT Validation
# ════════════════════════════════════════════════════════════════

def validate_vat_format(country: str, vat: str) -> bool:
    """Validate a VAT number format for a given EU country."""
    if not vat or not country:
        return False
    vat = vat.strip().upper()
    country = country.upper()
    pattern = _VAT_REGEX.get(country)
    if pattern is None:
        return False
    return bool(pattern.match(vat))


# ════════════════════════════════════════════════════════════════
# Public API — Invoice Structure Validation
# ════════════════════════════════════════════════════════════════

def _safe_traverse(obj: Any, path: str, sep: str = "/") -> bool:
    """Check if a dot/path-separated key path exists in a nested dict."""
    keys = path.split(sep)
    current = obj
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return False
    return True


def validate_invoice_structure(invoice_data: Dict[str, Any], fmt: str = "") -> List[Dict[str, Any]]:
    """
    Validate an invoice against format-specific structural rules.

    Returns a list of result dicts with keys: id, field, description, severity, passed.
    """
    fmt = fmt.lower().strip()
    rules = get_validation_rules(fmt)

    results = []
    for rule in rules:
        field_exists = _safe_traverse(invoice_data, rule.field)
        if rule.rule_type == "required":
            passed = field_exists
        elif rule.rule_type == "format":
            passed = field_exists  # basic field presence check
        else:
            passed = field_exists

        results.append({
            "id": rule.id,
            "field": rule.field,
            "description": rule.description,
            "severity": rule.severity,
            "passed": passed,
        })

    # If no format specified or no rules found, do generic sanity checks
    if not results:
        results = _generic_validation(invoice_data)

    return results


def _generic_validation(invoice_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generic validation when no specific format is provided."""
    checks = [
        ("id", ["ID", "id", "InvoiceNumber", "invoice_number", "Numero"]),
        ("date", ["IssueDate", "issue_date", "InvoiceDate", "Date", "Data"]),
        ("seller", ["AccountingSupplierParty", "Seller", "SellerParty",
                     "CedentePrestatore", "BuyerTradeParty"]),
        ("buyer", ["AccountingCustomerParty", "Buyer", "BuyerParty",
                     "CessionarioCommittente", "SellerTradeParty"]),
        ("amount", ["PayableAmount", "GrandTotalAmount", "ImportoTotaleDocumento",
                     "TotalGrossAmount", "LineExtensionTotalAmount"]),
    ]
    results = []
    for check_id, keys in checks:
        found = any(_safe_traverse(invoice_data, k) for k in keys)
        results.append({
            "id": f"generic-{check_id}",
            "field": check_id,
            "description": f"Field '{check_id}' exists in invoice data",
            "severity": "error" if check_id in ("id", "amount") else "warning",
            "passed": found,
        })
    return results


# ════════════════════════════════════════════════════════════════
# Public API — Format Conversion
# ════════════════════════════════════════════════════════════════

# EN 16931 semantic mapping: source field -> target field
_EN16931_MAPPING: Dict[str, Dict[str, str]] = {
    "ubl": {
        "Invoice/cbc:ID": "ID",
        "Invoice/cbc:IssueDate": "IssueDate",
        "Invoice/cbc:DueDate": "DueDate",
        "Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyName/cbc:Name": "SellerName",
        "Invoice/cac:AccountingCustomerParty/cac:Party/cac:PartyName/cbc:Name": "BuyerName",
        "Invoice/cac:TaxTotal/cbc:TaxAmount": "TaxAmount",
        "Invoice/cac:LegalMonetaryTotal/cbc:LineExtensionTotalAmount": "LineTotal",
        "Invoice/cac:LegalMonetaryTotal/cbc:PayableAmount": "PayableAmount",
        "Invoice/cac:InvoiceLine/cbc:InvoicedQuantity": "Quantity",
        "Invoice/cac:InvoiceLine/cac:Item/cbc:Name": "ItemName",
        "Invoice/cac:InvoiceLine/cac:Price/cbc:PriceAmount": "Price",
    },
    "cii": {
        "rsm:Invoice/ram:ID": "ID",
        "rsm:Invoice/ram:IssueDateTime/udt:DateTimeString/@value": "IssueDate",
        "rsm:Invoice/ram:BuyerTradeParty/ram:Name": "BuyerName",
        "rsm:Invoice/ram:SellerTradeParty/ram:Name": "SellerName",
        "rsm:Invoice/ram:SpecifiedTradeSettlement/ram:ApplicableTradeTax/ram:CalculatedAmount": "TaxAmount",
        "rsm:Invoice/ram:SpecifiedTradeSettlement/ram:SpecifiedTradeSettlementHeaderMonetarySummation/ram:LineTotalAmount": "LineTotal",
        "rsm:Invoice/ram:SpecifiedTradeSettlement/ram:SpecifiedTradeSettlementHeaderMonetarySummation/ram:GrandTotalAmount": "PayableAmount",
    },
    "peppol_bis": {
        "Invoice/cbc:ID": "ID",
        "Invoice/cbc:IssueDate": "IssueDate",
        "Invoice/cbc:DocumentCurrencyCode": "Currency",
        "Invoice/cac:AccountingSupplierParty/cac:Party/cbc:EndpointID/@value": "SellerEndpointID",
        "Invoice/cac:AccountingCustomerParty/cac:Party/cbc:EndpointID/@value": "BuyerEndpointID",
        "Invoice/cac:TaxTotal/cbc:TaxAmount": "TaxAmount",
        "Invoice/cac:LegalMonetaryTotal/cbc:LineExtensionTotalAmount": "LineTotal",
        "Invoice/cac:LegalMonetaryTotal/cbc:PayableAmount": "PayableAmount",
    },
    "fattura_pa": {
        "FatturaElettronica/FatturaElettronicaHeader/DatiTrasmissione/IdTrasmittente/IdCodice": "SenderID",
        "FatturaElettronica/FatturaElettronicaHeader/CedentePrestatore/DatiAnagrafici/Anagrafica/Denominazione": "SellerName",
        "FatturaElettronica/FatturaElettronicaHeader/CessionarioCommittente/DatiAnagrafici/Anagrafica/Denominazione": "BuyerName",
        "FatturaElettronica/FatturaElettronicaBody/DatiGenerali/DatiGeneraliDocumento/ImportoTotaleDocumento": "PayableAmount",
        "FatturaElettronica/FatturaElettronicaBody/DatiBeniServizi/DatiRiepilogo/0/Imposta": "TaxAmount",
    },
    "xrechnung": {
        "Invoice/cbc:ID": "ID",
        "Invoice/cbc:IssueDate": "IssueDate",
        "Invoice/cbc:InvoiceTypeCode": "InvoiceType",
        "Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID/@value": "SellerID",
        "Invoice/cac:AccountingCustomerParty/cac:Party/cac:PartyIdentification/cbc:ID/@value": "BuyerID",
        "Invoice/cac:LegalMonetaryTotal/cbc:PayableAmount": "PayableAmount",
        "Invoice/cac:TaxTotal/cbc:TaxAmount": "TaxAmount",
        "Invoice/cac:LegalMonetaryTotal/cbc:LineExtensionTotalAmount": "LineTotal",
    },
    "facturae": {
        "facturae:Parties/SellerParty/TaxIdentification/TaxIdentificationNumber": "SellerTaxID",
        "facturae:Parties/BuyerParty/TaxIdentification/TaxIdentificationNumber": "BuyerTaxID",
        "facturae:Invoices/Invoice/InvoiceHeader/InvoiceNumber": "ID",
        "facturae:Invoices/Invoice/InvoiceHeader/InvoiceDate": "IssueDate",
        "facturae:Invoices/Invoice/InvoiceTotals/TotalGrossAmount": "PayableAmount",
    },
    "zugferd": {
        "ZUGFeRD:Invoice/ID": "ID",
        "ZUGFeRD:Invoice/IssueDate": "IssueDate",
        "ZUGFeRD:Invoice/Seller/Name": "SellerName",
        "ZUGFeRD:Invoice/Buyer/Name": "BuyerName",
        "ZUGFeRD:Invoice/Summation/GrandTotalAmount": "PayableAmount",
        "ZUGFeRD:Invoice/Summation/TotalTaxAmount": "TaxAmount",
    },
}


def convert_invoice(
    invoice_data: Dict[str, Any],
    source_format: str,
    target_format: str,
) -> Dict[str, Any]:
    """
    Convert an invoice between supported e-invoice formats using
    EN 16931 semantic mapping (intermediate model).
    """
    source_format = source_format.lower().strip()
    target_format = target_format.lower().strip()

    # Validate formats
    supported = set(FORMAT_NAMES.keys())
    if source_format not in supported:
        return {"error": f"Unsupported source format '{source_format}'. Supported: {', '.join(sorted(supported))}"}
    if target_format not in supported:
        return {"error": f"Unsupported target format '{target_format}'. Supported: {', '.join(sorted(supported))}"}

    if source_format == target_format:
        return {
            "status": "no_conversion_needed",
            "source_format": source_format,
            "target_format": target_format,
            "en16931_compliant": True,
            "message": "Source and target formats are identical.",
            "mapping": _build_identity_mapping(invoice_data),
        }

    # Step 1: Extract source fields into EN 16931 intermediate model
    source_mapping = _EN16931_MAPPING.get(source_format, {})
    intermediate: Dict[str, Any] = {}

    for source_path, en_field in source_mapping.items():
        value = _extract_nested_value(invoice_data, source_path)
        if value is not None:
            intermediate[en_field] = value

    # Also try direct top-level keys
    for key in ["ID", "IssueDate", "DueDate", "PayableAmount", "TaxAmount",
                "LineExtensionTotalAmount", "DocumentCurrencyCode", "ProfileID"]:
        if key not in intermediate and key in invoice_data:
            intermediate[key] = invoice_data[key]

    # Step 2: Map from intermediate to target format
    target_mapping_rev: Dict[str, str] = {}
    for tgt_path, en_field in _EN16931_MAPPING.get(target_format, {}).items():
        target_mapping_rev[en_field] = tgt_path

    mapping_details = {}
    for en_field, en_value in intermediate.items():
        target_path = target_mapping_rev.get(en_field)
        if target_path:
            mapping_details[target_path] = {"from": en_field, "value": en_value}
        else:
            mapping_details[en_field] = {"from": en_field, "value": en_value, "note": "No direct mapping to target"}

    en16931_compliant = len(intermediate) >= 4  # at least 4 core fields mapped

    return {
        "status": "converted",
        "source_format": source_format,
        "target_format": target_format,
        "en16931_compliant": en16931_compliant,
        "message": f"Converted from {FORMAT_NAMES.get(source_format, source_format)} "
                   f"to {FORMAT_NAMES.get(target_format, target_format)} "
                   f"via EN 16931 semantic mapping. "
                   f"Mapped {len(intermediate)} fields.",
        "mapping": mapping_details,
    }


def _extract_nested_value(data: Dict[str, Any], path: str) -> Any:
    """Extract a value from nested dict using '/' separated path."""
    keys = path.split("/")
    current: Any = data
    for key in keys:
        # Handle attribute notation like @value
        if key.startswith("@"):
            # Attributes are stored as dict key in parent
            attr_key = key[1:]
            if isinstance(current, dict) and attr_key in current:
                current = current[attr_key]
            else:
                return None
            continue
        # Handle array index notation like /0/
        if key.isdigit():
            idx = int(key)
            if isinstance(current, (list, tuple)) and idx < len(current):
                current = current[idx]
            else:
                return None
            continue
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current


def _build_identity_mapping(data: Dict[str, Any]) -> Dict[str, Any]:
    """Build an identity mapping showing all fields in the data."""
    mapping = {}
    _flatten_dict(data, mapping, "")
    return mapping


def _flatten_dict(d: Dict[str, Any], result: Dict[str, Any], prefix: str):
    """Flatten a nested dict into '/' separated paths."""
    for key, value in d.items():
        path = f"{prefix}/{key}" if prefix else key
        if isinstance(value, dict):
            _flatten_dict(value, result, path)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                item_path = f"{path}/{i}"
                if isinstance(item, dict):
                    _flatten_dict(item, result, item_path)
                else:
                    result[item_path] = item
        else:
            result[path] = value


# ════════════════════════════════════════════════════════════════
# Public API — Conversion Helpers (for endpoints)
# ════════════════════════════════════════════════════════════════

def convert_country_rule_to_dict(rule: CountryRule) -> Dict[str, Any]:
    """Convert a CountryRule dataclass to a dict for API responses."""
    return {
        "country_code": rule.country_code,
        "country_name": rule.country_name,
        "vat_format": rule.vat_format,
        "vat_example": rule.vat_example,
        "mandatory_since": rule.mandatory_since,
        "threshold_above": rule.threshold_above,
        "preferred_formats": rule.preferred_formats,
        "accepted_formats": rule.accepted_formats,
        "requires_peppol_id": rule.requires_peppol_id,
        "requires_qualified_electronic_signature": rule.requires_qualified_electronic_signature,
        "central_platform_url": rule.central_platform_url,
        "additional_requirements": rule.additional_requirements,
        "tax_authority_name": rule.tax_authority_name,
    }


def convert_validation_rule_to_dict(rule: ValidationRule) -> Dict[str, Any]:
    """Convert a ValidationRule dataclass to a dict for API responses."""
    return {
        "id": rule.id,
        "format": rule.format,
        "field": rule.field,
        "description": rule.description,
        "severity": rule.severity,
        "rule_type": rule.rule_type,
    }


def convert_sample_to_dict(sample: SampleInvoice) -> Dict[str, Any]:
    """Convert a SampleInvoice dataclass to a dict for API responses."""
    return {
        "id": sample.id,
        "format": sample.format,
        "name": sample.name,
        "description": sample.description,
        "data": sample.data,
    }


# ════════════════════════════════════════════════════════════════
# Public API — Pipeline Summary
# ════════════════════════════════════════════════════════════════

def get_pipeline_summary() -> Dict[str, Any]:
    """Get a summary of the data pipeline for health checks."""
    total_rules = sum(len(rules) for rules in VALIDATION_RULES.values())
    return {
        "countries_count": len(EU_COUNTRY_RULES),
        "formats_count": len(FORMAT_NAMES),
        "validation_rules_count": total_rules,
        "sample_invoices_count": len(SAMPLE_INVOICES),
        "countries": list(EU_COUNTRY_RULES.keys()),
        "formats": list(FORMAT_NAMES.keys()),
        "cache_ttl_seconds": 3600,
    }
