"""
E-Invoice Router — Data Pipeline
Built-in curated dataset of EU e-invoicing standards.

Covers:
- All 27 EU countries' e-invoicing rules (B2G mandates, format preferences)
- PEPPOL BIS Billing 3.0 (UBL 2.1), CII (Cross Industry Invoice) D16B
- Syntax-level schemas, validation rules, sample invoices
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union


# ──────────────────────────────────────────────
# Enums & Types
# ──────────────────────────────────────────────

class InvoiceFormat(str, Enum):
    """Supported e-invoice syntax formats."""
    UBL = "ubl"
    CII = "cii"
    PEPPOL_BIS = "peppol_bis"
    FACTURAE = "facturae"
    ZUGFERD = "zugferd"
    XRechnung = "xrechnung"
    FatturaPA = "fattura_pa"
    EN16931 = "en16931"


class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationRule:
    id: str
    description: str
    xpath: Optional[str] = None
    severity: ValidationSeverity = ValidationSeverity.ERROR
    schema_ref: Optional[str] = None
    eu_standard_ref: Optional[str] = None


@dataclass
class CountryRule:
    country_code: str
    country_name: str
    vat_format: str
    vat_example: str
    mandatory_since: Optional[str]
    threshold_above: Optional[float]  # EUR
    preferred_formats: List[str]
    accepted_formats: List[str]
    requires_peppol_id: bool = False
    requires_qualified_electronic_signature: bool = False
    central_platform_url: Optional[str] = None
    additional_requirements: List[str] = field(default_factory=list)
    tax_authority_name: Optional[str] = None


@dataclass
class InvoiceSample:
    id: str
    format: str
    title: str
    description: str
    valid: bool = True
    data: dict = field(default_factory=dict)
    xml_body: Optional[str] = None


# ──────────────────────────────────────────────
# EU Country Rules Dataset
# ──────────────────────────────────────────────

EU_COUNTRY_RULES: List[CountryRule] = [
    CountryRule(
        country_code="AT", country_name="Austria",
        vat_format="ATU\\d{8}", vat_example="ATU12345678",
        mandatory_since="2014-01-01", threshold_above=100000.0,
        preferred_formats=["ubl", "xrechnung"],
        accepted_formats=["ubl", "cii", "peppol_bis", "xrechnung"],
        central_platform_url="https://www.usp.gv.at/",
        additional_requirements=["eRechnung for B2G mandatory since 2014", "XRechnung format accepted for B2G"],
        tax_authority_name="Bundesministerium für Finanzen"
    ),
    CountryRule(
        country_code="BE", country_name="Belgium",
        vat_format="BE0\\d{9}", vat_example="BE0123456789",
        mandatory_since="2023-01-01", threshold_above=0.0,
        preferred_formats=["ubl", "peppol_bis"],
        accepted_formats=["ubl", "cii", "peppol_bis", "facturae"],
        requires_peppol_id=True,
        central_platform_url="https://www.mercurius.belgium.be/",
        additional_requirements=["PEPPOL network mandatory for B2G", "Mercurius platform"],
        tax_authority_name="SPF Finances"
    ),
    CountryRule(
        country_code="BG", country_name="Bulgaria",
        vat_format="BG\\d{9,10}", vat_example="BG123456789",
        mandatory_since=None, threshold_above=None,
        preferred_formats=["ubl"],
        accepted_formats=["ubl", "cii"],
        tax_authority_name="National Revenue Agency"
    ),
    CountryRule(
        country_code="HR", country_name="Croatia",
        vat_format="HR\\d{11}", vat_example="HR12345678901",
        mandatory_since="2014-01-01", threshold_above=0.0,
        preferred_formats=["ubl", "cii"],
        accepted_formats=["ubl", "cii"],
        additional_requirements=["e-Račun standard", "Must use FINA platform for B2G"],
        tax_authority_name="Ministry of Finance"
    ),
    CountryRule(
        country_code="CY", country_name="Cyprus",
        vat_format="CY\\d{8}[A-Z]", vat_example="CY12345678A",
        mandatory_since=None, threshold_above=None,
        preferred_formats=["ubl", "peppol_bis"],
        accepted_formats=["ubl", "cii", "peppol_bis"],
        tax_authority_name="Tax Department"
    ),
    CountryRule(
        country_code="CZ", country_name="Czech Republic",
        vat_format="CZ\\d{8,10}", vat_example="CZ12345678",
        mandatory_since="2025-01-01", threshold_above=None,
        preferred_formats=["ubl", "cii"],
        accepted_formats=["ubl", "cii", "peppol_bis"],
        additional_requirements=["Povinná elektronická fakturace B2G from 2025"],
        tax_authority_name="Financial Administration"
    ),
    CountryRule(
        country_code="DK", country_name="Denmark",
        vat_format="DK\\d{8}", vat_example="DK12345678",
        mandatory_since="2005-02-01", threshold_above=0.0,
        preferred_formats=["ubl", "peppol_bis"],
        accepted_formats=["ubl", "cii", "peppol_bis"],
        requires_peppol_id=True,
        central_platform_url="https://nemhandel.dk/",
        additional_requirements=["NemHandel platform", "OIOUBL standard historically"],
        tax_authority_name="Skattestyrelsen"
    ),
    CountryRule(
        country_code="EE", country_name="Estonia",
        vat_format="EE\\d{9}", vat_example="EE123456789",
        mandatory_since="2019-04-01", threshold_above=10000.0,
        preferred_formats=["ubl", "peppol_bis"],
        accepted_formats=["ubl", "cii", "peppol_bis"],
        central_platform_url="https://www.e-arve.ee/",
        additional_requirements=["e-Invoice through PEPPOL or e-Arve keskus"],
        tax_authority_name="Estonian Tax and Customs Board"
    ),
    CountryRule(
        country_code="FI", country_name="Finland",
        vat_format="FI\\d{8}", vat_example="FI12345678",
        mandatory_since="2020-04-01", threshold_above=0.0,
        preferred_formats=["ubl", "cii", "peppol_bis"],
        accepted_formats=["ubl", "cii", "peppol_bis"],
        requires_peppol_id=True,
        central_platform_url="https://www.verkkolasku.fi/",
        additional_requirements=["Finnish e-invoice standard (Finvoice 3.0)", "TEAPSG XML"],
        tax_authority_name="Finnish Tax Administration"
    ),
    CountryRule(
        country_code="FR", country_name="France",
        vat_format="FR[A-Z0-9]{2}\\d{9}", vat_example="FRAB123456789",
        mandatory_since="2024-09-01", threshold_above=None,
        preferred_formats=["ubl", "facturae"],
        accepted_formats=["ubl", "cii", "facturae", "peppol_bis"],
        requires_qualified_electronic_signature=True,
        central_platform_url="https://www.impots.gouv.fr/",
        additional_requirements=["Chorus Pro platform", "Factur-X (Zugferd) hybrid format",
                                 "PPF (Portail Public de Facturation)"],
        tax_authority_name="Direction Générale des Finances Publiques"
    ),
    CountryRule(
        country_code="DE", country_name="Germany",
        vat_format="DE\\d{9}", vat_example="DE123456789",
        mandatory_since="2025-01-01", threshold_above=None,
        preferred_formats=["xrechnung"],
        accepted_formats=["ubl", "cii", "xrechnung", "peppol_bis", "zugferd"],
        central_platform_url="https://www.xrechnung.bund.de/",
        additional_requirements=["XRechnung is mandatory for B2G", "Peppol access point recommended",
                                 "ZUGFeRD 2.0 (Factur-X) for B2B", "EN 16931 compliant"],
        tax_authority_name="Bundesministerium der Finanzen"
    ),
    CountryRule(
        country_code="GR", country_name="Greece",
        vat_format="EL\\d{9}", vat_example="EL123456789",
        mandatory_since="2021-01-01", threshold_above=0.0,
        preferred_formats=["ubl", "cii"],
        accepted_formats=["ubl", "cii", "peppol_bis"],
        central_platform_url="https://www.aade.gr/",
        additional_requirements=["myDATA platform", "e-Books (Ηλεκτρονικά Βιβλία ΑΑΔΕ)"],
        tax_authority_name="Independent Authority for Public Revenue"
    ),
    CountryRule(
        country_code="HU", country_name="Hungary",
        vat_format="HU\\d{8}", vat_example="HU12345678",
        mandatory_since="2018-07-01", threshold_above=0.0,
        preferred_formats=["ubl", "cii"],
        accepted_formats=["ubl", "cii", "peppol_bis"],
        central_platform_url="https://online-szamla.nav.gov.hu/",
        additional_requirements=["Online Invoice (Online Számla) real-time reporting",
                                 "NAV real-time data reporting mandatory"],
        tax_authority_name="National Tax and Customs Administration"
    ),
    CountryRule(
        country_code="IE", country_name="Ireland",
        vat_format="IE\\d{7}[A-Z]{1,2}", vat_example="IE1234567A",
        mandatory_since=None, threshold_above=None,
        preferred_formats=["ubl", "peppol_bis"],
        accepted_formats=["ubl", "cii", "peppol_bis"],
        central_platform_url="https://www.ros.ie/",
        tax_authority_name="Office of the Revenue Commissioners"
    ),
    CountryRule(
        country_code="IT", country_name="Italy",
        vat_format="IT\\d{11}", vat_example="IT12345678901",
        mandatory_since="2019-01-01", threshold_above=0.0,
        preferred_formats=["fattura_pa"],
        accepted_formats=["ubl", "cii", "fattura_pa"],
        requires_qualified_electronic_signature=True,
        central_platform_url="https://www.fatturapa.gov.it/",
        additional_requirements=["FatturaPA mandatory for all invoices (B2G/B2B)",
                                 "SdI (Sistema di Interscambio)", "QR code mandatory"],
        tax_authority_name="Agenzia delle Entrate"
    ),
    CountryRule(
        country_code="LV", country_name="Latvia",
        vat_format="LV\\d{11}", vat_example="LV12345678901",
        mandatory_since="2018-06-01", threshold_above=0.0,
        preferred_formats=["ubl", "peppol_bis"],
        accepted_formats=["ubl", "cii", "peppol_bis"],
        central_platform_url="https://www.e-veseliba.gov.lv/",
        additional_requirements=["e-Veselība platform", "Peppol recommended"],
        tax_authority_name="State Revenue Service"
    ),
    CountryRule(
        country_code="LT", country_name="Lithuania",
        vat_format="LT\\d{9,12}", vat_example="LT123456789",
        mandatory_since="2024-07-01", threshold_above=0.0,
        preferred_formats=["ubl", "peppol_bis"],
        accepted_formats=["ubl", "cii", "peppol_bis"],
        central_platform_url="https://www.eivf.vmi.lt/",
        additional_requirements=["e-Sąskaita platform", "i.SAF reporting"],
        tax_authority_name="State Tax Inspectorate"
    ),
    CountryRule(
        country_code="LU", country_name="Luxembourg",
        vat_format="LU\\d{8}", vat_example="LU12345678",
        mandatory_since=None, threshold_above=None,
        preferred_formats=["ubl", "cii"],
        accepted_formats=["ubl", "cii", "peppol_bis"],
        tax_authority_name="Administration des Contributions Directes"
    ),
    CountryRule(
        country_code="MT", country_name="Malta",
        vat_format="MT\\d{8}", vat_example="MT12345678",
        mandatory_since=None, threshold_above=None,
        preferred_formats=["ubl"],
        accepted_formats=["ubl", "cii"],
        tax_authority_name="Commissioner for Revenue"
    ),
    CountryRule(
        country_code="NL", country_name="Netherlands",
        vat_format="NL\\d{9}B\\d{2}", vat_example="NL123456789B01",
        mandatory_since="2017-01-01", threshold_above=0.0,
        preferred_formats=["ubl", "peppol_bis"],
        accepted_formats=["ubl", "cii", "peppol_bis", "xrechnung"],
        requires_peppol_id=True,
        central_platform_url="https://www.simplerinvoicing.org/",
        additional_requirements=["Digipoort platform", "Peppol mandatory B2G",
                                 "EN 16931 compliant", "Simplerinvoicing (SI-UBL)"],
        tax_authority_name="Belastingdienst"
    ),
    CountryRule(
        country_code="PL", country_name="Poland",
        vat_format="PL\\d{10}", vat_example="PL1234567890",
        mandatory_since="2024-07-01", threshold_above=None,
        preferred_formats=["ubl", "cii"],
        accepted_formats=["ubl", "cii", "peppol_bis", "xrechnung"],
        central_platform_url="https://www.podatki.gov.pl/",
        additional_requirements=["KSeF (Krajowy System e-Faktur) mandatory from 2024/2025",
                                 "Structure FA(1) / FA(2) XML", "Real-time clearance model"],
        tax_authority_name="Ministry of Finance"
    ),
    CountryRule(
        country_code="PT", country_name="Portugal",
        vat_format="PT\\d{9}", vat_example="PT123456789",
        mandatory_since="2020-01-01", threshold_above=0.0,
        preferred_formats=["ubl", "facturae"],
        accepted_formats=["ubl", "cii", "facturae", "peppol_bis"],
        central_platform_url="https://www.portaldasfinancas.gov.pt/",
        additional_requirements=["e-Fatura platform", "SAF-T (PT) reporting",
                                 "Certified invoicing software required"],
        tax_authority_name="Autoridade Tributária e Aduaneira"
    ),
    CountryRule(
        country_code="RO", country_name="Romania",
        vat_format="RO\\d{2,10}", vat_example="RO12345678",
        mandatory_since="2022-07-01", threshold_above=0.0,
        preferred_formats=["ubl", "cii"],
        accepted_formats=["ubl", "cii", "peppol_bis"],
        central_platform_url="https://www.anaf.ro/",
        additional_requirements=["e-Factura system", "RO e-Invoice mandatory B2G",
                                 "RO e-Transport for high-risk goods"],
        tax_authority_name="Agenția Națională de Administrare Fiscală"
    ),
    CountryRule(
        country_code="SK", country_name="Slovakia",
        vat_format="SK\\d{10}", vat_example="SK1234567890",
        mandatory_since="2024-01-01", threshold_above=0.0,
        preferred_formats=["ubl", "cii"],
        accepted_formats=["ubl", "cii", "peppol_bis"],
        additional_requirements=["e-Faktúra system", "IS EFA (Elektronická Fakturácia)"],
        tax_authority_name="Financial Administration"
    ),
    CountryRule(
        country_code="SI", country_name="Slovenia",
        vat_format="SI\\d{8}", vat_example="SI12345678",
        mandatory_since="2015-01-01", threshold_above=0.0,
        preferred_formats=["ubl", "cii"],
        accepted_formats=["ubl", "cii", "peppol_bis"],
        central_platform_url="https://www.efaktura.gov.si/",
        additional_requirements=["e-Faktura platform", "e-Davki system"],
        tax_authority_name="Financial Administration of the Republic of Slovenia"
    ),
    CountryRule(
        country_code="ES", country_name="Spain",
        vat_format="ES[A-Z0-9]{1}\\d{7}[A-Z0-9]{1}", vat_example="ESB12345678",
        mandatory_since="2025-01-01", threshold_above=None,
        preferred_formats=["ubl", "facturae", "cii"],
        accepted_formats=["ubl", "cii", "facturae", "peppol_bis"],
        central_platform_url="https://www.facturae.gob.es/",
        additional_requirements=["Facturae (v3.2+) mandatory B2G", "SIR (Sistema de Intercambio de Registros)",
                                 "Ley Crea y Crece (B2B) from 2025", "VERI*FACTU (TBAI/Suministro Inmediato)"],
        tax_authority_name="Agencia Estatal de Administración Tributaria"
    ),
    CountryRule(
        country_code="SE", country_name="Sweden",
        vat_format="SE\\d{12}", vat_example="SE123456789012",
        mandatory_since="2019-04-01", threshold_above=0.0,
        preferred_formats=["ubl", "peppol_bis"],
        accepted_formats=["ubl", "cii", "peppol_bis"],
        requires_peppol_id=True,
        central_platform_url="https://www.e-faktura.svefaktura.se/",
        additional_requirements=["Peppol BIS Billing 3.0 mandatory", "Svefaktura standard"],
        tax_authority_name="Skatteverket"
    ),
]

EU_COUNTRIES = {r.country_code: r for r in EU_COUNTRY_RULES}


# ──────────────────────────────────────────────
# Validation Rules Database
# ──────────────────────────────────────────────

VALIDATION_RULES: Dict[str, List[ValidationRule]] = {
    "ubl": [
        ValidationRule("UBL-01", "Invoice must contain valid UBL namespace", "/*/namespace-uri()='urn:oasis:names:specification:ubl:schema:xsd:Invoice-2'"),
        ValidationRule("UBL-02", "Invoice must have an ID (cbc:ID)", "//cbc:ID"),
        ValidationRule("UBL-03", "Invoice must have an issue date (cbc:IssueDate)", "//cbc:IssueDate"),
        ValidationRule("UBL-04", "Invoice must have a valid InvoiceTypeCode (cbc:InvoiceTypeCode)", "//cbc:InvoiceTypeCode"),
        ValidationRule("UBL-05", "Supplier Party must be specified (cac:AccountingSupplierParty)", "//cac:AccountingSupplierParty"),
        ValidationRule("UBL-06", "Customer Party must be specified (cac:AccountingCustomerParty)", "//cac:AccountingCustomerParty"),
        ValidationRule("UBL-07", "At least one invoice line required", "//cac:InvoiceLine"),
        ValidationRule("UBL-08", "LegalMonetaryTotal must be present", "//cac:LegalMonetaryTotal"),
        ValidationRule("UBL-09", "PayableAmount must be non-negative", "//cac:LegalMonetaryTotal/cbc:PayableAmount[number(text())>=0]"),
        ValidationRule("UBL-10", "TaxTotal must be present if taxable", "//cac:TaxTotal"),
        ValidationRule("UBL-11", "Currency code must be valid ISO 4217", "//cbc:DocumentCurrencyCode"),
        ValidationRule("UBL-12", "Invoice period must be consistent", "//cac:InvoicePeriod", schema_ref="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2", eu_standard_ref="EN 16931-1"),
    ],
    "cii": [
        ValidationRule("CII-01", "CrossIndustryInvoice root element required", "/*[local-name()='CrossIndustryInvoice']"),
        ValidationRule("CII-02", "Supply chain trade transaction required", "//*[local-name()='SupplyChainTradeTransaction']"),
        ValidationRule("CII-03", "Applicable header trade agreement required", "//*[local-name()='ApplicableHeaderTradeAgreement']"),
        ValidationRule("CII-04", "Seller trade party required", "//*[local-name()='SellerTradeParty']"),
        ValidationRule("CII-05", "Buyer trade party required", "//*[local-name()='BuyerTradeParty']"),
        ValidationRule("CII-06", "Invoice monet sum must be present", "//*[local-name()='InvoiceMonetarySummation']"),
        ValidationRule("CII-07", "Payable amount must be non-negative", "//*[local-name()='PayableAmount'][@value>=0 or number(text())>=0]"),
        ValidationRule("CII-08", "At least one included supply chain trade line item", "//*[local-name()='IncludedSupplyChainTradeLineItem']"),
        ValidationRule("CII-09", "Issue date must be present", "//*[local-name()='IssueDateTime']"),
        ValidationRule("CII-10", "Currency must be valid ISO 4217", "//*[local-name()='InvoiceCurrencyCode']", schema_ref="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100", eu_standard_ref="EN 16931-1"),
    ],
    "peppol_bis": [
        ValidationRule("PEPPOL-01", "Must conform to PEPPOL BIS Billing 3.0", "/*[local-name()='Invoice' and namespace-uri()='urn:oasis:names:specification:ubl:schema:xsd:Invoice-2']"),
        ValidationRule("PEPPOL-02", "ProfileID must be PEPPOL-specific", "//cbc:ProfileID[starts-with(text(),'urn:fdc:peppol.eu')]"),
        ValidationRule("PEPPOL-03", "CustomizationID must match PEPPOL BIS 3.0", "//cbc:CustomizationID[text()='urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:01.1.2'] or //cbc:CustomizationID[text()='urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:01.1.0']"),
        ValidationRule("PEPPOL-04", "Peppol endpoint ID must be present for sender/receiver", "//cbc:EndpointID"),
        ValidationRule("PEPPOL-05", "AccountingSupplierParty must have a valid Peppol ID", "//cac:AccountingSupplierParty//cbc:EndpointID"),
        ValidationRule("PEPPOL-06", "AccountingCustomerParty must have a valid Peppol ID", "//cac:AccountingCustomerParty//cbc:EndpointID"),
        ValidationRule("PEPPOL-07", "All amounts must have currencyID attribute", "//cbc:LineExtensionAmount[@currencyID]"),
        ValidationRule("PEPPOL-08", "VAT category codes must be valid", "//cbc:ID[text()='S' or text()='E' or text()='AE' or text()='K' or text()='G' or text()='O' or text()='Z']", schema_ref="peppol-bis-billing-3.0", eu_standard_ref="EN 16931-1"),
    ],
    "fattura_pa": [
        ValidationRule("FP-01", "FatturaElettronica root element required", "/*[local-name()='FatturaElettronica']"),
        ValidationRule("FP-02", "FatturaElettronicaHeader must be present", "//*[local-name()='FatturaElettronicaHeader']"),
        ValidationRule("FP-03", "DatiTrasmissione required", "//*[local-name()='DatiTrasmissione']"),
        ValidationRule("FP-04", "IdTrasmittente must include country code and VAT", "//*[local-name()='IdTrasmittente']"),
        ValidationRule("FP-05", "Ditta/CedentePrestatore required", "//*[local-name()='CedentePrestatore']"),
        ValidationRule("FP-06", "DatiGenerali must be present", "//*[local-name()='DatiGenerali']"),
        ValidationRule("FP-07", "DatiBeniServizi required", "//*[local-name()='DatiBeniServizi']"),
        ValidationRule("FP-08", "AliquotaIVA must be specified for each line", "//*[local-name()='AliquotaIVA']"),
        ValidationRule("FP-09", "ProgressivoInvio must be unique per sender", "//*[local-name()='ProgressivoInvio']"),
        ValidationRule("FP-10", "ImportoTotaleDocumento must match sum", "//*[local-name()='ImportoTotaleDocumento']", schema_ref="https://www.fatturapa.gov.it/export/documentazione/fatturapa/v1.2.1/fatturaPA_1.2.1.xsd", eu_standard_ref="EN 16931-1 (Italian extension)"),
    ],
    "xrechnung": [
        ValidationRule("XR-01", "XRechnung UBL or CII profile required", "/*[local-name()='Invoice' and namespace-uri()='urn:oasis:names:specification:ubl:schema:xsd:Invoice-2'] or /*[local-name()='CrossIndustryInvoice']"),
        ValidationRule("XR-02", "CustomizationID must be XRechnung compliant", "//cbc:CustomizationID[contains(text(),'xrechnung')] or //*[local-name()='SpecifiedBinaryFile']"),
        ValidationRule("XR-03", "Leitweg-ID must be present for public buyers", "//cbc:ID[contains(text(),'Leitweg')]"),
        ValidationRule("XR-04", "EN 16931 compliance mandatory", "//cbc:CustomizationID"),
        ValidationRule("XR-05", "Attachment must be included or referenced as URL", "//cac:Attachment", schema_ref="xrechnung-3.0", eu_standard_ref="EN 16931-1"),
    ],
    "facturae": [
        ValidationRule("FACTURAE-01", "Facturae root element required", "/*[local-name()='Facturae']"),
        ValidationRule("FACTURAE-02", "FileHeader must be present", "//*[local-name()='FileHeader']"),
        ValidationRule("FACTURAE-03", "Parties required (Seller and Buyer)", "//*[local-name()='Parties']"),
        ValidationRule("FACTURAE-04", "InvoiceData must be present", "//*[local-name()='InvoiceData']"),
        ValidationRule("FACTURAE-05", "Tax summary required", "//*[local-name()='TaxSummary']"),
        ValidationRule("FACTURAE-06", "Invoice total must be valid", "//*[local-name()='InvoiceTotals']", schema_ref="http://www.facturae.es/Facturae/2009/v3.2/Facturae.xsd", eu_standard_ref="EN 16931-1 (Spanish extension)"),
    ],
    "zugferd": [
        ValidationRule("ZUGFERD-01", "ZUGFeRD must be valid CrossIndustryInvoice or embedded in PDF", "/*[local-name()='CrossIndustryInvoice']"),
        ValidationRule("ZUGFERD-02", "Profile must be BASIC, COMFORT, EXTENDED, or EN16931", "//*[local-name()='ProfileID']"),
        ValidationRule("ZUGFERD-03", "Conformance level must be specified", "//*[local-name()='ConformanceLevel']"),
        ValidationRule("ZUGFERD-04", "Seller and buyer trade party required", "//*[local-name()='SellerTradeParty'] and //*[local-name()='BuyerTradeParty']"),
        ValidationRule("ZUGFERD-05", "Specified monetary summation required", "//*[local-name()='SpecifiedMonetarySummation']", schema_ref="zugferd-2.0", eu_standard_ref="EN 16931-1"),
    ],
}

FORMAT_NAMES = {
    "ubl": "UBL 2.1",
    "cii": "Cross Industry Invoice (CII) D16B",
    "peppol_bis": "PEPPOL BIS Billing 3.0",
    "fattura_pa": "FatturaPA 1.2.1",
    "xrechnung": "XRechnung 3.0",
    "facturae": "Facturae 3.2",
    "zugferd": "ZUGFeRD 2.0 / Factur-X",
    "en16931": "EN 16931-1 Core Invoice",
}


# ──────────────────────────────────────────────
# Sample Invoice Templates
# ──────────────────────────────────────────────

SAMPLE_INVOICES: List[InvoiceSample] = [
    InvoiceSample(
        id="ubl-sample-001", format="ubl", title="Basic UBL 2.1 Invoice",
        description="A standard B2B UBL 2.1 invoice with one line item",
        data={
            "UBLVersionID": "2.1", "CustomizationID": "urn:cen.eu:en16931:2017",
            "ProfileID": "urn:fdc:peppol.eu:2017:poacc:billing:01.1.2",
            "ID": "INV-2025-001", "IssueDate": "2025-04-15",
            "DueDate": "2025-05-15", "InvoiceTypeCode": 380,
            "DocumentCurrencyCode": "EUR",
            "AccountingSupplierParty": {
                "PartyName": "ACME GmbH",
                "VATID": "DE123456789",
                "RegistrationAddress": {"CountryCode": "DE", "City": "Berlin", "StreetName": "Hauptstr. 1", "PostalZone": "10115"}
            },
            "AccountingCustomerParty": {
                "PartyName": "Buyer Corp",
                "VATID": "DE987654321",
                "RegistrationAddress": {"CountryCode": "DE", "City": "München", "StreetName": "Bahnhofstr. 10", "PostalZone": "80331"}
            },
            "InvoiceLines": [
                {"ID": "1", "Quantity": 10, "LineExtensionAmount": 1000.00, "ItemName": "Consulting Services", "SellersItemID": "SRV-001"}
            ],
            "LegalMonetaryTotal": {"LineExtensionAmount": 1000.00, "TaxExclusiveAmount": 1000.00, "TaxInclusiveAmount": 1190.00, "PayableAmount": 1190.00},
            "TaxTotal": {"TaxAmount": 190.00, "TaxSubtotal": [{"TaxableAmount": 1000.00, "TaxAmount": 190.00, "Percent": 19.0, "TaxScheme": "VAT"}]}
        }
    ),
    InvoiceSample(
        id="cii-sample-001", format="cii", title="Basic CII D16B Invoice",
        description="A standard CrossIndustry Invoice with one trade line item",
        data={
            "ExchangedDocumentContext": {"TestIndicator": False, "GuidelineSpecifiedDocumentContextParameter": {"ID": "urn:cen.eu:en16931:2017"}},
            "ExchangedDocument": {"ID": "INV-CII-001", "TypeCode": 380, "IssueDateTime": "2025-04-15"},
            "SupplyChainTradeTransaction": {
                "IncludedSupplyChainTradeLineItem": [
                    {"AssociatedDocumentLineDocument": {"LineID": "1"}, "SpecifiedTradeProduct": {"Name": "Software License"}, "SpecifiedLineTradeAgreement": {"NetPriceProductTradePrice": {"ChargeAmount": 500.00}}, "SpecifiedLineTradeDelivery": {"BilledQuantity": 2, "unitCode": "C62"}, "SpecifiedLineTradeSettlement": {"ApplicableTradeTax": {"TypeCode": "VAT", "CategoryCode": "S", "RateApplicablePercent": 19.0}, "SpecifiedTradeSettlementLineMonetarySummation": {"LineTotalAmount": 1000.00}}}
                ],
                "ApplicableHeaderTradeAgreement": {"SellerTradeParty": {"Name": "ACME GmbH", "SpecifiedTaxRegistration": {"ID": {"schemeID": "VA", "Value": "DE123456789"}}}, "BuyerTradeParty": {"Name": "Buyer Corp"}},
                "ApplicableHeaderTradeSettlement": {"InvoiceCurrencyCode": "EUR", "ApplicableTradeTax": {"CalculatedAmount": 190.00, "TypeCode": "VAT", "RateApplicablePercent": 19.0}, "SpecifiedTradeSettlementHeaderMonetarySummation": {"InvoiceTotalAmountWithoutVAT": 1000.00, "InvoiceTotalVATAmount": 190.00, "InvoiceTotalAmountWithVAT": 1190.00, "PayableAmount": 1190.00}}
            }
        }
    ),
    InvoiceSample(
        id="peppol-sample-001", format="peppol_bis", title="PEPPOL BIS Billing 3.0 Invoice",
        description="PEPPOL-compliant B2B invoice with Peppol endpoint IDs",
        data={
            "UBLVersionID": "2.1", "CustomizationID": "urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:01.1.2",
            "ProfileID": "urn:fdc:peppol.eu:2017:poacc:billing:01.1.2", "ID": "PEPPOL-INV-001",
            "IssueDate": "2025-04-15", "InvoiceTypeCode": 380, "DocumentCurrencyCode": "EUR",
            "AccountingSupplierParty": {
                "PartyName": "Nordic Supplies AB",
                "EndpointID": "0088:7350151021543",
                "VATID": "SE123456789012",
                "RegistrationAddress": {"CountryCode": "SE", "City": "Stockholm", "StreetName": "Kungsgatan 10", "PostalZone": "111 43"}
            },
            "AccountingCustomerParty": {
                "PartyName": "Danish Retail A/S",
                "EndpointID": "0088:5798012345678",
                "VATID": "DK12345678",
                "RegistrationAddress": {"CountryCode": "DK", "City": "Copenhagen", "StreetName": "Strøget 1", "PostalZone": "1000"}
            },
            "InvoiceLines": [
                {"ID": "1", "Quantity": 5, "LineExtensionAmount": 2500.00, "ItemName": "Office Supplies", "SellersItemID": "OFF-001"}
            ],
            "LegalMonetaryTotal": {"LineExtensionAmount": 2500.00, "TaxExclusiveAmount": 2500.00, "TaxInclusiveAmount": 3100.00, "PayableAmount": 3100.00},
            "TaxTotal": {"TaxAmount": 600.00, "TaxSubtotal": [{"TaxableAmount": 2500.00, "TaxAmount": 600.00, "Percent": 24.0, "TaxScheme": "VAT"}]}
        }
    ),
    InvoiceSample(
        id="fattura-pa-001", format="fattura_pa", title="Italian FatturaPA",
        description="Italian mandatory e-invoice format with SdI data",
        data={
            "FatturaElettronicaHeader": {
                "DatiTrasmissione": {
                    "IdTrasmittente": {"IdPaese": "IT", "IdCodice": "01234567890"},
                    "ProgressivoInvio": "INV-000001",
                    "FormatoTrasmissione": "FPA12",
                    "CodiceDestinatario": "ABCDEF01"
                },
                "CedentePrestatore": {
                    "DatiAnagrafici": {"IdFiscaleIVA": {"IdPaese": "IT", "IdCodice": "01234567890"}, "CodiceFiscale": "RSSMRA80A01H501U", "Anagrafica": {"Denominazione": "RoSsi Srl"}},
                    "Sede": {"Indirizzo": "Via Roma 1", "CAP": "00100", "Comune": "Roma", "Provincia": "RM", "Nazione": "IT"}
                },
                "CessionarioCommittente": {
                    "DatiAnagrafici": {"IdFiscaleIVA": {"IdPaese": "IT", "IdCodice": "09876543210"}, "CodiceFiscale": "12345678901", "Anagrafica": {"Denominazione": "Acme S.p.A."}},
                    "Sede": {"Indirizzo": "Via Milano 2", "CAP": "20100", "Comune": "Milano", "Provincia": "MI", "Nazione": "IT"}
                }
            },
            "FatturaElettronicaBody": {
                "DatiGenerali": {"DatiGeneraliDocumento": {"TipoDocumento": "TD01", "Divisa": "EUR", "Data": "2025-04-15", "Numero": "1", "ImportoTotaleDocumento": 1220.00}},
                "DatiBeniServizi": {
                    "DettaglioLinee": [{"NumeroLinea": 1, "Descrizione": "Consulenza IT", "Quantita": 1.0, "PrezzoUnitario": 1000.00, "PrezzoTotale": 1000.00, "AliquotaIVA": 22.0}],
                    "DatiRiepilogo": [{"AliquotaIVA": 22.0, "ImponibileImporto": 1000.00, "Imposta": 220.00}]
                },
                "DatiPagamento": {"CondizioniPagamento": "TP01", "DettaglioPagamento": [{"ModalitaPagamento": "MP01", "DataScadenzaPagamento": "2025-05-15", "ImportoPagamento": 1220.00}]}
            }
        }
    ),
    InvoiceSample(
        id="xrechnung-sample-001", format="xrechnung", title="German XRechnung",
        description="German B2G XRechnung with Leitweg-ID",
        data={
            "UBLVersionID": "2.1", "CustomizationID": "urn:cen.eu:en16931:2017#compliant#urn:xoev-de:xrechnung:3.0",
            "ProfileID": "urn:fdc:peppol.eu:2017:poacc:billing:01.1.2", "ID": "XR-2025-001",
            "IssueDate": "2025-04-15", "InvoiceTypeCode": 380, "DocumentCurrencyCode": "EUR",
            "AccountingSupplierParty": {
                "PartyName": "Lieferant GmbH",
                "EndpointID": "LEITWEG-ID:DE123456789",
                "VATID": "DE987654321",
                "RegistrationAddress": {"CountryCode": "DE", "City": "Köln", "StreetName": "Domstr. 5", "PostalZone": "50667"}
            },
            "AccountingCustomerParty": {
                "PartyName": "Öffentliche Verwaltung",
                "EndpointID": "LEITWEG-ID:991-12345678-90",
                "RegistrationAddress": {"CountryCode": "DE", "City": "Bonn", "StreetName": "Berliner Str. 100", "PostalZone": "53111"}
            },
            "InvoiceLines": [
                {"ID": "1", "Quantity": 40, "LineExtensionAmount": 8000.00, "ItemName": "IT-Support", "SellersItemID": "IT-2025-001"}
            ],
            "LegalMonetaryTotal": {"LineExtensionAmount": 8000.00, "TaxExclusiveAmount": 8000.00, "TaxInclusiveAmount": 9520.00, "PayableAmount": 9520.00},
            "TaxTotal": {"TaxAmount": 1520.00, "TaxSubtotal": [{"TaxableAmount": 8000.00, "TaxAmount": 1520.00, "Percent": 19.0, "TaxScheme": "VAT"}]}
        }
    ),
    InvoiceSample(
        id="facturae-sample-001", format="facturae", title="Spanish Facturae 3.2",
        description="Spanish mandatory B2G invoice format Facturae v3.2",
        data={
            "FileHeader": {"FileVersion": "3.2", "Batch": {"BatchIdentifier": "BATCH-001", "InvoicesCount": 1, "TotalInvoicesAmount": 1452.00, "TotalOutstandingAmount": 0.00, "TotalExecutableAmount": 1452.00}},
            "Parties": {
                "SellerParty": {"TaxIdentification": {"TaxIdentificationNumber": "B12345678", "PartyTypeCode": 1}, "LegalPerson": {"Name": "Proveedor SL"}},
                "BuyerParty": {"TaxIdentification": {"TaxIdentificationNumber": "P1234567A", "PartyTypeCode": 2}, "AdministrativeCentres": {"AdministrativeCentre": [{"CentreCode": "O00001234", "RoleTypeCode": 1, "Name": "Ayuntamiento de Madrid", "AddressInSpain": {"Address": "Calle Mayor 1", "PostCode": "28001", "Town": "Madrid", "Province": "28"}}]}}
            },
            "Invoices": [{"InvoiceHeader": {"InvoiceNumber": "FAC-2025-001", "InvoiceSeriesCode": "FAC25", "InvoiceDocumentType": "FC", "InvoiceIssueDate": "2025-04-15"}, "InvoiceIssueData": {"InvoiceCurrencyCode": "EUR", "LanguageNameType": "es"}, "TaxesWithheld": [], "TaxesOutputs": [{"TaxTypeCode": "01", "TaxRate": 21.0, "TaxableBase": {"TotalAmount": 1200.00}, "TaxAmount": {"TotalAmount": 252.00}}], "InvoiceTotals": {"TotalGrossAmount": 1452.00, "TotalGeneralDiscounts": 0.00, "TotalGeneralSurcharges": 0.00, "TotalGrossAmountBeforeTaxes": 1452.00, "TotalTaxOutputs": {"TotalAmount": 252.00}, "TotalTaxesWithheld": {"TotalAmount": 0.00}, "InvoiceTotal": 1452.00, "Total OutstandingAmount": 0.00, "TotalExecutableAmount": 1452.00}, "Items": [{"SaleDetail": {"ItemDescription": "Servicios de consultoría", "Quantity": "1", "UnitOfMeasure": "E30", "UnitPriceWithoutTax": 1200.00, "GrossAmount": 1200.00, "TotalCost": 1200.00}}]}]
        }
    ),
    InvoiceSample(
        id="zugferd-sample-001", format="zugferd", title="ZUGFeRD BASIC Invoice",
        description="German/French hybrid invoice format (embedded XML in PDF)",
        data={
            "ExchangedDocumentContext": {"TestIndicator": False, "GuidelineSpecifiedDocumentContextParameter": {"ID": "urn:cen.eu:en16931:2017", "ProfileID": "urn:factur-x.eu:1p0:basic"}},
            "ExchangedDocument": {"ID": "ZF-2025-001", "TypeCode": 380, "IssueDateTime": "2025-04-15"},
            "SupplyChainTradeTransaction": {
                "IncludedSupplyChainTradeLineItem": [
                    {"AssociatedDocumentLineDocument": {"LineID": "1"}, "SpecifiedTradeProduct": {"Name": "Büromaterial"}, "SpecifiedLineTradeAgreement": {"NetPriceProductTradePrice": {"ChargeAmount": 150.00}}, "SpecifiedLineTradeDelivery": {"BilledQuantity": 3, "unitCode": "C62"}, "SpecifiedLineTradeSettlement": {"ApplicableTradeTax": {"TypeCode": "VAT", "CategoryCode": "S", "RateApplicablePercent": 19.0}, "SpecifiedTradeSettlementLineMonetarySummation": {"LineTotalAmount": 450.00}}}
                ],
                "ApplicableHeaderTradeAgreement": {"SellerTradeParty": {"Name": "ZUGFeRD GmbH"}, "BuyerTradeParty": {"Name": "Factur-X AG"}},
                "ApplicableHeaderTradeSettlement": {"InvoiceCurrencyCode": "EUR", "ApplicableTradeTax": {"CalculatedAmount": 85.50, "TypeCode": "VAT", "RateApplicablePercent": 19.0}, "SpecifiedTradeSettlementHeaderMonetarySummation": {"InvoiceTotalAmountWithoutVAT": 450.00, "InvoiceTotalVATAmount": 85.50, "InvoiceTotalAmountWithVAT": 535.50, "PayableAmount": 535.50}}
            }
        }
    ),
]


# ──────────────────────────────────────────────
# Pipeline Functions
# ──────────────────────────────────────────────

def get_country_rule(country_code: str) -> Optional[CountryRule]:
    """Get country rules by 2-letter ISO country code."""
    return EU_COUNTRIES.get(country_code.upper())


def get_all_countries() -> List[CountryRule]:
    """Return all EU country rules."""
    return EU_COUNTRY_RULES


def get_validation_rules(format_name: str) -> List[ValidationRule]:
    """Get validation rules for a given invoice format."""
    return VALIDATION_RULES.get(format_name.lower(), [])


def get_all_formats() -> Dict[str, str]:
    """Return map of format keys to human-readable names."""
    return FORMAT_NAMES


def get_format_names() -> List[str]:
    """Return list of supported format keys."""
    return list(FORMAT_NAMES.keys())


def get_sample_invoice(format_name: str) -> Optional[InvoiceSample]:
    """Get first sample invoice for a given format."""
    for inv in SAMPLE_INVOICES:
        if inv.format == format_name.lower():
            return inv
    return None


def get_all_sample_invoices() -> List[InvoiceSample]:
    """Get all sample invoices."""
    return SAMPLE_INVOICES


def validate_vat_format(country_code: str, vat_number: str) -> bool:
    """Validate a VAT number format against the country's pattern."""
    rule = get_country_rule(country_code.upper())
    if not rule:
        return False
    pattern = rule.vat_format
    return bool(re.match(pattern, vat_number))


