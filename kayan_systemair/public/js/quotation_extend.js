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
            method: "kayan_systemair.kayan_systemair.api.get_item_prices",
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
    // Client-side preview \u2014 server will recalculate on save
    let row = locals[cdt][cdn];
    let cfg_rate    = frm.doc.sa_eur_egp_rate || 1;
    let cfg_margin  = frm.doc.sa_default_margin / 100 || 0.5;
    let cfg_ship    = frm.doc.sa_shipping_rate / 100 || 0.12;
    let cfg_customs = frm.doc.sa_default_customs / 100 || 0;
    let cfg_vat     = 1.14;
    let cfg_cf      = 1.1235; // Default CF

    frappe.call({
        method: "kayan_systemair.kayan_systemair.api.get_price_config",
        callback: function(r){
            if(r.message && r.message.combined_cost_factor){
                cfg_cf = r.message.combined_cost_factor;
                cfg_vat = 1 + (r.message.vat_rate / 100);
            }
            
            let ex       = parseFloat(row.ex_price) || 0;
            let qty      = parseFloat(row.qty) || 1;
            let disc1    = parseFloat(row.supplier_discount)   / 100 || 0;
            let disc2    = parseFloat(row.additional_discount) / 100 || 0;
            let customs  = row.customs_rate !== undefined ? parseFloat(row.customs_rate)/100 : cfg_customs;
            let margin   = row.margin_percent !== undefined ? parseFloat(row.margin_percent)/100 : cfg_margin;
        
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
    });

}

function recalculate_all(frm) {
    (frm.doc.sa_items || []).forEach(row => {
        recalculate_row(frm, row.doctype, row.name);
    });
}

function update_quotation_totals(frm) {
    let total_egp = (frm.doc.sa_items || []).reduce((s, r) => s + parseFloat(r.total_price_egp || 0), 0);
    frm.set_value("sa_grand_total_egp", round2(total_egp));
}

function set_margin_color(frm, cdt, cdn, margin_pct) {
    let color = margin_pct >= 40 ? "green" : margin_pct >= 25 ? "orange" : "red";
    // Apply color to the margin field cell
    let grid_row = frm.fields_dict["sa_items"].grid.get_row(cdn);
    if (grid_row && grid_row.columns["margin_percent"]) {
        grid_row.columns["margin_percent"].$el.css("color", color);
    }
}

function flt(val)     { return parseFloat(val) || 0; }
function round2(val)  { return Math.round(val * 100) / 100; }
function round4(val)  { return Math.round(val * 10000) / 10000; }
