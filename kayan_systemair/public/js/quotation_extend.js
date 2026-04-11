/**
 * quotation_extend.js
 * ===================
 * Global client-side extension for the standard Quotation DocType.
 * Loaded on every desk page via app_include_js in hooks.py.
 *
 * Features:
 *  - Toggle SA sections on/off based on is_systemair_quotation flag
 *  - Debounced per-row recalculation (preview only; server recalculates on save)
 *  - Header-level defaults propagation
 *  - item_code change → auto-fetch prices
 *  - Margin colour indicators (green/amber/red)
 *  - Grand total footer update
 *  - "Add Fan Item" shortcut button
 */

(function() {
    'use strict';

    // ------------------------------------------------------------------
    // Quotation form hooks
    // ------------------------------------------------------------------
    frappe.ui.form.on('Quotation', {

        refresh: function(frm) {
            toggle_sa_sections(frm);
            if (frm.doc.is_systemair_quotation) {
                setup_sa_toolbar(frm);
                apply_margin_colors(frm);
                update_quotation_totals(frm);
            }
        },

        is_systemair_quotation: function(frm) {
            toggle_sa_sections(frm);
            if (frm.doc.is_systemair_quotation) {
                // Load defaults from Price Config if rate not set
                if (!flt(frm.doc.sa_eur_egp_rate)) {
                    load_price_config_defaults(frm);
                }
                setup_sa_toolbar(frm);
            }
        },

        // Header-level field changes → recalculate all rows
        sa_eur_egp_rate:     function(frm) { recalculate_all_rows(frm); },
        sa_default_discount: function(frm) { apply_defaults_and_recalculate(frm); },
        sa_default_margin:   function(frm) { apply_defaults_and_recalculate(frm); },
        sa_default_customs:  function(frm) { apply_defaults_and_recalculate(frm); },
        sa_additional_discount: function(frm) { apply_defaults_and_recalculate(frm); },
        sa_shipping_rate:    function(frm) { recalculate_all_rows(frm); },
    });

    // ------------------------------------------------------------------
    // SystemAir Quotation Item child table hooks
    // ------------------------------------------------------------------
    frappe.ui.form.on('SystemAir Quotation Item', {

        item_code: function(frm, cdt, cdn) {
            var row = frappe.get_doc(cdt, cdn);
            if (!row.item_code) return;
            fetch_item_prices(frm, cdt, cdn, row.item_code);
        },

        // Per-row field changes → debounced recalculate
        ex_price:           function(frm, cdt, cdn) { debounced_recalc(frm, cdt, cdn); },
        qty:                function(frm, cdt, cdn) { debounced_recalc(frm, cdt, cdn); },
        supplier_discount:  function(frm, cdt, cdn) { debounced_recalc(frm, cdt, cdn); },
        additional_discount:function(frm, cdt, cdn) { debounced_recalc(frm, cdt, cdn); },
        customs_rate:       function(frm, cdt, cdn) { debounced_recalc(frm, cdt, cdn); },
        margin_percent:     function(frm, cdt, cdn) {
            debounced_recalc(frm, cdt, cdn);
            update_margin_color_row(frm, cdt, cdn);
        },

        form_render: function(frm, cdt, cdn) {
            update_margin_color_row(frm, cdt, cdn);
        },
    });

    // ------------------------------------------------------------------
    // Toggle SA sections
    // ------------------------------------------------------------------
    function toggle_sa_sections(frm) {
        var is_sa = !!(frm.doc.is_systemair_quotation);

        // Show/hide standard items table
        frm.toggle_display('items', !is_sa);
        frm.toggle_display('taxes_and_charges', !is_sa);

        // Show/hide SA tables (the custom fields)
        frm.toggle_display('sa_items', is_sa);
        frm.toggle_display('sa_accessories', is_sa);
        frm.toggle_display('sa_project_ref', is_sa);
        frm.toggle_display('sa_eur_egp_rate', is_sa);
        frm.toggle_display('sa_default_discount', is_sa);
        frm.toggle_display('sa_additional_discount', is_sa);
        frm.toggle_display('sa_default_margin', is_sa);
        frm.toggle_display('sa_shipping_rate', is_sa);
        frm.toggle_display('sa_default_customs', is_sa);
        frm.toggle_display('sa_total_cif_eur', is_sa);
        frm.toggle_display('sa_grand_total_egp', is_sa);
        frm.toggle_display('sa_effective_margin', is_sa);
        frm.toggle_display('print_internal', is_sa);
    }

    // ------------------------------------------------------------------
    // Load Price Config defaults into header
    // ------------------------------------------------------------------
    function load_price_config_defaults(frm) {
        frappe.call({
            method: 'kayan_systemair.api.get_price_config',
            callback: function(r) {
                if (!r.message) return;
                var cfg = r.message;
                if (!flt(frm.doc.sa_eur_egp_rate)) {
                    frm.set_value('sa_eur_egp_rate', cfg.default_currency_rate);
                }
                if (!flt(frm.doc.sa_default_margin)) {
                    frm.set_value('sa_default_margin', cfg.default_margin);
                }
                if (!flt(frm.doc.sa_shipping_rate)) {
                    frm.set_value('sa_shipping_rate', cfg.default_shipping_rate);
                }
            }
        });
    }

    // ------------------------------------------------------------------
    // Setup SA-specific toolbar buttons
    // ------------------------------------------------------------------
    function setup_sa_toolbar(frm) {
        if (frm.doc.docstatus !== 0) return;

        frm.add_custom_button(__('Add Fan Item'), function() {
            frappe.new_doc('SystemAir Fan Item');
        }, __('SystemAir'));

        frm.add_custom_button(__('Refresh Prices'), function() {
            refresh_all_prices(frm);
        }, __('SystemAir'));
    }

    // ------------------------------------------------------------------
    // Fetch prices when item_code changes on a row
    // ------------------------------------------------------------------
    function fetch_item_prices(frm, cdt, cdn, item_code) {
        frappe.call({
            method: 'kayan_systemair.api.get_item_prices',
            args: { item_code: item_code },
            callback: function(r) {
                if (!r.message) return;
                frappe.model.set_value(cdt, cdn, 'germany_list_price', flt(r.message.germany));
                frappe.model.set_value(cdt, cdn, 'malaysia_list_price', flt(r.message.malaysia));

                // Auto-fill EX price from Germany list if not already set
                var row = frappe.get_doc(cdt, cdn);
                if (!flt(row.ex_price) && r.message.germany) {
                    frappe.model.set_value(cdt, cdn, 'ex_price', flt(r.message.germany));
                }

                // Fetch item name
                frappe.db.get_value('Item', item_code, 'item_name', function(res) {
                    if (res && res.item_name) {
                        frappe.model.set_value(cdt, cdn, 'item_name', res.item_name);
                    }
                });

                debounced_recalc(frm, cdt, cdn);
            }
        });
    }

    // ------------------------------------------------------------------
    // Refresh prices for ALL rows
    // ------------------------------------------------------------------
    function refresh_all_prices(frm) {
        var rows = frm.doc.sa_items || [];
        var promises = rows.map(function(row) {
            if (!row.item_code) return Promise.resolve();
            return new Promise(function(resolve) {
                fetch_item_prices(frm, row.doctype, row.name, row.item_code);
                resolve();
            });
        });
        Promise.all(promises).then(function() {
            frappe.show_alert({ message: __('Prices refreshed'), indicator: 'green' });
        });
    }

    // ------------------------------------------------------------------
    // Apply quotation-level defaults to all rows then recalculate
    // ------------------------------------------------------------------
    function apply_defaults_and_recalculate(frm) {
        var rows = frm.doc.sa_items || [];
        rows.forEach(function(row) {
            if (flt(frm.doc.sa_default_discount) && !flt(row.supplier_discount)) {
                frappe.model.set_value(row.doctype, row.name, 'supplier_discount',
                    flt(frm.doc.sa_default_discount));
            }
            if (flt(frm.doc.sa_default_margin) && !flt(row.margin_percent)) {
                frappe.model.set_value(row.doctype, row.name, 'margin_percent',
                    flt(frm.doc.sa_default_margin));
            }
            if (flt(frm.doc.sa_default_customs) && !flt(row.customs_rate)) {
                frappe.model.set_value(row.doctype, row.name, 'customs_rate',
                    flt(frm.doc.sa_default_customs));
            }
        });
        recalculate_all_rows(frm);
    }

    // ------------------------------------------------------------------
    // Recalculate all rows
    // ------------------------------------------------------------------
    function recalculate_all_rows(frm) {
        var rows = frm.doc.sa_items || [];
        rows.forEach(function(row) {
            if (flt(row.ex_price) > 0) {
                calculate_row(frm, row.doctype, row.name);
            }
        });
    }

    // ------------------------------------------------------------------
    // Debounce helper per row
    // ------------------------------------------------------------------
    var _debounce_timers = {};
    function debounced_recalc(frm, cdt, cdn) {
        var key = cdn;
        if (_debounce_timers[key]) clearTimeout(_debounce_timers[key]);
        _debounce_timers[key] = setTimeout(function() {
            calculate_row(frm, cdt, cdn);
            delete _debounce_timers[key];
        }, 350);
    }

    // ------------------------------------------------------------------
    // Client-side 16-step calculation (mirrors pricing_engine.py)
    // ------------------------------------------------------------------
    function calculate_row(frm, cdt, cdn) {
        var row = frappe.get_doc(cdt, cdn);
        if (!row) return;

        var ex_price = flt(row.ex_price);
        if (!ex_price || ex_price <= 0) return;

        var qty = flt(row.qty) || 1;
        var supplier_discount = flt(row.supplier_discount);
        var additional_discount = flt(row.additional_discount);
        var customs_rate = flt(row.customs_rate);
        var margin_percent = flt(row.margin_percent) ||
                             flt(frm.doc.sa_default_margin) || 50;
        var shipping_rate = flt(frm.doc.sa_shipping_rate) || 12;
        var eur_egp_rate = flt(frm.doc.sa_eur_egp_rate) || 50;

        // Get combined cost factor from boot session or use default
        var cf = (frappe.boot.systemair_config && frappe.boot.systemair_config.combined_cost_factor)
                 ? flt(frappe.boot.systemair_config.combined_cost_factor) : 1.1235;
        var vat_rate = (frappe.boot.systemair_config && frappe.boot.systemair_config.vat_rate)
                       ? flt(frappe.boot.systemair_config.vat_rate) : 14;

        // Step 4
        var basic_ex = flt(ex_price * qty * (1 - supplier_discount / 100), 4);
        // Step 6
        var final_ex = flt(basic_ex * (1 - additional_discount / 100), 4);
        // Step 7
        var shipping = flt(basic_ex * (shipping_rate / 100), 4);
        // Step 8
        var cif = flt(final_ex + shipping, 4);
        // Step 11
        var vat_mult = flt(1 + vat_rate / 100, 6);
        // Step 13
        var customs_mult = flt(1 + customs_rate / 100, 6);
        var ddp = flt(cif * cf * eur_egp_rate * vat_mult * customs_mult, 2);
        // Step 15
        var margin_mult = flt(1 + margin_percent / 100, 6);
        var total_egp = flt(cif * cf * margin_mult * eur_egp_rate * vat_mult * customs_mult, 2);
        // Step 16
        var unit_egp = flt(total_egp / qty, 2);

        // Write back (silent to avoid re-triggering)
        frappe.model.set_value(cdt, cdn, 'basic_ex_price',  flt(basic_ex, 2));
        frappe.model.set_value(cdt, cdn, 'shipping_cost',   flt(shipping, 2));
        frappe.model.set_value(cdt, cdn, 'final_ex_price',  flt(final_ex, 2));
        frappe.model.set_value(cdt, cdn, 'cif',             flt(cif, 2));
        frappe.model.set_value(cdt, cdn, 'ddp_cost',        ddp);
        frappe.model.set_value(cdt, cdn, 'unit_price_egp',  unit_egp);
        frappe.model.set_value(cdt, cdn, 'total_price_egp', total_egp);
        frappe.model.set_value(cdt, cdn, 'rate',            unit_egp);
        frappe.model.set_value(cdt, cdn, 'amount',          total_egp);

        update_quotation_totals(frm);
        update_margin_color_row(frm, cdt, cdn);
    }

    // ------------------------------------------------------------------
    // Update quotation-level totals
    // ------------------------------------------------------------------
    function update_quotation_totals(frm) {
        if (!frm.doc.is_systemair_quotation) return;

        var total_cif = 0, grand_total = 0, total_ddp = 0;

        (frm.doc.sa_items || []).forEach(function(row) {
            total_cif   += flt(row.cif);
            grand_total += flt(row.total_price_egp);
            total_ddp   += flt(row.ddp_cost);
        });
        (frm.doc.sa_accessories || []).forEach(function(row) {
            grand_total += flt(row.total_price_egp);
        });

        frm.set_value('sa_total_cif_eur',   flt(total_cif, 2));
        frm.set_value('sa_grand_total_egp', flt(grand_total, 2));

        var eff_margin = (grand_total > 0)
            ? flt((grand_total - total_ddp) / grand_total * 100, 2)
            : 0;
        frm.set_value('sa_effective_margin', eff_margin);
    }

    // ------------------------------------------------------------------
    // Margin colour indicators
    // ------------------------------------------------------------------
    function apply_margin_colors(frm) {
        (frm.doc.sa_items || []).forEach(function(row) {
            update_margin_color_row(frm, row.doctype, row.name);
        });
    }

    function update_margin_color_row(frm, cdt, cdn) {
        var row = frappe.get_doc(cdt, cdn);
        if (!row) return;

        var margin = flt(row.margin_percent);
        var color_class;
        if (margin >= 40) {
            color_class = 'margin-green';
        } else if (margin >= 25) {
            color_class = 'margin-orange';
        } else {
            color_class = 'margin-red';
        }

        // Apply via DOM — target the margin_percent cell in the grid
        var grid_row = frm.fields_dict['sa_items'] &&
                       frm.fields_dict['sa_items'].grid &&
                       frm.fields_dict['sa_items'].grid.get_row(cdn);
        if (grid_row && grid_row.columns && grid_row.columns.margin_percent) {
            var $cell = grid_row.columns.margin_percent.$cell;
            if ($cell) {
                $cell.removeClass('margin-green margin-orange margin-red')
                     .addClass(color_class);
            }
        }
    }

})();