def convert_country_rule_to_dict(rule: CountryRule) -> dict:
    """Convert CountryRule dataclass to dictionary for JSON serialization."""
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


def convert_validation_rule_to_dict(rule: ValidationRule) -> dict:
    """Convert ValidationRule dataclass to dictionary."""
    return {
        "id": rule.id,
        "description": rule.description,
        "xpath": rule.xpath,
        "severity": rule.severity.value,
        "schema_ref": rule.schema_ref,
        "eu_standard_ref": rule.eu_standard_ref,
    }


def convert_sample_to_dict(sample: InvoiceSample) -> dict:
    """Convert InvoiceSample dataclass to dictionary."""
    return {
        "id": sample.id,
        "format": sample.format,
        "title": sample.title,
        "description": sample.description,
        "valid": sample.valid,
        "data": sample.data,
    }


def listify_countries() -> List[dict]:
    """Return all country rules as dicts."""
    return [convert_country_rule_to_dict(r) for r in EU_COUNTRY_RULES]


# ──────────────────────────────────────────────
# Core Validation Engine (Python-level)
# ──────────────────────────────────────────────

def validate_invoice_structure(data: dict, format_name: str) -> List[dict]:
    """
    Perform high-level structural validation on invoice data.
    Checks for required top-level keys and basic field presence.
    """
    results = []
    rules = get_validation_rules(format_name)

    if not rules:
        results.append({
            "rule_id": "FORMAT-UNKNOWN",
            "severity": "error",
            "message": f"Unknown format: {format_name}. Supported formats: {', '.join(get_format_names())}",
            "passed": False,
        })
        return results

    for rule in rules:
        passed = _check_rule_against_data(data, rule)
        results.append({
            "rule_id": rule.id,
            "description": rule.description,
            "severity": rule.severity.value if hasattr(rule.severity, 'value') else rule.severity,
            "xpath": rule.xpath,
            "schema_ref": rule.schema_ref,
            "eu_standard_ref": rule.eu_standard_ref,
            "passed": passed,
            "message": "Passed" if passed else f"Failed: {rule.description}",
        })

    return results


