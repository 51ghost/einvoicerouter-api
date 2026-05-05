# E-Invoice Router API

**Validate, convert, and look up EU e-invoicing rules — all 27 member states, all major formats.**

Built for the EU Digital Single Market. Handles PEPPOL BIS Billing 3.0, UBL 2.1, Cross Industry Invoice (CII), XRechnung, FatturaPA, Facturae, and ZUGFeRD/Factur-X.

## ✨ Features

- **Validation** — Structural and semantic validation against format-specific schemas
- **Conversion** — Cross-format mapping via EN 16931 semantic model
- **Country Rules** — All 27 EU countries' e-invoicing mandates, VAT formats, thresholds
- **VAT Check** — Format validation for VAT numbers per country
- **Samples** — Curated sample invoices for every supported format
- **RapidAPI Ready** — Tiered pricing, API key auth, rate limiting, CORS

## 🚀 Quick Start

```bash
# Clone & install
git clone https://github.com/51ghost/einvoicerouter-api.git
cd einvoicerouter-api
pip install -r requirements.txt

# Run
python main.py

# Or with uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open **http://localhost:8000/docs** for interactive Swagger docs.

## 📦 Deployment

### Railway

```bash
railway login
railway init
railway up
```

Or set `RAILWAY_GIT_REPO_URL` to your fork in Railway dashboard.

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📡 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/health` | Health check & data pipeline status |
| `POST` | `/v1/validate` | Validate an e-invoice |
| `POST` | `/v1/convert` | Convert between formats |
| `GET` | `/v1/country/{code}` | Country e-invoicing rules |
| `GET` | `/v1/countries` | All 27 EU countries |
| `GET` | `/v1/formats` | Supported formats & rules |
| `GET` | `/v1/samples/{format}` | Sample invoice |
| `GET` | `/v1/samples` | All sample invoices |
| `GET` | `/v1/check-vat/{country}/{vat}` | Validate VAT format |

### Authentication

Pass your API key as the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/v1/health
```

## 📋 Supported Formats

| Key | Format | EN 16931 |
|-----|--------|----------|
| `ubl` | UBL 2.1 (Universal Business Language) | ✅ Core |
| `cii` | Cross Industry Invoice D16B | ✅ Core |
| `peppol_bis` | PEPPOL BIS Billing 3.0 | ✅ Compliant |
| `xrechnung` | XRechnung 3.0 (Germany) | ✅ Compliant |
| `fattura_pa` | FatturaPA 1.2.1 (Italy) | ✅ Extended |
| `facturae` | Facturae 3.2 (Spain) | ✅ Extended |
| `zugferd` | ZUGFeRD 2.0 / Factur-X | ✅ Compliant |

## 🗺️ EU Country Coverage

All 27 EU member states:

AT, BE, BG, HR, CY, CZ, DK, EE, FI, FR, DE, GR, HU, IE, IT, LV, LT, LU, MT, NL, PL, PT, RO, SK, SI, ES, SE

Each entry includes:
- VAT number format & example
- B2G mandate date & threshold
- Preferred & accepted formats
- Central platform URL
- PEPPOL & e-signature requirements
- Additional compliance notes

## 🧪 Example: Validate an Invoice

```bash
curl -X POST "http://localhost:8000/v1/validate" \
  -H "X-API-Key: dev-api-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "invoice": {
      "ID": "INV-001",
      "IssueDate": "2025-04-15",
      "InvoiceTypeCode": 380,
      "DocumentCurrencyCode": "EUR",
      "AccountingSupplierParty": {"PartyName": "Supplier GmbH", "VATID": "DE123456789"},
      "AccountingCustomerParty": {"PartyName": "Buyer AG"},
      "InvoiceLines": [{"ID": "1", "Quantity": 10, "LineExtensionAmount": 1000.00, "ItemName": "Services"}],
      "LegalMonetaryTotal": {"LineExtensionAmount": 1000.00, "TaxExclusiveAmount": 1000.00, "TaxInclusiveAmount": 1190.00, "PayableAmount": 1190.00},
      "TaxTotal": {"TaxAmount": 190.00, "TaxSubtotal": [{"TaxableAmount": 1000.00, "TaxAmount": 190.00, "Percent": 19.0, "TaxScheme": "VAT"}]}
    },
    "format": "ubl",
    "country": "DE"
  }'
```

## 📊 Built-in Dataset

The `data_pipeline.py` module includes a curated dataset of:

- **27** EU country rule profiles
- **7** format specifications with validation rules
- **~60** individual validation rules
- **8** sample invoice templates with real-world data
- VAT format regex patterns for all countries

## 📝 License

MIT — see LICENSE file.
