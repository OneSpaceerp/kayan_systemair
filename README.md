# kayan_systemair

**SystemAir Axial Fan Quotation & Pricing Application**

A custom Frappe/ERPNext v16 application developed by **Nest Software Development** for **Kayan for Import** — the Egyptian representative of SystemAir (Sweden).

## Features

- **SystemAir Item Creator**: Guided DocType that encodes the SystemAir type-key naming convention, auto-generates item codes, fetches list prices, and registers items in ERPNext.
- **Price List Data Management**: Excel import tool for Germany and Malaysia price lists (~9,000 rows) via background jobs.
- **Pricing Engine**: 16-step server-side formula chain replicating the Excel COST sheet exactly (EX price → discounts → shipping → CIF → customs → VAT → cost factors → margin → final EGP price).
- **Enhanced Quotation**: Standard ERPNext Quotation extended with per-line pricing breakdown, accessories, 7-state workflow, and branded PDF.

## Installation

```bash
bench get-app kayan_systemair https://github.com/nsd-eg/kayan_systemair
bench --site site.local install-app kayan_systemair
bench build
```

## Requirements

- Frappe v16
- ERPNext v16
- Python 3.11+
- openpyxl >= 3.1.0

## Roles

| Role | Description |
|------|-------------|
| SystemAir Sales User | Create fan items, create/submit quotations |
| SystemAir Sales Manager | Approve quotations, access all reports |
| SystemAir Admin | Manage price config, import price lists |

## Developer

**Nest Software Development**
- Website: https://nsd-eg.com
- Email: info@nsd-eg.com

## License

MIT