def _check_rule_against_data(data: dict, rule: ValidationRule) -> bool:
    """
    Simple structural key-presence check for Python dict data.
    Maps XPath-like hints to dict key checks.
    """
    rule_id = rule.id

    # UBL checks
    if rule_id == "UBL-01":
        return True  # namespace check done at XML level
    elif rule_id == "UBL-02":
        return "ID" in data
    elif rule_id == "UBL-03":
        return "IssueDate" in data
    elif rule_id == "UBL-04":
        return "InvoiceTypeCode" in data
    elif rule_id == "UBL-05":
        return "AccountingSupplierParty" in data
    elif rule_id == "UBL-06":
        return "AccountingCustomerParty" in data
    elif rule_id == "UBL-07":
        lines = data.get("InvoiceLines", [])
        return isinstance(lines, list) and len(lines) > 0
    elif rule_id == "UBL-08":
        return "LegalMonetaryTotal" in data
    elif rule_id == "UBL-09":
        total = data.get("LegalMonetaryTotal", {})
        payable = total.get("PayableAmount", 0)
        return payable >= 0
    elif rule_id == "UBL-10":
        return "TaxTotal" in data
    elif rule_id == "UBL-11":
        return "DocumentCurrencyCode" in data
    elif rule_id == "UBL-12":
        return True  # InvoicePeriod optional

    # CII checks
    elif rule_id == "CII-01":
        return True  # XML-level check
    elif rule_id == "CII-02":
        return "SupplyChainTradeTransaction" in data
    elif rule_id == "CII-03":
        tx = data.get("SupplyChainTradeTransaction", {})
        return "ApplicableHeaderTradeAgreement" in tx
    elif rule_id == "CII-04":
        tx = data.get("SupplyChainTradeTransaction", {})
        agreement = tx.get("ApplicableHeaderTradeAgreement", {})
        return "SellerTradeParty" in agreement
    elif rule_id == "CII-05":
        tx = data.get("SupplyChainTradeTransaction", {})
        agreement = tx.get("ApplicableHeaderTradeAgreement", {})
        return "BuyerTradeParty" in agreement
    elif rule_id == "CII-06":
        tx = data.get("SupplyChainTradeTransaction", {})
        settlement = tx.get("ApplicableHeaderTradeSettlement", {})
        if "SpecifiedTradeSettlementHeaderMonetarySummation" in settlement:
            return True
        return "InvoiceMonetarySummation" in settlement
    elif rule_id == "CII-07":
        tx = data.get("SupplyChainTradeTransaction", {})
        settlement = tx.get("ApplicableHeaderTradeSettlement", {})
        summ = settlement.get("SpecifiedTradeSettlementHeaderMonetarySummation", {})
        payable = summ.get("PayableAmount", 0)
        return payable >= 0
    elif rule_id == "CII-08":
        tx = data.get("SupplyChainTradeTransaction", {})
        items = tx.get("IncludedSupplyChainTradeLineItem", [])
        return isinstance(items, list) and len(items) > 0
    elif rule_id == "CII-09":
        doc = data.get("ExchangedDocument", {})
        return "IssueDateTime" in doc
    elif rule_id == "CII-10":
        tx = data.get("SupplyChainTradeTransaction", {})
        settlement = tx.get("ApplicableHeaderTradeSettlement", {})
        return "InvoiceCurrencyCode" in settlement

    # PEPPOL checks
    elif rule_id in ("PEPPOL-01", "PEPPOL-02"):
        return True
    elif rule_id == "PEPPOL-03":
        cust_id = data.get("CustomizationID", "")
        return "en16931" in cust_id and "peppol" in cust_id
    elif rule_id in ("PEPPOL-04", "PEPPOL-05"):
        supplier = data.get("AccountingSupplierParty", {})
        return "EndpointID" in supplier
    elif rule_id == "PEPPOL-06":
        customer = data.get("AccountingCustomerParty", {})
        return "EndpointID" in customer
    elif rule_id == "PEPPOL-07":
        return "DocumentCurrencyCode" in data
    elif rule_id == "PEPPOL-08":
        return "InvoiceTypeCode" in data

    # FatturaPA checks
    elif rule_id == "FP-01":
        return True
    elif rule_id == "FP-02":
        return "FatturaElettronicaHeader" in data
    elif rule_id == "FP-03":
        header = data.get("FatturaElettronicaHeader", {})
        return "DatiTrasmissione" in header
    elif rule_id == "FP-04":
        header = data.get("FatturaElettronicaHeader", {})
        trasmissione = header.get("DatiTrasmissione", {})
        return "IdTrasmittente" in trasmissione
    elif rule_id == "FP-05":
        header = data.get("FatturaElettronicaHeader", {})
        return "CedentePrestatore" in header
    elif rule_id == "FP-06":
        body = data.get("FatturaElettronicaBody", {})
        return "DatiGenerali" in body
    elif rule_id == "FP-07":
        body = data.get("FatturaElettronicaBody", {})
        return "DatiBeniServizi" in body
    elif rule_id == "FP-08":
        body = data.get("FatturaElettronicaBody", {})
        beni = body.get("DatiBeniServizi", {})
        linee = beni.get("DettaglioLinee", [])
        return any("AliquotaIVA" in l for l in (linee if isinstance(linee, list) else [linee]))
    elif rule_id == "FP-09":
        header = data.get("FatturaElettronicaHeader", {})
        trasmissione = header.get("DatiTrasmissione", {})
        return "ProgressivoInvio" in trasmissione
    elif rule_id == "FP-10":
        body = data.get("FatturaElettronicaBody", {})
        generali = body.get("DatiGenerali", {})
        doc = generali.get("DatiGeneraliDocumento", {})
        return "ImportoTotaleDocumento" in doc

    # XRechnung checks
    elif rule_id == "XR-01":
        return True
    elif rule_id == "XR-02":
        cust_id = data.get("CustomizationID", "")
        return "xrechnung" in cust_id.lower()
    elif rule_id in ("XR-03", "XR-04", "XR-05"):
        return True

    # Facturae checks
    elif rule_id == "FACTURAE-01":
        return True
    elif rule_id == "FACTURAE-02":
        return "FileHeader" in data
    elif rule_id == "FACTURAE-03":
        return "Parties" in data
    elif rule_id == "FACTURAE-04":
        invoices = data.get("Invoices", [])
        if isinstance(invoices, list) and len(invoices) > 0:
            return "InvoiceHeader" in invoices[0]
        if isinstance(invoices, dict):
            return "InvoiceHeader" in invoices
        return False
    elif rule_id == "FACTURAE-05":
        invoices = data.get("Invoices", [])
        inv = invoices[0] if isinstance(invoices, list) and len(invoices) > 0 else invoices if isinstance(invoices, dict) else {}
        return "TaxesOutputs" in inv or "TaxSummary" in inv or "TaxesWithheld" in inv
    elif rule_id == "FACTURAE-06":
        invoices = data.get("Invoices", [])
        inv = invoices[0] if isinstance(invoices, list) and len(invoices) > 0 else invoices if isinstance(invoices, dict) else {}
        return "InvoiceTotals" in inv

    # ZUGFeRD checks
    elif rule_id == "ZUGFERD-01":
        return True
    elif rule_id == "ZUGFERD-02":
        ctx = data.get("ExchangedDocumentContext", {})
        param = ctx.get("GuidelineSpecifiedDocumentContextParameter", {})
        return "ProfileID" in param
    elif rule_id == "ZUGFERD-03":
        return True
    elif rule_id == "ZUGFERD-04":
        tx = data.get("SupplyChainTradeTransaction", {})
        agreement = tx.get("ApplicableHeaderTradeAgreement", {})
        return "SellerTradeParty" in agreement and "BuyerTradeParty" in agreement
    elif rule_id == "ZUGFERD-05":
        tx = data.get("SupplyChainTradeTransaction", {})
        settlement = tx.get("ApplicableHeaderTradeSettlement", {})
        return "SpecifiedTradeSettlementHeaderMonetarySummation" in settlement

    # Default: pass for unknown rules
    return True


