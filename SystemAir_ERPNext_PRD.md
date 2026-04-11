# Kayan SystemAir — ERPNext Custom Application
## Product Requirements Document (PRD) v1.0
**App Name:** `kayan_systemair` | **ERPNext Version:** 16 | **Frappe Version:** 16 | **Date:** April 2026

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Project Context & Business Problem](#2-project-context--business-problem)
3. [Scope](#3-scope)
4. [SystemAir Fan Type-Key Standard](#4-systemair-fan-type-key-standard)
5. [Module 1 — SystemAir Item Creator](#5-module-1--systemair-item-creator)
6. [Module 2 — Price List Data Management](#6-module-2--price-list-data-management)
7. [Module 3 — Pricing Engine](#7-module-3--pricing-engine)
8. [Module 4 — Enhanced SystemAir Quotation](#8-module-4--enhanced-systemair-quotation)
9. [Custom Print Format](#9-custom-print-format)
10. [Data Model — DocTypes Summary](#10-data-model--doctypes-summary)
11. [Roles & Permissions](#11-roles--permissions)
12. [Custom Reports](#12-custom-reports)
13. [Complete File & Folder Structure](#13-complete-file--folder-structure)
14. [Key File Contents & Skeletons](#14-key-file-contents--skeletons)
15. [Technical Architecture](#15-technical-architecture)
16. [Installation & Data Migration](#16-installation--data-migration)
17. [Testing Requirements](#17-testing-requirements)
18. [Implementation Plan](#18-implementation-plan)
19. [Open Questions](#19-open-questions)
20. [Appendix — Formula Reference & Glossary](#20-appendix--formula-reference--glossary)

---

## 1. Executive Summary

Kayan for Import is an Egyptian trading company representing **SystemAir** (Sweden) in the local and regional market. They run **ERPNext v16** as their primary ERP.

The SystemAir axial fan sales team currently works **entirely in Excel** for quotations. This project replaces that workflow with a custom ERPNext v16 application — `kayan_systemair` — introducing:

- **SystemAir Item Creator**: A guided DocType that encodes the Systemair type-key naming convention, auto-generates the correct item code, fetches the list price, and registers the item in the ERPNext Item master.
- **SystemAir Pricing Engine**: A server-side Python module that replicates every formula in the team's Excel workbook — EX price, discounts, shipping, CIF, customs, VAT, cost factors, currency rate, margin — producing a fully audited, ERP-native quotation.
- **Enhanced Quotation Form**: The standard ERPNext Quotation extended with per-line pricing breakdown, accessories table, workflow approval, and a branded PDF print format.

### Success Criteria
- All SystemAir quotations created, approved, and converted to Sales Orders entirely inside ERPNext.
- Pricing engine output matches Excel to within ±0.01 EUR for any input set.
- New fan items registered in under 60 seconds.
- Zero re-entry of data from Quotation to Sales Order.

---

## 2. Project Context & Business Problem

### 2.1 Current (As-Is) Workflow

```
Customer Inquiry
      │
      ▼
Open Excel "000-Pricing Sheet 2026.xlsx"
      │
      ▼
Enter fan model names on COST sheet
      │  (VLOOKUP → Germany Price List ~6,800 rows → EX Price EUR)
      ▼
Manually enter: Discount, Qty, Customs %, Currency Rate, Margin %
      │
      ▼
Excel calculates:
  Basic EX Price = EX_Price × Qty × (1 - Discount)
  Shipping = Basic_EX_Price × 12%
  CIF = Final_EX_Price + Shipping
  Cost Factors = 1.05 × 1.07 = 1.1235
  VAT = 1.14
  Total Price = CIF × CF × (1+MG) × Rate × VAT × (1+Customs)
      │
      ▼
Export QUOTATION sheet as PDF → email customer
      │
      ▼
If approved → manually re-enter EVERYTHING in ERPNext
(Item, Quotation, Sales Order, Purchase Order)
```

### 2.2 Pain Points

| Pain Point | Description |
|---|---|
| No ERPNext item codes | Fan models not registered as Items — impossible to track stock, orders, or invoices |
| Dual data entry | All data entered in Excel AND ERPNext separately |
| No audit trail | Excel files emailed between team members; no version control or approval workflow |
| Formula errors | Complex nested formulas break when rows are inserted/deleted |
| Currency risk | Exchange rate manually typed each time — no link to ERPNext Currency Exchange |
| Reporting blind spot | Management cannot see SystemAir pipeline, win-rate, or margin in ERPNext |
| Price list drift | Germany/Malaysia price lists embedded in Excel — update requires manual copy-paste |

---

## 3. Scope

### 3.1 In-Scope (Phase 1)

- Custom Frappe app: `kayan_systemair`
- DocType: `SystemAir Fan Item` — guided item creation wizard
- DocType: `SystemAir Price Config` — global pricing parameters (Single DocType)
- DocType: `SystemAir Weight Table` — fan weight by nominal diameter
- DocType: `SystemAir Quotation Item` — child table with full pricing engine
- DocType: `SystemAir Accessory Item` — accessories child table
- Custom Quotation fields and layout via `Quotation` customization
- Price List Import Tool (custom Page)
- Custom Print Format: branded quotation PDF
- Custom Reports: Quotation Summary, Margin Analysis, Price List Viewer
- Roles: `SystemAir Sales User`, `SystemAir Sales Manager`, `SystemAir Admin`
- ERPNext workspace: `SystemAir`
- Fixtures: weight table, price config defaults, custom fields, roles

### 3.2 Out-of-Scope (Phase 1)

- Automated EUR/EGP rate fetch from external API
- Systemair API / WebSelect integration
- Purchase Order, Delivery Note, Invoice workflow modifications
- Fan aerodynamic performance curve lookup

---

## 4. SystemAir Fan Type-Key Standard

Every SystemAir fan model is identified by a structured code. The naming is defined in the Systemair installation manual and confirmed by the client.

### 4.1 Type-Key Pattern

```
{Fan_Model} {Nominal_Diameter}-{Num_Blades}/{Blade_Angle}°-{Num_Poles}({Smoke_Rating})-{Suffixes}
```

**Example:** `AXC 355-6/10°-2(B)-PV MC`

| Segment | Example Value | Meaning |
|---|---|---|
| Fan Model | `AXC` | Axial fan standard. Options: `AXC`, `AXR`, `AXS`, `AXCP`, `AXCPV`, `AJR`, `AJ8` |
| Nominal Diameter | `355` | Fan diameter in mm. Options: 315, 355, 400, 450, 500, 560, 630, 710, 800, 900, 1000, 1120, 1250, 1400, 1600 |
| Number of Blades | `6` | Integer count of impeller blades |
| Blade Angle | `10°` | Pitch angle in degrees |
| Number of Poles | `2` | Motor pole count: 2 (3000rpm), 4 (1500rpm), 6 (1000rpm), 8 (750rpm) |
| Smoke Rating | `(B)` | `(B)` = 300°C/120min, `(F)` = 400°C/120min. Omit for standard fans |
| `-PV` | Guide Vane | Optional: fan fitted with guide vane |
| `MC` | Medium Casing | Optional: fan supplied with medium casing |
| `-P` | Plus / New Gen | New impeller generation (also expressed as AXCP model) |
| `-TR` | Reversible | Airflow reversible (also expressed as AXR model) |
| `-G` | Series | Two fans in series |
| `-B` (box) | Insulated Box | Fan with insulated acoustic box |
| `-A` | Low Pressure | Low pressure impeller variant |

### 4.2 Fan Model Options (Select Field)

```
AXC    → Axial fan
AXR    → Axial fan — reversible
AXS    → Axial fan — ship
AXCP   → Axial fan — plus (new impeller generation)
AXCPV  → Axial fan — plus — guide vane
AJR    → Circular jet fan
AJ8    → Octagonal jet fan
DVAX   → Roof fan
```

### 4.3 Model Code Assembly Logic (Python)

```python
def assemble_model_code(doc):
    code = f"{doc.fan_model} {doc.nominal_diameter}"
    code += f"-{doc.num_blades}/{doc.blade_angle}°"
    code += f"-{doc.num_poles}"
    if doc.smoke_rating and doc.smoke_rating != "None":
        code += f"({doc.smoke_rating})"
    if doc.guide_vane:
        code += "-PV"
    if doc.medium_casing:
        code += " MC"
    if doc.config_suffix and doc.config_suffix != "None":
        code += doc.config_suffix
    if doc.reversible:
        code += "-TR"
    return code
```

---

## 5. Module 1 — SystemAir Item Creator

### 5.1 DocType: `SystemAir Fan Item`

**Type:** Document (transactional wizard — on submit creates/links ERPNext Item)
**Module:** `kayan_systemair`
**Is Submittable:** Yes

#### Section A — Fan Model Attributes (Core Type-Key)

| Field Name | fieldname | fieldtype | Options | Required |
|---|---|---|---|---|
| Axial Fan Model | `fan_model` | Select | AXC\nAXR\nAXS\nAXCP\nAXCPV\nAJR\nAJ8\nDVAX | Yes |
| Nominal Fan Diameter (mm) | `nominal_diameter` | Select | 315\n355\n400\n450\n500\n560\n630\n710\n800\n900\n1000\n1120\n1250\n1400\n1600 | Yes |
| Number of Blades | `num_blades` | Int | — | Yes |
| Blade Angle (°) | `blade_angle` | Data | — | Yes |
| Number of Poles | `num_poles` | Select | 2\n4\n6\n8 | Yes |
| Smoke Rating | `smoke_rating` | Select | None\nB\nF | No |

#### Section B — Optional Suffixes

| Field Name | fieldname | fieldtype | Description |
|---|---|---|---|
| Guide Vane (PV) | `guide_vane` | Check | Appends `-PV` to model code |
| Plus / New Impeller | `plus_impeller` | Check | Used with AXCP/AXCPV only |
| Medium Casing (MC) | `medium_casing` | Check | Appends ` MC` to model code |
| Reversible (TR) | `reversible` | Check | Appends `-TR` to model code |
| Configuration Suffix | `config_suffix` | Select | None\n-G\n-B\n-A\n-P | No |

#### Section C — Auto-Generated & Lookup Fields (Read-Only)

| Field Name | fieldname | fieldtype | Description |
|---|---|---|---|
| Generated Model Code | `model_code` | Data | Auto-assembled, read-only |
| Item Already Exists | `item_exists` | Check | Set by system after lookup |
| Existing ERPNext Item | `erp_item` | Link → Item | Populated if item found |
| Germany List Price (EUR) | `germany_price` | Currency | VLOOKUP from Germany Price List |
| Malaysia List Price (EUR) | `malaysia_price` | Currency | VLOOKUP from Malaysia Price List |
| Fan Family / Product Group | `product_group` | Data | From price list lookup |
| Primary Factory | `primary_factory` | Data | e.g. Germany, Sweden, Malaysia |
| Approx. Weight (kg) | `approx_weight` | Float | From weight table by diameter |

#### Section D — Technical Performance Data

| Field Name | fieldname | fieldtype | Description |
|---|---|---|---|
| Airflow (l/s) | `airflow_ls` | Float | Airflow at duty point |
| ESP (Pa) | `esp_pa` | Float | External static pressure |
| Input Power (kW) | `input_power_kw` | Float | Nominal shaft power |
| Speed (rpm) | `speed_rpm` | Int | Motor speed |
| Fan Type Description | `fan_type_desc` | Data | e.g. Axial Inline, Wall Mounted |
| Origin | `origin` | Data | Country of manufacture |

### 5.2 Item Lookup & Creation Flow

```
User saves SystemAir Fan Item
        │
        ▼
assemble_model_code() → model_code
        │
        ▼
frappe.db.get_value("Item", {"item_code": model_code})
        │
     ┌──┴──┐
   Found  Not Found
     │        │
     ▼        ▼
item_exists  Show "New Item" banner
= True       Create Item button visible
Link item    ──────────────────────────
             On click → create_item()
             Sets: item_code, item_name,
             item_group="SystemAir Axial Fans",
             stock_uom="Nos",
             is_purchase_item=1,
             is_sales_item=1,
             + all custom sa_ fields
```

### 5.3 Custom Fields on ERPNext Item DocType

These fields are added to the standard `Item` DocType via Fixtures:

| fieldname | fieldtype | Label |
|---|---|---|
| `sa_nominal_diameter` | Select | SA: Nominal Diameter (mm) |
| `sa_num_blades` | Int | SA: Number of Blades |
| `sa_blade_angle` | Data | SA: Blade Angle (°) |
| `sa_num_poles` | Select | SA: Number of Poles |
| `sa_smoke_rating` | Select | SA: Smoke Rating |
| `sa_weight_kg` | Float | SA: Approx. Weight (kg) |
| `sa_article_no` | Data | SA: Article No. (Systemair) |
| `sa_product_family` | Data | SA: Product Family |
| `sa_primary_factory` | Data | SA: Primary Factory |

---

## 6. Module 2 — Price List Data Management

### 6.1 ERPNext Price Lists (Created on Install)

| Price List Name | Currency | Source | Item Count |
|---|---|---|---|
| `Systemair Germany 2026` | EUR | `Price List.xlsx` → Sheet "Germany" | ~8,300 rows |
| `Systemair Malaysia 2026` | EUR | `Price List.xlsx` → Sheet "Box,Jet MY" | ~782 rows |

### 6.2 Price List Import Tool

**Page:** `kayan_systemair/page/price_list_import/`

Features:
- `.xlsx` file upload widget
- Auto-detect sheet (Germany / Malaysia)
- Map columns: `item_name` → `Item.item_name`, `sales_price` → `Item Price.price_list_rate`
- Preview table (first 20 rows) before import
- Background job import (`frappe.enqueue`)
- Creates/updates `Item Price` records in bulk
- Import log: timestamp, user, records created/updated/skipped

### 6.3 Price Fetch Logic

```python
def get_list_price(model_code, price_list="Systemair Germany 2026"):
    # Exact match
    price = frappe.db.get_value(
        "Item Price",
        {"item_code": model_code, "price_list": price_list, "selling": 1},
        "price_list_rate"
    )
    if price:
        return price
    # Fuzzy fallback — search by item_name
    results = frappe.db.sql("""
        SELECT ip.item_code, ip.price_list_rate, i.item_name
        FROM `tabItem Price` ip
        JOIN `tabItem` i ON i.item_code = ip.item_code
        WHERE ip.price_list = %s
          AND i.item_name LIKE %s
        LIMIT 10
    """, (price_list, f"%{model_code}%"), as_dict=True)
    return results  # Return list for user selection dialog
```

### 6.4 SystemAir Weight Table (DocType: `SystemAir Weight Table`)

Single DocType (non-submittable master) loaded from fixture:

| Nominal Diameter (mm) | Min Weight (kg) | Max Weight (kg) |
|---|---|---|
| 315 | 40 | 57 |
| 355 | 40 | 57 |
| 400 | 45 | 62 |
| 450 | 52 | 84 |
| 500 | 52 | 107 |
| 560 | 58 | 112 |
| 630 | 93 | 160 |
| 710 | 100 | 200 |
| 800 | 100 | 287 |
| 900 | 163 | 343 |
| 1000 | 100 | 287 |
| 1120 | 281 | 557 |
| 1250 | 336 | 667 |
| 1400 | 511 | 778 |
| 1600 | 545 | 1792 |

> **Note:** Shipping cost uses `max_weight_kg`. Admin can override any value.

---

## 7. Module 3 — Pricing Engine

### 7.1 DocType: `SystemAir Price Config` (Single DocType)

| fieldname | fieldtype | Default | Label |
|---|---|---|---|
| `vat_rate` | Percent | 14 | VAT Rate (%) |
| `cost_factor_1` | Float | 1.05 | Cost Factor 1 (Overhead) |
| `cost_factor_2` | Float | 1.07 | Cost Factor 2 (Finance) |
| `combined_cost_factor` | Float | 1.1235 | Combined Cost Factor (CF1 × CF2) — Read-only |
| `default_shipping_rate` | Percent | 12 | Default Shipping Rate (%) |
| `default_margin` | Percent | 50 | Default Margin % (MG) |
| `default_currency_rate` | Float | — | Default EUR→EGP Rate |
| `default_customs_rate` | Percent | 0 | Default Customs Duty Rate (%) |

### 7.2 Complete Pricing Formula Chain

Extracted from `000-Pricing Sheet 2026.xlsx`, COST sheet, columns L–AB:

| Step | Field | Formula | Excel Col | Notes |
|---|---|---|---|---|
| 1 | `ex_price` | From Germany/Malaysia price list VLOOKUP | L, M | Auto-fetched; user can override |
| 2 | `supplier_discount` | Manual entry (0.0–1.0) | N | e.g. 0.20 for 20% |
| 3 | `qty` | Standard ERPNext qty field | O | Integer |
| 4 | `basic_ex_price` | `ex_price × qty × (1 − supplier_discount)` | P | Pre-discount extended price |
| 5 | `additional_discount` | Optional second-level discount | Q | Can be 0 |
| 6 | `final_ex_price` | `basic_ex_price × (1 − additional_discount)` | R | Net EX price |
| 7 | `shipping_cost` | `basic_ex_price × shipping_rate` (default 12%) | S | CIF shipping estimate |
| 8 | `cif` | `final_ex_price + shipping_cost` | T | Cost Insurance Freight |
| 9 | `cost_factors` | `CF1 × CF2 = 1.05 × 1.07 = 1.1235` | W | Fixed; from Price Config |
| 10 | `customs_rate` | Manual entry per item | U | Egypt import customs tariff |
| 11 | `vat_multiplier` | `1 + vat_rate` → `1.14` | V | Egyptian VAT; from Price Config |
| 12 | `currency_rate` | EUR→EGP rate from quotation header | X | Overrides Price Config default |
| 13 | `ddp_cost` | `cif × cost_factors × currency_rate × vat_multiplier × (1 + customs_rate)` | Y | Dry DDP landed cost |
| 14 | `margin` | Configurable per item (default 50%) | Z | Sales margin over landed cost |
| 15 | `total_price` | `cif × cost_factors × (1 + margin) × currency_rate × vat_multiplier × (1 + customs_rate)` | AB | Final selling price for qty |
| 16 | `unit_price` | `total_price / qty` | AA | Per-unit selling price → ERPNext `rate` |

### 7.3 Pricing Engine Python Implementation

```python
# kayan_systemair/kayan_systemair/doctype/systemair_quotation_item/pricing_engine.py

import frappe
from frappe.utils import flt

def compute_pricing(item_row, quotation_doc):
    """
    Replicates all 16 steps of the Excel COST sheet pricing formula chain.
    Called from SystemAir Quotation Item.before_save() and
    Quotation.before_save() for all SA items.
    """
    cfg = frappe.get_single("SystemAir Price Config")

    # --- Inputs ---
    ex_price           = flt(item_row.ex_price)
    qty                = flt(item_row.qty) or 1
    supplier_discount  = flt(item_row.supplier_discount) / 100
    additional_discount= flt(item_row.additional_discount) / 100
    customs_rate       = flt(item_row.customs_rate) / 100
    margin             = flt(item_row.margin_percent) / 100
    shipping_rate      = flt(quotation_doc.sa_shipping_rate or cfg.default_shipping_rate) / 100
    currency_rate      = flt(quotation_doc.sa_eur_egp_rate or cfg.default_currency_rate) or 1
    cost_factors       = flt(cfg.cost_factor_1) * flt(cfg.cost_factor_2)
    vat_multiplier     = 1 + (flt(cfg.vat_rate) / 100)

    # --- Steps 4–16 ---
    basic_ex_price      = ex_price * qty * (1 - supplier_discount)       # Step 4
    final_ex_price      = basic_ex_price * (1 - additional_discount)     # Step 6
    shipping_cost       = basic_ex_price * shipping_rate                  # Step 7
    cif                 = final_ex_price + shipping_cost                  # Step 8
    ddp_cost            = (cif * cost_factors * currency_rate
                           * vat_multiplier * (1 + customs_rate))        # Step 13
    total_price         = (cif * cost_factors * (1 + margin)
                           * currency_rate * vat_multiplier
                           * (1 + customs_rate))                          # Step 15
    unit_price          = total_price / qty if qty else 0                 # Step 16

    # --- Write back to item row ---
    item_row.basic_ex_price     = basic_ex_price
    item_row.final_ex_price     = final_ex_price
    item_row.shipping_cost      = shipping_cost
    item_row.cif                = cif
    item_row.ddp_cost           = ddp_cost
    item_row.unit_price_egp     = unit_price
    item_row.total_price_egp    = total_price
    item_row.rate               = unit_price   # standard ERPNext rate field
    item_row.amount             = total_price  # standard ERPNext amount field

    return item_row
```

### 7.4 Margin Color Indicator (Client-Side JS)

```javascript
// Green  ≥ 40%
// Amber  25% – 39%
// Red    < 25%
function get_margin_color(margin_pct) {
    if (margin_pct >= 40) return "green";
    if (margin_pct >= 25) return "orange";
    return "red";
}
```

---

## 8. Module 4 — Enhanced SystemAir Quotation

### 8.1 Quotation Header — Custom Fields Added

| fieldname | fieldtype | Label | Default | Required | Editable |
|---|---|---|---|---|---|
| `is_systemair_quotation` | Check | Is SystemAir Quotation | 0 | No | Yes |
| `sa_project_ref` | Data | Project Reference | — | No | Yes |
| `sa_eur_egp_rate` | Float | EUR/EGP Exchange Rate | from Config | No | Yes |
| `sa_default_customs` | Percent | Default Customs Duty % | 0 | No | Yes |
| `sa_default_discount` | Percent | Default Supplier Discount % | 0 | No | Yes |
| `sa_additional_discount` | Percent | Default Additional Discount % | 0 | No | Yes |
| `sa_default_margin` | Percent | Default Margin % | 50 | No | Yes |
| `sa_shipping_rate` | Percent | Shipping Rate % | 12 | No | Yes |
| `sa_total_cif_eur` | Currency | Total CIF (EUR) | auto-calc | No | No |
| `sa_grand_total_egp` | Currency | Grand Total (EGP) | auto-calc | No | No |
| `sa_effective_margin` | Percent | Effective Margin % | auto-calc | No | No |

### 8.2 SystemAir Quotation Item — Child Table Fields

**DocType:** `SystemAir Quotation Item`
**Parent:** `Quotation` (field: `sa_items`)

| fieldname | fieldtype | Label | Required | Read-Only |
|---|---|---|---|---|
| `sa_sn` | Data | Fan Reference (SN) | No | No |
| `location` | Data | Location / Tag | No | No |
| `fan_type` | Select | Fan Type | No | No |
| `speed_type` | Select | Speed | No | No |
| `smoke_rating` | Select | Smoke Rating | No | No |
| `sa_article_no` | Data | Article No. | No | No |
| `item_code` | Link → Item | Model (Item) | Yes | No |
| `item_name` | Data | Item Name | No | Yes |
| `airflow_ls` | Float | Airflow (l/s) | No | No |
| `esp_pa` | Float | ESP (Pa) | No | No |
| `qty` | Float | Qty | Yes | No |
| `germany_list_price` | Currency | Germany List Price (EUR) | No | Yes |
| `malaysia_list_price` | Currency | Malaysia List Price (EUR) | No | Yes |
| `ex_price` | Currency | EX Price (EUR) | Yes | No |
| `supplier_discount` | Percent | Supplier Discount % | No | No |
| `additional_discount` | Percent | Additional Discount % | No | No |
| `customs_rate` | Percent | Customs Duty % | No | No |
| `margin_percent` | Percent | Margin % (MG) | No | No |
| `approx_weight_kg` | Float | Approx. Weight (kg) | No | No |
| `basic_ex_price` | Currency | Basic EX Price (EUR) | No | Yes |
| `shipping_cost` | Currency | Shipping Cost (EUR) | No | Yes |
| `final_ex_price` | Currency | Final EX Price (EUR) | No | Yes |
| `cif` | Currency | CIF (EUR) | No | Yes |
| `ddp_cost` | Currency | DDP Cost (EUR) | No | Yes |
| `unit_price_egp` | Currency | Unit Price (EGP) | No | Yes |
| `total_price_egp` | Currency | Total Price (EGP) | No | Yes |
| `rate` | Currency | Rate (standard) | No | Yes |
| `amount` | Currency | Amount (standard) | No | Yes |

### 8.3 SystemAir Accessory Item — Child Table Fields

**DocType:** `SystemAir Accessory Item`
**Parent:** `Quotation` (field: `sa_accessories`)

| fieldname | fieldtype | Label |
|---|---|---|
| `sa_article_no` | Data | Article No. |
| `item_code` | Link → Item | Item |
| `accessory_name` | Data | Accessory Name |
| `qty` | Float | Qty |
| `unit_price_eur` | Currency | Unit Price (EUR) |
| `total_price_egp` | Currency | Total Price (EGP) |

### 8.4 Quotation Workflow

**Workflow Name:** `SystemAir Quotation Workflow`
**DocType:** `Quotation`
**Condition:** `doc.is_systemair_quotation == 1`

| State | Style | Allow Edit |
|---|---|---|
| Draft | default | Yes |
| Pending Review | warning | Sales User only — read-only for others |
| Approved | success | Manager can edit margin/discount |
| Sent to Customer | primary | Read-only |
| Order Received | success | Read-only |
| Lost | danger | Reason field mandatory |
| Cancelled | secondary | No |

**Workflow Transitions:**

| Action | From | To | Role |
|---|---|---|---|
| Submit for Review | Draft | Pending Review | SystemAir Sales User |
| Approve | Pending Review | Approved | SystemAir Sales Manager |
| Reject | Pending Review | Draft | SystemAir Sales Manager |
| Mark Sent | Approved | Sent to Customer | SystemAir Sales User |
| Mark Won | Sent to Customer | Order Received | SystemAir Sales User |
| Mark Lost | Sent to Customer | Lost | SystemAir Sales User |
| Cancel | Any | Cancelled | SystemAir Sales Manager |

---

## 9. Custom Print Format

**Name:** `SystemAir Quotation`
**DocType:** `Quotation`
**Standard:** No (Jinja2 custom)

### Sections

1. **Header:** Kayan for Import letterhead, "QUOTATION" title, quotation number, date, validity
2. **Customer Details:** Name, address, attention, contact
3. **Project Info:** Project name, reference, subject
4. **Items Table:** SN | Location | Model | Fan Type | Speed | Smoke | Flow (l/s) | ESP (Pa) | Qty | Unit Price | Total
5. **Accessories Table:** (if accessories exist)
6. **Summary Box:** Total CIF (EUR) | Customs | VAT | Grand Total (EGP) | Exchange Rate used
7. **Footer:** T&C reference, validity, authorized signature block
8. **Internal Page** (toggled by `print_internal` check): Full pricing breakdown per item (Steps 1–16)

---

## 10. Data Model — DocTypes Summary

### 10.1 Custom DocTypes

| DocType | Type | Module | Purpose |
|---|---|---|---|
| `SystemAir Fan Item` | Document (Submittable) | kayan_systemair | Guided fan model registration wizard |
| `SystemAir Price Config` | Single | kayan_systemair | Global pricing parameters |
| `SystemAir Weight Table` | Document | kayan_systemair | Fan weight by nominal diameter |
| `SystemAir Quotation Item` | Child Table | kayan_systemair | Extended line-item with pricing engine |
| `SystemAir Accessory Item` | Child Table | kayan_systemair | Accessories line-item |
| `SystemAir Import Log` | Document | kayan_systemair | Price list import audit log |

### 10.2 Standard DocTypes Extended

| Standard DocType | Customization |
|---|---|
| `Item` | Custom fields: `sa_nominal_diameter`, `sa_num_blades`, `sa_blade_angle`, `sa_num_poles`, `sa_smoke_rating`, `sa_weight_kg`, `sa_article_no`, `sa_product_family`, `sa_primary_factory`. New Item Group: `SystemAir Axial Fans` |
| `Item Price` | No structural change. Two new Price Lists added on install |
| `Quotation` | Custom header fields (11 fields). Two new child table fields: `sa_items` → `SystemAir Quotation Item`, `sa_accessories` → `SystemAir Accessory Item`. Standard items table hidden when `is_systemair_quotation = 1` |

---

## 11. Roles & Permissions

### Custom Roles

| Role | Permissions |
|---|---|
| `SystemAir Sales User` | Create/edit SystemAir Fan Item. Create/submit Quotation (Draft, Pending Review). Read Price Config & Weight Table. |
| `SystemAir Sales Manager` | All Sales User permissions. Approve Quotations. Edit Margin/Discount/Customs at any state. Access all SA reports. |
| `SystemAir Admin` | All Manager permissions. Edit Price Config. Run Price List Import. Manage Weight Table. Delete documents. View Import Logs. |

### DocType Permission Matrix

| DocType | SA Sales User | SA Sales Manager | SA Admin |
|---|---|---|---|
| SystemAir Fan Item | R W C | R W C D | R W C D |
| SystemAir Price Config | R | R | R W |
| SystemAir Weight Table | R | R | R W C D |
| Quotation (SA) | R W C | R W C D | R W C D |
| SystemAir Import Log | — | R | R W C D |

> `R`=Read `W`=Write `C`=Create `D`=Delete

---

## 12. Custom Reports

| Report Name | Type | Description |
|---|---|---|
| `SystemAir Quotation Summary` | Script Report | All SA quotations: No., Date, Customer, Project, Status, Items, Total CIF (EUR), Grand Total (EGP), Effective Margin % |
| `Margin Analysis` | Script Report | Per-item margin breakdown: EX Price, Discount, CIF, Customs, DDP, Selling Price, Gross Margin, Margin % |
| `Systemair Price List Viewer` | Query Report | Side-by-side Germany vs Malaysia prices: Item Code, Name, Product Group, Germany (EUR), Malaysia (EUR), Factory, Updated |
| `Fan Weight Reference` | Query Report | SystemAir Weight Table reference |

---

## 13. Complete File & Folder Structure

```
kayan_systemair/                          ← Git repository root
│
├── kayan_systemair/                      ← Main Python package
│   │
│   ├── __init__.py                       ← App version: __version__ = "1.0.0"
│   ├── hooks.py                          ← Frappe hooks (app events, overrides)
│   ├── modules.txt                       ← "kayan_systemair"
│   ├── patches.txt                       ← Patch list (one patch per line)
│   ├── install.py                        ← Post-install setup script
│   ├── uninstall.py                      ← Pre-uninstall cleanup
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── desktop.py                    ← Workspace/desktop icon config (legacy)
│   │   └── docs.py                       ← Documentation config
│   │
│   ├── doctype/
│   │   ├── __init__.py
│   │   │
│   │   ├── systemair_fan_item/
│   │   │   ├── __init__.py
│   │   │   ├── systemair_fan_item.json   ← DocType schema definition
│   │   │   ├── systemair_fan_item.py     ← Controller (Python)
│   │   │   ├── systemair_fan_item.js     ← Client-side form script
│   │   │   └── test_systemair_fan_item.py
│   │   │
│   │   ├── systemair_price_config/
│   │   │   ├── __init__.py
│   │   │   ├── systemair_price_config.json
│   │   │   ├── systemair_price_config.py
│   │   │   ├── systemair_price_config.js
│   │   │   └── test_systemair_price_config.py
│   │   │
│   │   ├── systemair_weight_table/
│   │   │   ├── __init__.py
│   │   │   ├── systemair_weight_table.json
│   │   │   ├── systemair_weight_table.py
│   │   │   └── test_systemair_weight_table.py
│   │   │
│   │   ├── systemair_quotation_item/
│   │   │   ├── __init__.py
│   │   │   ├── systemair_quotation_item.json  ← Child table DocType
│   │   │   ├── systemair_quotation_item.py    ← compute_pricing() called here
│   │   │   ├── pricing_engine.py              ← Core pricing formula chain
│   │   │   └── test_systemair_quotation_item.py
│   │   │
│   │   ├── systemair_accessory_item/
│   │   │   ├── __init__.py
│   │   │   ├── systemair_accessory_item.json
│   │   │   ├── systemair_accessory_item.py
│   │   │   └── test_systemair_accessory_item.py
│   │   │
│   │   └── systemair_import_log/
│   │       ├── __init__.py
│   │       ├── systemair_import_log.json
│   │       └── systemair_import_log.py
│   │
│   ├── page/
│   │   └── price_list_import/
│   │       ├── __init__.py
│   │       ├── price_list_import.json    ← Page definition
│   │       ├── price_list_import.py      ← Server-side import logic + API endpoints
│   │       ├── price_list_import.js      ← Page JS (file upload, preview, import button)
│   │       └── price_list_import.html    ← Page template
│   │
│   ├── report/
│   │   ├── __init__.py
│   │   │
│   │   ├── systemair_quotation_summary/
│   │   │   ├── __init__.py
│   │   │   ├── systemair_quotation_summary.json
│   │   │   └── systemair_quotation_summary.py
│   │   │
│   │   ├── margin_analysis/
│   │   │   ├── __init__.py
│   │   │   ├── margin_analysis.json
│   │   │   └── margin_analysis.py
│   │   │
│   │   ├── systemair_price_list_viewer/
│   │   │   ├── __init__.py
│   │   │   ├── systemair_price_list_viewer.json
│   │   │   └── systemair_price_list_viewer.sql   ← Query Report SQL
│   │   │
│   │   └── fan_weight_reference/
│   │       ├── __init__.py
│   │       ├── fan_weight_reference.json
│   │       └── fan_weight_reference.sql
│   │
│   ├── workspace/
│   │   └── kayan_systemair/
│   │       ├── kayan_systemair.json      ← Workspace definition (ERPNext v16 format)
│   │       └── kayan_systemair.py
│   │
│   ├── custom/
│   │   ├── __init__.py
│   │   └── quotation.py                 ← Quotation controller overrides (hooks)
│   │
│   ├── print_format/
│   │   └── systemair_quotation/
│   │       ├── systemair_quotation.json  ← Print Format definition
│   │       └── systemair_quotation.html  ← Jinja2 template
│   │
│   ├── fixtures/
│   │   ├── custom_field.json             ← Custom fields on Item & Quotation
│   │   ├── property_setter.json          ← Field property overrides
│   │   ├── item_group.json               ← "SystemAir Axial Fans" item group
│   │   ├── price_list.json               ← Two SystemAir price lists
│   │   ├── role.json                     ← Three custom roles
│   │   ├── workflow.json                 ← SystemAir Quotation Workflow
│   │   ├── workflow_state.json           ← Workflow states
│   │   ├── workflow_action.json          ← Workflow actions/transitions
│   │   ├── systemair_price_config.json   ← Default Price Config values
│   │   └── systemair_weight_table.json   ← All 15 diameter weight records
│   │
│   └── public/
│       ├── js/
│       │   ├── quotation_extend.js       ← Quotation form customization
│       │   └── systemair_fan_item.js     ← Model code preview + item check
│       └── css/
│           └── kayan_systemair.css       ← Custom styling (margin colors, etc.)
│
├── requirements.txt                      ← Python dependencies (openpyxl, etc.)
├── pyproject.toml                        ← ERPNext v16 uses pyproject.toml
├── MANIFEST.in
├── LICENSE
└── README.md
```

---

## 14. Key File Contents & Skeletons

### 14.1 `pyproject.toml`

```toml
[project]
name = "kayan_systemair"
authors = [{ name = "Kayan for Import" }]
description = "SystemAir Fan Sales Module for ERPNext v16"
requires-python = ">=3.11"
readme = "README.md"
dynamic = ["version"]
dependencies = [
    "frappe",
    "openpyxl>=3.1.0",
]

[project.urls]
Homepage = "https://github.com/kayan-erp/kayan_systemair"

[tool.flit.metadata]
module = "kayan_systemair"

[tool.bench.dev-dependencies]
frappe = ">=16.0.0"
```

### 14.2 `kayan_systemair/__init__.py`

```python
__version__ = "1.0.0"
```

### 14.3 `kayan_systemair/hooks.py`

```python
from . import __version__ as app_version

app_name        = "kayan_systemair"
app_title       = "Kayan SystemAir"
app_publisher   = "Kayan for Import"
app_description = "SystemAir Axial Fan Sales Module"
app_email       = "it@kayan.com"
app_license     = "MIT"
app_version     = app_version

# ── Fixtures ──────────────────────────────────────────────────────────────────
fixtures = [
    "Role",
    "Item Group",
    "Price List",
    "Workflow",
    "Workflow State",
    "Workflow Action",
    {
        "dt": "Custom Field",
        "filters": [["dt", "in", ["Item", "Quotation", "Quotation Item"]]]
    },
    {
        "dt": "Property Setter",
        "filters": [["doc_type", "in", ["Item", "Quotation"]]]
    },
    "SystemAir Price Config",
    "SystemAir Weight Table",
    "Print Format",
]

# ── Document Events ───────────────────────────────────────────────────────────
doc_events = {
    "Quotation": {
        "before_save":  "kayan_systemair.custom.quotation.before_save",
        "on_submit":    "kayan_systemair.custom.quotation.on_submit",
        "on_cancel":    "kayan_systemair.custom.quotation.on_cancel",
    }
}

# ── Scheduled Tasks ───────────────────────────────────────────────────────────
scheduler_events = {
    "weekly": [
        "kayan_systemair.tasks.remind_price_list_update"
    ]
}

# ── App Includes (JS/CSS) ─────────────────────────────────────────────────────
app_include_js  = "/assets/kayan_systemair/js/quotation_extend.js"
app_include_css = "/assets/kayan_systemair/css/kayan_systemair.css"

# ── Website ───────────────────────────────────────────────────────────────────
# (none for this app)

# ── Override Whitelisted Methods ──────────────────────────────────────────────
override_whitelisted_methods = {}

# ── Boot Session ─────────────────────────────────────────────────────────────
boot_session = "kayan_systemair.startup.boot_session"
```

### 14.4 `kayan_systemair/modules.txt`

```
kayan_systemair
```

### 14.5 `kayan_systemair/install.py`

```python
import frappe

def after_install():
    """Called by bench after app installation."""
    create_item_groups()
    create_price_lists()
    create_roles()
    setup_workspace()
    frappe.db.commit()
    print("[kayan_systemair] Installation complete.")


def create_item_groups():
    if not frappe.db.exists("Item Group", "SystemAir Axial Fans"):
        frappe.get_doc({
            "doctype": "Item Group",
            "item_group_name": "SystemAir Axial Fans",
            "parent_item_group": "Products",
            "is_group": 0,
        }).insert(ignore_permissions=True)


def create_price_lists():
    for pl_name in ["Systemair Germany 2026", "Systemair Malaysia 2026"]:
        if not frappe.db.exists("Price List", pl_name):
            frappe.get_doc({
                "doctype": "Price List",
                "price_list_name": pl_name,
                "currency": "EUR",
                "selling": 1,
                "buying": 0,
                "enabled": 1,
            }).insert(ignore_permissions=True)


def create_roles():
    for role in ["SystemAir Sales User", "SystemAir Sales Manager", "SystemAir Admin"]:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({
                "doctype": "Role",
                "role_name": role,
                "desk_access": 1,
            }).insert(ignore_permissions=True)


def setup_workspace():
    """Ensure workspace is visible after install."""
    pass  # Workspace loaded from fixtures/workspace JSON
```

### 14.6 `kayan_systemair/doctype/systemair_fan_item/systemair_fan_item.py`

```python
import frappe
from frappe.model.document import Document
from frappe.utils import flt
from kayan_systemair.doctype.systemair_quotation_item.pricing_engine import get_list_price


class SystemAirFanItem(Document):

    def validate(self):
        self.model_code = self._assemble_model_code()
        self._check_item_exists()
        self._fetch_prices()
        self._fetch_weight()

    def on_submit(self):
        if not self.item_exists:
            self._create_erp_item()

    # ── Private helpers ────────────────────────────────────────────────────

    def _assemble_model_code(self):
        code = f"{self.fan_model} {self.nominal_diameter}"
        code += f"-{self.num_blades}/{self.blade_angle}\u00b0"
        code += f"-{self.num_poles}"
        if self.smoke_rating and self.smoke_rating != "None":
            code += f"({self.smoke_rating})"
        if self.guide_vane:
            code += "-PV"
        if self.medium_casing:
            code += " MC"
        if self.config_suffix and self.config_suffix != "None":
            code += self.config_suffix
        if self.reversible:
            code += "-TR"
        return code

    def _check_item_exists(self):
        existing = frappe.db.get_value("Item", {"item_code": self.model_code}, "name")
        self.item_exists = 1 if existing else 0
        self.erp_item = existing or None

    def _fetch_prices(self):
        self.germany_price  = get_list_price(self.model_code, "Systemair Germany 2026") or 0
        self.malaysia_price = get_list_price(self.model_code, "Systemair Malaysia 2026") or 0

    def _fetch_weight(self):
        weight = frappe.db.get_value(
            "SystemAir Weight Table",
            {"nominal_diameter": int(self.nominal_diameter)},
            "max_weight_kg"
        )
        self.approx_weight = flt(weight)

    def _create_erp_item(self):
        item = frappe.get_doc({
            "doctype": "Item",
            "item_code": self.model_code,
            "item_name": self.model_code,
            "item_group": "SystemAir Axial Fans",
            "stock_uom": "Nos",
            "is_purchase_item": 1,
            "is_sales_item": 1,
            "is_stock_item": 0,
            # Custom SA fields
            "sa_nominal_diameter": str(self.nominal_diameter),
            "sa_num_blades": self.num_blades,
            "sa_blade_angle": self.blade_angle,
            "sa_num_poles": str(self.num_poles),
            "sa_smoke_rating": self.smoke_rating,
            "sa_weight_kg": self.approx_weight,
            "sa_product_family": self.product_group,
            "sa_primary_factory": self.primary_factory,
        })
        item.insert(ignore_permissions=True)
        self.erp_item = item.name
        self.item_exists = 1
        frappe.msgprint(
            f"Item <b>{self.model_code}</b> created successfully in ERPNext.",
            alert=True, indicator="green"
        )
```

### 14.7 `kayan_systemair/doctype/systemair_quotation_item/pricing_engine.py`

```python
import frappe
from frappe.utils import flt


def compute_pricing(item_row, quotation_doc):
    """
    Full 16-step pricing formula chain.
    Replicates Excel COST sheet columns L–AB exactly.
    """
    cfg = frappe.get_single("SystemAir Price Config")

    # ── Inputs ────────────────────────────────────────────────────────────
    ex_price            = flt(item_row.ex_price)
    qty                 = flt(item_row.qty) or 1
    supplier_discount   = flt(item_row.supplier_discount) / 100
    additional_discount = flt(item_row.additional_discount) / 100
    customs_rate        = flt(item_row.customs_rate) / 100
    margin              = flt(item_row.margin_percent) / 100
    shipping_rate       = flt(
        getattr(quotation_doc, "sa_shipping_rate", None) or cfg.default_shipping_rate
    ) / 100
    currency_rate       = flt(
        getattr(quotation_doc, "sa_eur_egp_rate", None) or cfg.default_currency_rate
    ) or 1
    cost_factors        = flt(cfg.cost_factor_1) * flt(cfg.cost_factor_2)  # 1.05 × 1.07
    vat_multiplier      = 1 + (flt(cfg.vat_rate) / 100)                    # 1.14

    if not ex_price:
        frappe.throw(f"EX Price must be set for item {item_row.item_code or item_row.idx}")

    # ── Steps 4–16 ────────────────────────────────────────────────────────
    basic_ex_price   = ex_price * qty * (1 - supplier_discount)            # Step 4  → Col P
    final_ex_price   = basic_ex_price * (1 - additional_discount)          # Step 6  → Col R
    shipping_cost    = basic_ex_price * shipping_rate                       # Step 7  → Col S
    cif              = final_ex_price + shipping_cost                       # Step 8  → Col T
    ddp_cost         = (cif * cost_factors * currency_rate                  # Step 13 → Col Y
                        * vat_multiplier * (1 + customs_rate))
    total_price      = (cif * cost_factors * (1 + margin)                  # Step 15 → Col AB
                        * currency_rate * vat_multiplier * (1 + customs_rate))
    unit_price       = total_price / qty                                    # Step 16 → Col AA

    # ── Write back ───────────────────────────────────────────────────────
    item_row.basic_ex_price  = round(basic_ex_price, 4)
    item_row.final_ex_price  = round(final_ex_price, 4)
    item_row.shipping_cost   = round(shipping_cost, 4)
    item_row.cif             = round(cif, 4)
    item_row.ddp_cost        = round(ddp_cost, 4)
    item_row.unit_price_egp  = round(unit_price, 2)
    item_row.total_price_egp = round(total_price, 2)
    item_row.rate            = round(unit_price, 2)
    item_row.amount          = round(total_price, 2)

    return item_row


def get_list_price(item_code, price_list):
    """
    Exact match first, fuzzy match fallback.
    Returns float or list of dicts (for fuzzy).
    """
    price = frappe.db.get_value(
        "Item Price",
        {"item_code": item_code, "price_list": price_list, "selling": 1},
        "price_list_rate"
    )
    if price:
        return flt(price)

    # Fuzzy fallback via item_name
    results = frappe.db.sql("""
        SELECT ip.item_code, ip.price_list_rate, i.item_name
        FROM   `tabItem Price` ip
        JOIN   `tabItem` i ON i.item_code = ip.item_code
        WHERE  ip.price_list = %s
        AND    i.item_name LIKE %s
        LIMIT  10
    """, (price_list, f"%{item_code}%"), as_dict=True)

    return results if results else None


def get_weight_for_diameter(diameter_mm):
    """Returns max_weight_kg from SystemAir Weight Table for given diameter."""
    return flt(frappe.db.get_value(
        "SystemAir Weight Table",
        {"nominal_diameter": int(diameter_mm)},
        "max_weight_kg"
    ))
```

### 14.8 `kayan_systemair/custom/quotation.py`

```python
import frappe
from kayan_systemair.doctype.systemair_quotation_item.pricing_engine import compute_pricing


def before_save(doc, method):
    """Triggered by hooks.py for every Quotation save."""
    if not doc.is_systemair_quotation:
        return
    _recalculate_all_items(doc)
    _compute_quotation_totals(doc)


def _recalculate_all_items(doc):
    for item in doc.get("sa_items") or []:
        # Apply quotation-level defaults if item-level not set
        if not item.supplier_discount:
            item.supplier_discount = doc.sa_default_discount or 0
        if not item.additional_discount:
            item.additional_discount = doc.sa_additional_discount or 0
        if not item.customs_rate:
            item.customs_rate = doc.sa_default_customs or 0
        if not item.margin_percent:
            item.margin_percent = doc.sa_default_margin or 50
        compute_pricing(item, doc)


def _compute_quotation_totals(doc):
    total_cif    = sum(flt(r.cif) for r in doc.get("sa_items") or [])
    grand_total  = sum(flt(r.total_price_egp) for r in doc.get("sa_items") or [])
    total_ddp    = sum(flt(r.ddp_cost) for r in doc.get("sa_items") or [])

    doc.sa_total_cif_eur = total_cif
    doc.sa_grand_total_egp = grand_total
    doc.grand_total = grand_total

    # Effective margin = (Grand Total - Total DDP) / Grand Total
    if grand_total:
        doc.sa_effective_margin = round((grand_total - total_ddp) / grand_total * 100, 2)


def on_submit(doc, method):
    if not doc.is_systemair_quotation:
        return
    # Lock calculated fields on submission


def on_cancel(doc, method):
    pass


def flt(val, precision=None):
    from frappe.utils import flt as _flt
    return _flt(val, precision)
```

### 14.9 `kayan_systemair/page/price_list_import/price_list_import.py`

```python
import frappe
from frappe import _
from frappe.utils.file_manager import save_file
import openpyxl
import io


@frappe.whitelist()
def import_price_list(file_content, price_list_name, sheet_name):
    """
    Background-safe import function.
    Called from price_list_import.js via frappe.call().
    Enqueues a background job for large imports.
    """
    frappe.enqueue(
        "kayan_systemair.page.price_list_import.price_list_import._do_import",
        queue="long",
        timeout=3600,
        file_content=file_content,
        price_list_name=price_list_name,
        sheet_name=sheet_name,
        user=frappe.session.user,
    )
    return {"message": _("Import started in background. Check Import Log for results.")}


def _do_import(file_content, price_list_name, sheet_name, user):
    """Actual import logic — runs as background job."""
    wb = openpyxl.load_workbook(io.BytesIO(file_content), data_only=True)
    ws = wb[sheet_name]

    headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
    # Detect column positions
    name_col  = _find_col(headers, ["Item name", "item_name"])
    price_col = _find_col(headers, ["Sales price", "sales_price"])
    no_col    = _find_col(headers, ["Item no", "item_no"])

    created = updated = skipped = 0

    for row in ws.iter_rows(min_row=2, values_only=True):
        item_name  = row[name_col]  if name_col  is not None else None
        list_price = row[price_col] if price_col is not None else None
        item_no    = row[no_col]    if no_col    is not None else None

        if not item_name or not list_price:
            skipped += 1
            continue

        # Get or create Item
        item_code = str(item_name).strip()
        if not frappe.db.exists("Item", item_code):
            frappe.get_doc({
                "doctype": "Item",
                "item_code": item_code,
                "item_name": item_code,
                "item_group": "SystemAir Axial Fans",
                "stock_uom": "Nos",
                "is_sales_item": 1,
                "is_purchase_item": 1,
                "is_stock_item": 0,
                "sa_article_no": str(item_no) if item_no else "",
            }).insert(ignore_permissions=True)
            created += 1
        else:
            updated += 1

        # Upsert Item Price
        existing_price = frappe.db.get_value(
            "Item Price",
            {"item_code": item_code, "price_list": price_list_name},
            "name"
        )
        if existing_price:
            frappe.db.set_value("Item Price", existing_price, "price_list_rate", list_price)
        else:
            frappe.get_doc({
                "doctype": "Item Price",
                "item_code": item_code,
                "price_list": price_list_name,
                "price_list_rate": list_price,
                "selling": 1,
                "currency": "EUR",
            }).insert(ignore_permissions=True)

    frappe.db.commit()

    # Write import log
    frappe.get_doc({
        "doctype": "SystemAir Import Log",
        "price_list": price_list_name,
        "sheet_name": sheet_name,
        "imported_by": user,
        "records_created": created,
        "records_updated": updated,
        "records_skipped": skipped,
        "status": "Completed",
    }).insert(ignore_permissions=True)
    frappe.db.commit()


def _find_col(headers, candidates):
    for i, h in enumerate(headers):
        if h and any(c.lower() in str(h).lower() for c in candidates):
            return i
    return None
```

### 14.10 `kayan_systemair/public/js/quotation_extend.js`

```javascript
// Extends the standard ERPNext Quotation form for SystemAir quotations.
// Loaded globally via hooks.py app_include_js.

frappe.ui.form.on("Quotation", {
    refresh(frm) {
        if (!frm.doc.is_systemair_quotation) return;
        toggle_sa_sections(frm);
        add_sa_buttons(frm);
    },

    is_systemair_quotation(frm) {
        toggle_sa_sections(frm);
    },

    sa_eur_egp_rate(frm)       { recalculate_all(frm); },
    sa_default_discount(frm)   { recalculate_all(frm); },
    sa_default_margin(frm)     { recalculate_all(frm); },
    sa_default_customs(frm)    { recalculate_all(frm); },
    sa_shipping_rate(frm)      { recalculate_all(frm); },
});

frappe.ui.form.on("SystemAir Quotation Item", {
    ex_price(frm, cdt, cdn)          { recalculate_row(frm, cdt, cdn); },
    qty(frm, cdt, cdn)               { recalculate_row(frm, cdt, cdn); },
    supplier_discount(frm, cdt, cdn) { recalculate_row(frm, cdt, cdn); },
    additional_discount(frm, cdt, cdn){ recalculate_row(frm, cdt, cdn); },
    customs_rate(frm, cdt, cdn)      { recalculate_row(frm, cdt, cdn); },
    margin_percent(frm, cdt, cdn)    { recalculate_row(frm, cdt, cdn); },

    item_code(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.item_code) return;
        // Auto-fetch list prices
        frappe.call({
            method: "kayan_systemair.api.get_item_prices",
            args: { item_code: row.item_code },
            callback(r) {
                if (r.message) {
                    frappe.model.set_value(cdt, cdn, "germany_list_price",  r.message.germany || 0);
                    frappe.model.set_value(cdt, cdn, "malaysia_list_price", r.message.malaysia || 0);
                    frappe.model.set_value(cdt, cdn, "ex_price",            r.message.germany || 0);
                    recalculate_row(frm, cdt, cdn);
                }
            }
        });
    }
});

function toggle_sa_sections(frm) {
    const is_sa = frm.doc.is_systemair_quotation;
    frm.toggle_display("items", !is_sa);           // Hide standard items table
    frm.toggle_display("sa_items", is_sa);          // Show SA items table
    frm.toggle_display("sa_accessories", is_sa);
    frm.toggle_display("sa_pricing_section", is_sa);
}

function add_sa_buttons(frm) {
    if (frm.doc.docstatus !== 0) return;
    frm.add_custom_button(__("Add Fan Item"), () => {
        frappe.new_doc("SystemAir Fan Item", {}, doc => {
            // After fan item creation, link back to quotation
        });
    }, __("SystemAir"));
}

function recalculate_row(frm, cdt, cdn) {
    // Client-side preview — server will recalculate on save
    let row = locals[cdt][cdn];
    let cfg_rate    = frm.doc.sa_eur_egp_rate || 1;
    let cfg_margin  = frm.doc.sa_default_margin / 100 || 0.5;
    let cfg_ship    = frm.doc.sa_shipping_rate / 100 || 0.12;
    let cfg_customs = frm.doc.sa_default_customs / 100 || 0;
    let cfg_vat     = 1.14;
    let cfg_cf      = 1.1235;

    let ex       = flt(row.ex_price);
    let qty      = flt(row.qty) || 1;
    let disc1    = flt(row.supplier_discount)   / 100;
    let disc2    = flt(row.additional_discount) / 100;
    let customs  = flt(row.customs_rate || cfg_customs * 100) / 100;
    let margin   = flt(row.margin_percent || cfg_margin * 100) / 100;

    let basic    = ex * qty * (1 - disc1);
    let final_ex = basic * (1 - disc2);
    let ship     = basic * cfg_ship;
    let cif      = final_ex + ship;
    let total    = cif * cfg_cf * (1 + margin) * cfg_rate * cfg_vat * (1 + customs);
    let unit     = total / qty;

    frappe.model.set_value(cdt, cdn, "basic_ex_price",  round4(basic));
    frappe.model.set_value(cdt, cdn, "final_ex_price",  round4(final_ex));
    frappe.model.set_value(cdt, cdn, "shipping_cost",   round4(ship));
    frappe.model.set_value(cdt, cdn, "cif",             round4(cif));
    frappe.model.set_value(cdt, cdn, "unit_price_egp",  round2(unit));
    frappe.model.set_value(cdt, cdn, "total_price_egp", round2(total));

    // Margin color indicator
    set_margin_color(frm, cdt, cdn, margin * 100);
    update_quotation_totals(frm);
}

function recalculate_all(frm) {
    (frm.doc.sa_items || []).forEach(row => {
        recalculate_row(frm, row.doctype, row.name);
    });
}

function update_quotation_totals(frm) {
    let total_egp = (frm.doc.sa_items || []).reduce((s, r) => s + flt(r.total_price_egp), 0);
    frm.set_value("sa_grand_total_egp", round2(total_egp));
}

function set_margin_color(frm, cdt, cdn, margin_pct) {
    let color = margin_pct >= 40 ? "green" : margin_pct >= 25 ? "orange" : "red";
    // Apply color to the margin field cell
    let grid_row = frm.fields_dict["sa_items"].grid.get_row(cdn);
    if (grid_row) {
        grid_row.columns["margin_percent"].$el.css("color", color);
    }
}

function flt(val)     { return parseFloat(val) || 0; }
function round2(val)  { return Math.round(val * 100) / 100; }
function round4(val)  { return Math.round(val * 10000) / 10000; }
```

### 14.11 `kayan_systemair/doctype/systemair_fan_item/systemair_fan_item.js`

```javascript
frappe.ui.form.on("SystemAir Fan Item", {
    // Live model code preview
    fan_model(frm)         { update_model_code(frm); },
    nominal_diameter(frm)  { update_model_code(frm); fetch_weight(frm); },
    num_blades(frm)        { update_model_code(frm); },
    blade_angle(frm)       { update_model_code(frm); },
    num_poles(frm)         { update_model_code(frm); },
    smoke_rating(frm)      { update_model_code(frm); },
    guide_vane(frm)        { update_model_code(frm); },
    medium_casing(frm)     { update_model_code(frm); },
    reversible(frm)        { update_model_code(frm); },
    config_suffix(frm)     { update_model_code(frm); },

    refresh(frm) {
        if (frm.doc.model_code) check_item_exists(frm);
        if (frm.doc.docstatus === 1 && !frm.doc.item_exists) {
            frm.add_custom_button(__("Create ERPNext Item"), () => {
                frappe.call({
                    method: "kayan_systemair.doctype.systemair_fan_item.systemair_fan_item.create_item_from_doc",
                    args: { docname: frm.doc.name },
                    callback(r) { frm.reload_doc(); }
                });
            }).addClass("btn-primary");
        }
    }
});

function update_model_code(frm) {
    let d = frm.doc;
    if (!d.fan_model || !d.nominal_diameter || !d.num_blades || !d.blade_angle || !d.num_poles) return;

    let code = `${d.fan_model} ${d.nominal_diameter}`;
    code += `-${d.num_blades}/${d.blade_angle}\u00b0`;
    code += `-${d.num_poles}`;
    if (d.smoke_rating && d.smoke_rating !== "None") code += `(${d.smoke_rating})`;
    if (d.guide_vane)   code += "-PV";
    if (d.medium_casing) code += " MC";
    if (d.config_suffix && d.config_suffix !== "None") code += d.config_suffix;
    if (d.reversible)   code += "-TR";

    frm.set_value("model_code", code);
    check_item_exists(frm, code);
}

function check_item_exists(frm, code) {
    let model = code || frm.doc.model_code;
    if (!model) return;
    frappe.db.get_value("Item", { item_code: model }, "name").then(r => {
        if (r && r.message && r.message.name) {
            frm.set_value("item_exists", 1);
            frm.set_value("erp_item", r.message.name);
            frm.set_intro(__("This item already exists in ERPNext."), "blue");
        } else {
            frm.set_value("item_exists", 0);
            frm.set_value("erp_item", null);
            frm.set_intro(__("New item — submit to register in ERPNext."), "orange");
        }
        fetch_prices(frm, model);
    });
}

function fetch_prices(frm, model) {
    frappe.call({
        method: "kayan_systemair.api.get_item_prices",
        args: { item_code: model },
        callback(r) {
            if (r.message) {
                frm.set_value("germany_price",  r.message.germany  || 0);
                frm.set_value("malaysia_price", r.message.malaysia || 0);
            }
        }
    });
}

function fetch_weight(frm) {
    if (!frm.doc.nominal_diameter) return;
    frappe.db.get_value(
        "SystemAir Weight Table",
        { nominal_diameter: frm.doc.nominal_diameter },
        "max_weight_kg"
    ).then(r => {
        if (r && r.message) frm.set_value("approx_weight", r.message.max_weight_kg);
    });
}
```

### 14.12 `kayan_systemair/report/systemair_quotation_summary/systemair_quotation_summary.py`

```python
import frappe

def execute(filters=None):
    filters = filters or {}

    columns = [
        {"label": "Quotation",       "fieldname": "name",               "fieldtype": "Link",     "options": "Quotation", "width": 130},
        {"label": "Date",            "fieldname": "transaction_date",   "fieldtype": "Date",     "width": 100},
        {"label": "Customer",        "fieldname": "party_name",         "fieldtype": "Data",     "width": 160},
        {"label": "Project Ref",     "fieldname": "sa_project_ref",     "fieldtype": "Data",     "width": 130},
        {"label": "Status",          "fieldname": "status",             "fieldtype": "Data",     "width": 100},
        {"label": "Fan Items",       "fieldname": "num_items",          "fieldtype": "Int",      "width": 80},
        {"label": "Total CIF (EUR)", "fieldname": "sa_total_cif_eur",   "fieldtype": "Currency", "width": 130},
        {"label": "Grand Total (EGP)","fieldname": "sa_grand_total_egp","fieldtype": "Currency", "width": 140},
        {"label": "Effective Margin %","fieldname": "sa_effective_margin","fieldtype": "Percent","width": 120},
    ]

    conditions = "q.is_systemair_quotation = 1"
    if filters.get("from_date"):
        conditions += f" AND q.transaction_date >= '{filters['from_date']}'"
    if filters.get("to_date"):
        conditions += f" AND q.transaction_date <= '{filters['to_date']}'"
    if filters.get("status"):
        conditions += f" AND q.status = '{filters['status']}'"
    if filters.get("customer"):
        conditions += f" AND q.party_name = '{filters['customer']}'"

    data = frappe.db.sql(f"""
        SELECT
            q.name, q.transaction_date, q.party_name,
            q.sa_project_ref, q.status,
            COUNT(qi.name) AS num_items,
            q.sa_total_cif_eur, q.sa_grand_total_egp, q.sa_effective_margin
        FROM `tabQuotation` q
        LEFT JOIN `tabSystemAir Quotation Item` qi ON qi.parent = q.name
        WHERE {conditions}
        GROUP BY q.name
        ORDER BY q.transaction_date DESC
    """, as_dict=True)

    return columns, data
```

### 14.13 `kayan_systemair/fixtures/systemair_weight_table.json`

```json
[
  {"doctype": "SystemAir Weight Table", "nominal_diameter": 315,  "min_weight_kg": 40,  "max_weight_kg": 57},
  {"doctype": "SystemAir Weight Table", "nominal_diameter": 355,  "min_weight_kg": 40,  "max_weight_kg": 57},
  {"doctype": "SystemAir Weight Table", "nominal_diameter": 400,  "min_weight_kg": 45,  "max_weight_kg": 62},
  {"doctype": "SystemAir Weight Table", "nominal_diameter": 450,  "min_weight_kg": 52,  "max_weight_kg": 84},
  {"doctype": "SystemAir Weight Table", "nominal_diameter": 500,  "min_weight_kg": 52,  "max_weight_kg": 107},
  {"doctype": "SystemAir Weight Table", "nominal_diameter": 560,  "min_weight_kg": 58,  "max_weight_kg": 112},
  {"doctype": "SystemAir Weight Table", "nominal_diameter": 630,  "min_weight_kg": 93,  "max_weight_kg": 160},
  {"doctype": "SystemAir Weight Table", "nominal_diameter": 710,  "min_weight_kg": 100, "max_weight_kg": 200},
  {"doctype": "SystemAir Weight Table", "nominal_diameter": 800,  "min_weight_kg": 100, "max_weight_kg": 287},
  {"doctype": "SystemAir Weight Table", "nominal_diameter": 900,  "min_weight_kg": 163, "max_weight_kg": 343},
  {"doctype": "SystemAir Weight Table", "nominal_diameter": 1000, "min_weight_kg": 100, "max_weight_kg": 287},
  {"doctype": "SystemAir Weight Table", "nominal_diameter": 1120, "min_weight_kg": 281, "max_weight_kg": 557},
  {"doctype": "SystemAir Weight Table", "nominal_diameter": 1250, "min_weight_kg": 336, "max_weight_kg": 667},
  {"doctype": "SystemAir Weight Table", "nominal_diameter": 1400, "min_weight_kg": 511, "max_weight_kg": 778},
  {"doctype": "SystemAir Weight Table", "nominal_diameter": 1600, "min_weight_kg": 545, "max_weight_kg": 1792}
]
```

### 14.14 `kayan_systemair/fixtures/systemair_price_config.json`

```json
[
  {
    "doctype": "SystemAir Price Config",
    "vat_rate": 14.0,
    "cost_factor_1": 1.05,
    "cost_factor_2": 1.07,
    "combined_cost_factor": 1.1235,
    "default_shipping_rate": 12.0,
    "default_margin": 50.0,
    "default_currency_rate": 50.0,
    "default_customs_rate": 0.0
  }
]
```

### 14.15 `kayan_systemair/workspace/kayan_systemair/kayan_systemair.json` (ERPNext v16 format)

```json
{
  "charts": [],
  "content": "[{\"type\":\"onboarding\",\"data\":{\"onboarding_name\":\"SystemAir\",\"col\":12}},{\"type\":\"spacer\",\"data\":{\"col\":12}},{\"type\":\"header\",\"data\":{\"text\":\"<h2>Quotations</h2>\",\"col\":12}},{\"type\":\"shortcut\",\"data\":{\"shortcut_name\":\"New SA Quotation\",\"col\":3}},{\"type\":\"shortcut\",\"data\":{\"shortcut_name\":\"SA Fan Item\",\"col\":3}},{\"type\":\"shortcut\",\"data\":{\"shortcut_name\":\"Price List Import\",\"col\":3}},{\"type\":\"shortcut\",\"data\":{\"shortcut_name\":\"Price Config\",\"col\":3}}]",
  "doctype": "Workspace",
  "extends": "",
  "extends_another_page": 0,
  "hide_custom": 0,
  "icon": "fan",
  "is_hidden": 0,
  "label": "SystemAir",
  "module": "kayan_systemair",
  "name": "SystemAir",
  "onboarding": "SystemAir",
  "parent_page": "",
  "public": 1,
  "restrict_to_domain": "",
  "roles": [
    {"role": "SystemAir Sales User"},
    {"role": "SystemAir Sales Manager"},
    {"role": "SystemAir Admin"}
  ],
  "shortcuts": [
    {"label": "New SA Quotation",   "type": "DocType", "doc_view": "new", "link_to": "Quotation"},
    {"label": "SA Fan Item",        "type": "DocType", "link_to": "SystemAir Fan Item"},
    {"label": "Price List Import",  "type": "Page",    "link_to": "price-list-import"},
    {"label": "Price Config",       "type": "DocType", "link_to": "SystemAir Price Config"},
    {"label": "Quotation Summary",  "type": "Report",  "link_to": "SystemAir Quotation Summary"},
    {"label": "Margin Analysis",    "type": "Report",  "link_to": "Margin Analysis"}
  ]
}
```

---

## 15. Technical Architecture

### 15.1 ERPNext v16 Specific Notes

- Python **3.11+** required
- Uses `pyproject.toml` instead of `setup.py`
- Frappe v16 uses **Rq (Redis Queue)** for background jobs
- DocType JSON schema v16: `"engine": "InnoDB"` field removed; use `"track_changes": 1` for audit
- `frappe.get_single()` for Single DocTypes unchanged
- Client scripts in DocType folder (`doctype_name.js`) — auto-loaded by Frappe
- Global JS via `app_include_js` in `hooks.py`
- Workspace v16 format: JSON-based, replaces old `desktop.py`
- **Naming Series:** `SA-ITEM-.YYYY.-.####` for SystemAir Fan Items
- **Naming Series:** Uses standard Quotation naming from ERPNext

### 15.2 Performance

| Concern | Solution |
|---|---|
| Price list lookup on 8,300+ rows | Index on `item_code` in `tabItem Price` (already indexed by ERPNext) |
| Bulk price import | `frappe.enqueue()` → background job, `queue="long"`, `timeout=3600` |
| Weight table lookup | `frappe.cache().get_value()` with 24h TTL |
| Client-side preview | Debounced recalculation — 300ms delay after last keystroke |

### 15.3 API Endpoints (Whitelisted)

```python
# kayan_systemair/api.py

import frappe
from frappe import _
from kayan_systemair.doctype.systemair_quotation_item.pricing_engine import get_list_price


@frappe.whitelist()
def get_item_prices(item_code):
    """Returns Germany and Malaysia list prices for a given item code."""
    return {
        "germany":  get_list_price(item_code, "Systemair Germany 2026"),
        "malaysia": get_list_price(item_code, "Systemair Malaysia 2026"),
    }


@frappe.whitelist()
def check_item_exists(model_code):
    """Returns item name if exists, else None."""
    return frappe.db.get_value("Item", {"item_code": model_code}, "name")


@frappe.whitelist()
def get_weight_for_diameter(diameter):
    """Returns max weight for a given nominal diameter."""
    return frappe.db.get_value(
        "SystemAir Weight Table",
        {"nominal_diameter": int(diameter)},
        ["min_weight_kg", "max_weight_kg"],
        as_dict=True
    )


@frappe.whitelist()
def get_price_config():
    """Returns current SystemAir Price Config values."""
    return frappe.get_single("SystemAir Price Config").as_dict()
```

---

## 16. Installation & Data Migration

### 16.1 Installation Commands

```bash
# 1. Get the app
bench get-app https://github.com/kayan-erp/kayan_systemair

# 2. Install on site
bench --site [your-site.com] install-app kayan_systemair

# 3. Run migrations (creates DocType tables)
bench --site [your-site.com] migrate

# 4. Run setup (loads fixtures, creates item groups, roles, price lists)
bench --site [your-site.com] execute kayan_systemair.install.after_install

# 5. Build assets
bench build --app kayan_systemair

# 6. Restart
bench restart
```

### 16.2 Import Price Lists

```bash
# Via UI (recommended):
# Navigate to: SystemAir Workspace → Price List Import
# Upload "Price List.xlsx" → select sheet "Germany" → Import
# Upload "Price List.xlsx" → select sheet "Box,Jet MY" → Import

# Via bench (for automation):
bench --site [your-site.com] execute \
  kayan_systemair.page.price_list_import.price_list_import.import_from_file \
  --kwargs '{"filepath": "/path/to/Price List.xlsx", "price_list": "Systemair Germany 2026", "sheet": "Germany"}'
```

### 16.3 Data Migration from Excel

```bash
# Migrate open quotations from Excel workbook
bench --site [your-site.com] execute \
  kayan_systemair.migration.migrate_from_excel \
  --kwargs '{"filepath": "/path/to/000-Pricing Sheet 2026.xlsx"}'
```

---

## 17. Testing Requirements

### 17.1 Unit Tests — Pricing Engine (`test_systemair_quotation_item.py`)

```python
import frappe
import unittest
from kayan_systemair.doctype.systemair_quotation_item.pricing_engine import compute_pricing

class TestPricingEngine(unittest.TestCase):

    def setUp(self):
        # Ensure Price Config has known values
        cfg = frappe.get_single("SystemAir Price Config")
        cfg.vat_rate = 14
        cfg.cost_factor_1 = 1.05
        cfg.cost_factor_2 = 1.07
        cfg.default_shipping_rate = 12
        cfg.save()

    def test_standard_fan_50pct_margin(self):
        """Test Case 1: Standard fan, 0% customs, 50% margin."""
        item = frappe._dict(
            ex_price=1000, qty=2, supplier_discount=20,
            additional_discount=0, customs_rate=0, margin_percent=50
        )
        quotation = frappe._dict(sa_eur_egp_rate=50, sa_shipping_rate=12)
        compute_pricing(item, quotation)

        self.assertAlmostEqual(item.basic_ex_price, 1600.0,  places=2)  # 1000×2×0.8
        self.assertAlmostEqual(item.shipping_cost,  192.0,   places=2)  # 1600×0.12
        self.assertAlmostEqual(item.cif,            1792.0,  places=2)  # 1600 + 192
        # total = 1792 × 1.1235 × 1.5 × 50 × 1.14 × 1.0
        expected_total = 1792 * 1.1235 * 1.5 * 50 * 1.14 * 1.0
        self.assertAlmostEqual(item.total_price_egp, expected_total, places=2)
        self.assertAlmostEqual(item.unit_price_egp, expected_total / 2, places=2)

    def test_smoke_rated_fan_10pct_customs(self):
        """Test Case 2: Smoke-rated (B), 10% customs, 40% margin."""
        item = frappe._dict(
            ex_price=2500, qty=1, supplier_discount=15,
            additional_discount=5, customs_rate=10, margin_percent=40
        )
        quotation = frappe._dict(sa_eur_egp_rate=55, sa_shipping_rate=12)
        compute_pricing(item, quotation)
        self.assertGreater(item.total_price_egp, 0)
        self.assertAlmostEqual(item.unit_price_egp, item.total_price_egp, places=2)

    def test_zero_ex_price_raises_error(self):
        """Test Case 3: Zero EX Price must raise validation error."""
        item = frappe._dict(
            ex_price=0, qty=1, supplier_discount=0,
            additional_discount=0, customs_rate=0, margin_percent=50,
            item_code="TEST-001", idx=1
        )
        quotation = frappe._dict(sa_eur_egp_rate=50, sa_shipping_rate=12)
        with self.assertRaises(frappe.exceptions.ValidationError):
            compute_pricing(item, quotation)

    def test_excel_parity(self):
        """
        Test Case 6: Excel parity.
        Known inputs from 000-Pricing Sheet 2026.xlsx with known outputs.
        EX Price = 500 EUR, Qty = 1, Discount = 0%, Shipping = 12%,
        CF = 1.1235, VAT = 1.14, Rate = 50, MG = 50%, Customs = 0%
        Expected Total = 500 × 1.12 × 1.1235 × 1.5 × 50 × 1.14 × 1.0
        """
        item = frappe._dict(
            ex_price=500, qty=1, supplier_discount=0,
            additional_discount=0, customs_rate=0, margin_percent=50
        )
        quotation = frappe._dict(sa_eur_egp_rate=50, sa_shipping_rate=12)
        compute_pricing(item, quotation)

        # CIF = 500 + (500 × 0.12) = 560
        self.assertAlmostEqual(item.cif, 560.0, places=4)
        # Total = 560 × 1.1235 × 1.5 × 50 × 1.14
        expected = 560 * 1.1235 * 1.5 * 50 * 1.14
        self.assertAlmostEqual(item.total_price_egp, expected, places=2)
```

### 17.2 Run Tests

```bash
bench --site [your-site.com] run-tests --app kayan_systemair
```

---

## 18. Implementation Plan

| Phase | Weeks | Deliverables | Milestone |
|---|---|---|---|
| 1 | 1–2 | App scaffold, all DocTypes JSON + Python, fixtures, roles, price list import tool | App installable; price lists imported |
| 2 | 3–4 | Pricing engine (Python), 16-step formula, unit tests (Excel parity verified) | Engine passes all unit tests |
| 3 | 5–6 | Quotation customization: header fields, SA items child table, accessories table, full UI, workflow | End-to-end quotation creatable |
| 4 | 7 | Custom Print Format (Jinja2 PDF), all 4 custom reports, SystemAir workspace | PDF matches current Excel output |
| 5 | 8 | Excel migration utility, data migration of open quotations | All open quotations in ERPNext |
| 6 | 9 | UAT with sales team, bug fixes, performance tuning | UAT sign-off from Sales Manager |
| 7 | 10 | Production deployment, training session, go-live support | Go-live |

---

## 19. Open Questions

| # | Question | Owner | Impact |
|---|---|---|---|
| 1 | Quotation print format: bilingual Arabic/English or English only? | Kayan Management | Print format design + translation effort |
| 2 | Is 50% the minimum margin — or can Sales User offer less with Manager approval? | Sales Manager | Workflow approval logic |
| 3 | Should EUR/EGP rate be manual per quotation or auto-fetched from ERPNext Currency Exchange? | IT / Finance | Integration complexity |
| 4 | Are there other fan families (K, KD, KV inline fans) this team also quotes? | SystemAir Sales Team | Item Creator scope |
| 5 | Correct customs duty rate for AXC fans specifically? Excel shows 0% for most items. | Finance / Logistics | Default value in Price Config |
| 6 | Should submitted quotations be locked, or can a Sales Manager always unlock? | Sales Manager | Workflow state machine |
| 7 | Track competitor quotations (lost reason: competitor price) for analytics? | Sales Manager | Lost reason field options |

---

## 20. Appendix — Formula Reference & Glossary

### 20.1 Excel Column → Python Variable Mapping

| Excel Col | Excel Name | Python Variable | Formula |
|---|---|---|---|
| L | Globle Price | `germany_list_price` | `frappe.db.get_value("Item Price", ...)` |
| M | EX Price € | `ex_price` | User input; defaults to `germany_list_price` |
| N | Discount | `supplier_discount` | e.g. `0.20` for 20% |
| O | Qty. | `qty` | Standard ERPNext field |
| P | Basic T EX Price € | `basic_ex_price` | `ex_price × qty × (1 - supplier_discount)` |
| Q | Discount on Basic | `additional_discount` | e.g. `0.05` for 5% |
| R | Final T EX Price € | `final_ex_price` | `basic_ex_price × (1 - additional_discount)` |
| S | Shipping | `shipping_cost` | `basic_ex_price × shipping_rate` (default `0.12`) |
| T | CIF | `cif` | `final_ex_price + shipping_cost` |
| U | Customs | `customs_rate` | e.g. `0.05` for 5% |
| V | VAT | `vat_multiplier` | `1 + vat_rate` → `1.14` |
| W | COST FACTORS | `cost_factors` | `cf1 × cf2 = 1.05 × 1.07 = 1.1235` |
| X | Currency rate | `currency_rate` | EUR→EGP; from quotation header |
| Y | Dry DDP Cost € | `ddp_cost` | `cif × cost_factors × currency_rate × vat_multiplier × (1 + customs_rate)` |
| Z | MG (Margin) | `margin` | `0.50` default |
| AB | Total Price € | `total_price` | `cif × cost_factors × (1 + margin) × currency_rate × vat_multiplier × (1 + customs_rate)` |
| AA | Unit Price € | `unit_price` | `total_price / qty` |

### 20.2 Glossary

| Term | Definition |
|---|---|
| AXC | Axial fan (standard, uni-directional) — Systemair model family |
| AXR | Axial fan, reversible |
| AXCP / AXCPV | Axial fan, plus (new impeller) / plus with guide vane |
| CIF | Cost, Insurance, Freight — price including shipping to destination port |
| DDP | Delivered Duty Paid — full landed cost including customs and VAT |
| EX Price / EXW | Ex-Works price — factory gate price paid to Systemair in EUR |
| ESP | External Static Pressure — duct system resistance in Pascals |
| ERPNext | Open-source ERP platform built on Frappe. Kayan's primary system |
| Frappe | Python/JS web framework underlying ERPNext. v16 requires Python 3.11+ |
| MG | Gross margin percentage added to landed DDP cost |
| PV | Guide vane suffix — fan fitted with downstream guide vanes |
| Smoke B / F | (B) 300°C/120min smoke extraction; (F) 400°C/120min |
| VAT | Egyptian Value Added Tax — 14% applied to selling price |
| VLOOKUP (ERPNext) | Replicated by `frappe.db.get_value()` on `tabItem Price` |
| Single DocType | ERPNext DocType with only one record (like a settings page) |
| Child Table | DocType embedded in a parent DocType as a row-level table |

---

*Document End — kayan_systemair PRD v1.0 | ERPNext v16 | April 2026*
*Prepared for: Kayan for Import | Confidential*