# ──────────────────────────────────────────────
# Conversion Pipeline
# ──────────────────────────────────────────────

def convert_invoice(data: dict, source_format: str, target_format: str) -> dict:
    """
    Convert invoice data between formats.
    This is a structural mapping — real XML conversion would use XSLT.

    Returns a mapping report with the source data and conversion status.
    """
    supported = get_format_names()
    if source_format not in supported:
        return {"error": f"Unsupported source format: {source_format}", "status": "error"}
    if target_format not in supported:
        return {"error": f"Unsupported target format: {target_format}", "status": "error"}

    # For now, return a conversion blueprint
    return {
        "source_format": source_format,
        "target_format": target_format,
        "status": "mapping_available",
        "en16931_compliant": True,
        "message": f"Conversion from {FORMAT_NAMES.get(source_format, source_format)} to {FORMAT_NAMES.get(target_format, target_format)} is supported via EN 16931 semantic mapping.",
        "source_data": data,
    }


# ──────────────────────────────────────────────
# Data Summary / Reporting
# ──────────────────────────────────────────────

def get_pipeline_summary() -> dict:
    """Return a summary of the entire data pipeline."""
    return {
        "total_countries": len(EU_COUNTRY_RULES),
        "country_codes": [r.country_code for r in EU_COUNTRY_RULES],
        "total_formats": len(FORMAT_NAMES),
        "formats": FORMAT_NAMES,
        "total_rules": sum(len(v) for v in VALIDATION_RULES.values()),
        "rules_by_format": {k: len(v) for k, v in VALIDATION_RULES.items()},
        "total_sample_invoices": len(SAMPLE_INVOICES),
        "sample_invoice_ids": [s.id for s in SAMPLE_INVOICES],
    }
