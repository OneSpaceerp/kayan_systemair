/**
 * quotation_extend.js
 * ===================
 * Global client-side extension for the standard Quotation DocType.
 * Loaded on every desk page via app_include_js in hooks.py.
 *
 * Features:
 *  - Toggle SA sections on/off based on is_systemair_quotation flag
 *  - Debounced per-row recalculation (preview only; server recalculates on save)
 *  - Two-pass shipping allocation: Percent of Basic (default) or Lump Sum
 *  - Header-level defaults propagation
 *  - Article number → auto-fill item, prices, fan_type, origin, smoke_rating
 *  - item_code change → back-fill article_no + same attributes
 *  - Accessory table: article_no / item_code → auto-fetch Germany price
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
                recalculate_all_rows(frm);
                update_quotation_totals(frm);
            }
        },

        validate: function(frm) {
            if (frm.doc.is_systemair_quotation) {
                (frm.doc.items || []).forEach(function(row) {
                    if (!row.item_name) row.item_name = row.item_code || 'Item';
                    if (!row.uom) row.uom = 'Nos';
                    if (!row.qty) row.qty = 1;
                    if (!row.conversion_factor) row.conversion_factor = 1;
                    if (row.ordered_qty == null) row.ordered_qty = 0;
                });
                if (!(frm.doc.items || []).length) {
                    var sa_items = (frm.doc.sa_items || []).filter(function(r) {
                        return r.item_code;
                    });
                    if (sa_items.length > 0) {
                        var first = sa_items[0];
                        var row = frm.add_child('items');
                        row.item_code = first.item_code;
                        row.item_name = first.item_name || first.item_code;
                        row.uom = 'Nos';
                        row.qty = flt(first.qty) || 1;
                        row.rate = flt(first.unit_price_egp) || 0;
                        row.conversion_factor = 1;
                        row.ordered_qty = 0;
                    }
                }
            }
        },

        is_systemair_quotation: function(frm) {
            toggle_sa_sections(frm);
            if (frm.doc.is_systemair_quotation) {
                if (!flt(frm.doc.sa_eur_egp_rate)) {
                    load_price_config_defaults(frm);
                }
                setup_sa_toolbar(frm);
            }
        },

        // Header-level field changes → recalculate all rows
        sa_eur_egp_rate:          function(frm) { recalculate_all_rows(frm); },
        sa_default_discount:      function(frm) { apply_defaults_and_recalculate(frm); },
        sa_default_margin:        function(frm) { apply_defaults_and_recalculate(frm); },
        sa_default_customs:       function(frm) { apply_defaults_and_recalculate(frm); },
        sa_additional_discount:   function(frm) { apply_defaults_and_recalculate(frm); },
        sa_shipping_rate:         function(frm) { recalculate_all_rows(frm); },
        sa_shipping_mode:         function(frm) {
            frm.toggle_display('sa_shipping_rate',
                frm.doc.sa_shipping_mode !== 'Lump Sum');
            frm.toggle_display('sa_total_shipping_eur',
                frm.doc.sa_shipping_mode === 'Lump Sum');
            recalculate_all_rows(frm);
        },
        sa_total_shipping_eur:    function(frm) { recalculate_all_rows(frm); },
    });

    // ------------------------------------------------------------------
    // SystemAir Quotation Item child table hooks
    // ------------------------------------------------------------------
    frappe.ui.form.on('SystemAir Quotation Item', {

        sa_article_no: function(frm, cdt, cdn) {
            var row = frappe.get_doc(cdt, cdn);
            if (!row.sa_article_no) return;
            lookup_by_article_no(frm, cdt, cdn, row.sa_article_no);
        },

        item_code: function(frm, cdt, cdn) {
            var row = frappe.get_doc(cdt, cdn);
            if (!row.item_code) return;
            fetch_item_prices(frm, cdt, cdn, row.item_code);
        },

        // Per-row field changes → debounced recalculate
        ex_price:            function(frm, cdt, cdn) { debounced_recalc(frm, cdt, cdn); },
        qty:                 function(frm, cdt, cdn) { debounced_recalc(frm, cdt, cdn); },
        supplier_discount:   function(frm, cdt, cdn) { debounced_recalc(frm, cdt, cdn); },
        additional_discount: function(frm, cdt, cdn) { debounced_recalc(frm, cdt, cdn); },
        customs_rate:        function(frm, cdt, cdn) { debounced_recalc(frm, cdt, cdn); },
        margin_percent:      function(frm, cdt, cdn) {
            debounced_recalc(frm, cdt, cdn);
            update_margin_color_row(frm, cdt, cdn);
        },

        form_render: function(frm, cdt, cdn) {
            update_margin_color_row(frm, cdt, cdn);
        },
    });

    // ------------------------------------------------------------------
    // SystemAir Accessory Item child table hooks (§6)
    // ------------------------------------------------------------------
    frappe.ui.form.on('SystemAir Accessory Item', {

        sa_article_no: function(frm, cdt, cdn) {
            var row = frappe.get_doc(cdt, cdn);
            if (!row.sa_article_no) return;
            lookup_accessory_by_article_no(frm, cdt, cdn, row.sa_article_no);
        },

        item_code: function(frm, cdt, cdn) {
            var row = frappe.get_doc(cdt, cdn);
            if (!row.item_code) return;
            fetch_accessory_price_by_item(frm, cdt, cdn, row.item_code);
        },
    });

    // ------------------------------------------------------------------
    // Toggle SA sections
    // ------------------------------------------------------------------
    function toggle_sa_sections(frm) {
        var is_sa = !!(frm.doc.is_systemair_quotation);

        frm.toggle_display('items',              !is_sa);
        frm.toggle_display('taxes_and_charges',  !is_sa);

        frm.toggle_display('sa_items',               is_sa);
        frm.toggle_display('sa_accessories',         is_sa);
        frm.toggle_display('sa_project_ref',         is_sa);
        frm.toggle_display('sa_eur_egp_rate',        is_sa);
        frm.toggle_display('sa_default_discount',    is_sa);
        frm.toggle_display('sa_additional_discount', is_sa);
        frm.toggle_display('sa_default_margin',      is_sa);
        frm.toggle_display('sa_shipping_mode',       is_sa);
        frm.toggle_display('sa_shipping_rate',
            is_sa && frm.doc.sa_shipping_mode !== 'Lump Sum');
        frm.toggle_display('sa_total_shipping_eur',
            is_sa && frm.doc.sa_shipping_mode === 'Lump Sum');
        frm.toggle_display('sa_flow_unit',           is_sa);
        frm.toggle_display('sa_esp_unit',            is_sa);
        frm.toggle_display('sa_default_customs',     is_sa);
        frm.toggle_display('sa_total_cif_eur',       is_sa);
        frm.toggle_display('sa_total_basic_eur',     is_sa);
        frm.toggle_display('sa_total_ddp_egp',       is_sa);
        frm.toggle_display('sa_grand_total_egp',     is_sa);
        frm.toggle_display('sa_effective_margin',    is_sa);
        frm.toggle_display('print_internal',         is_sa);
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
    // Article number → look up item + fill prices, fan_type, origin,
    //                   smoke_rating, ex_price (§2 auto-fill)
    // ------------------------------------------------------------------
    function lookup_by_article_no(frm, cdt, cdn, article_no) {
        frappe.call({
            method: 'kayan_systemair.api.get_article_details',
            args: { article_no: article_no },
            callback: function(r) {
                if (!r.message) return;
                var d = r.message;
                frappe.model.set_value(cdt, cdn, 'item_code',          d.item_code);
                frappe.model.set_value(cdt, cdn, 'item_name',          d.item_name);
                frappe.model.set_value(cdt, cdn, 'germany_list_price',  flt(d.germany_list_price));
                frappe.model.set_value(cdt, cdn, 'malaysia_list_price', flt(d.malaysia_list_price));

                var row = frappe.get_doc(cdt, cdn);

                // Fan attribute auto-fill (only if empty, user override wins)
                if (!row.fan_type && d.type_of_fan) {
                    var mt = _map_type_of_fan(d.type_of_fan);
                    if (mt) frappe.model.set_value(cdt, cdn, 'fan_type', mt);
                }
                if (!row.origin && d.primary_factory) {
                    var mo = _map_factory_to_origin(d.primary_factory);
                    if (mo) frappe.model.set_value(cdt, cdn, 'origin', mo);
                }
                if (!row.smoke_rating) {
                    var ms = _map_temperature_to_smoke(d.temperature_rate || '');
                    if (ms) frappe.model.set_value(cdt, cdn, 'smoke_rating', ms);
                }

                // Default EX price: Malaysia first, Germany fallback
                if (!flt(row.ex_price)) {
                    var ex = flt(d.malaysia_list_price) || flt(d.germany_list_price);
                    if (ex) frappe.model.set_value(cdt, cdn, 'ex_price', ex);
                }
                debounced_recalc(frm, cdt, cdn);
            }
        });
    }

    // ------------------------------------------------------------------
    // item_code change → fetch prices + back-fill article_no + attributes
    // ------------------------------------------------------------------
    function fetch_item_prices(frm, cdt, cdn, item_code) {
        frappe.call({
            method: 'kayan_systemair.api.get_item_prices',
            args: { item_code: item_code },
            callback: function(r) {
                if (!r.message) return;
                frappe.model.set_value(cdt, cdn, 'germany_list_price', flt(r.message.germany));
                frappe.model.set_value(cdt, cdn, 'malaysia_list_price', flt(r.message.malaysia));

                var row = frappe.get_doc(cdt, cdn);
                if (!flt(row.ex_price)) {
                    var ex = flt(r.message.malaysia) || flt(r.message.germany);
                    if (ex) frappe.model.set_value(cdt, cdn, 'ex_price', ex);
                }

                // Back-fill article_no and fan attributes from Item master
                frappe.db.get_value('Item', item_code,
                    ['item_name', 'sa_article_no', 'sa_type_of_fan', 'sa_primary_factory', 'sa_temperature_rate'],
                    function(res) {
                        if (!res) return;
                        if (res.item_name) {
                            frappe.model.set_value(cdt, cdn, 'item_name', res.item_name);
                        }
                        var cur = frappe.get_doc(cdt, cdn);
                        if (res.sa_article_no && !cur.sa_article_no) {
                            frappe.model.set_value(cdt, cdn, 'sa_article_no', res.sa_article_no);
                        }
                        if (!cur.fan_type && res.sa_type_of_fan) {
                            var mt = _map_type_of_fan(res.sa_type_of_fan);
                            if (mt) frappe.model.set_value(cdt, cdn, 'fan_type', mt);
                        }
                        if (!cur.origin && res.sa_primary_factory) {
                            var mo = _map_factory_to_origin(res.sa_primary_factory);
                            if (mo) frappe.model.set_value(cdt, cdn, 'origin', mo);
                        }
                        if (!cur.smoke_rating) {
                            var ms = _map_temperature_to_smoke(res.sa_temperature_rate || '');
                            if (ms) frappe.model.set_value(cdt, cdn, 'smoke_rating', ms);
                        }
                    }
                );

                debounced_recalc(frm, cdt, cdn);
            }
        });
    }

    // ------------------------------------------------------------------
    // Accessory article_no → fetch item + Germany price (§6)
    // ------------------------------------------------------------------
    function lookup_accessory_by_article_no(frm, cdt, cdn, article_no) {
        frappe.call({
            method: 'kayan_systemair.api.get_article_details',
            args: { article_no: article_no },
            callback: function(r) {
                if (!r.message) return;
                var d = r.message;
                if (d.item_code) frappe.model.set_value(cdt, cdn, 'item_code',      d.item_code);
                if (d.item_name) frappe.model.set_value(cdt, cdn, 'accessory_name', d.item_name);
                var price = flt(d.germany_list_price) || flt(d.malaysia_list_price);
                if (price)      frappe.model.set_value(cdt, cdn, 'unit_price_eur',  price);
                update_quotation_totals(frm);
            }
        });
    }

    // ------------------------------------------------------------------
    // Accessory item_code → fetch Germany price + back-fill name/article
    // ------------------------------------------------------------------
    function fetch_accessory_price_by_item(frm, cdt, cdn, item_code) {
        frappe.call({
            method: 'kayan_systemair.api.get_item_prices',
            args: { item_code: item_code },
            callback: function(r) {
                if (!r.message) return;
                var price = flt(r.message.germany) || flt(r.message.malaysia);
                if (price) frappe.model.set_value(cdt, cdn, 'unit_price_eur', price);

                frappe.db.get_value('Item', item_code, ['item_name', 'sa_article_no'], function(res) {
                    if (!res) return;
                    if (res.item_name) {
                        frappe.model.set_value(cdt, cdn, 'accessory_name', res.item_name);
                    }
                    if (res.sa_article_no) {
                        var cur = frappe.get_doc(cdt, cdn);
                        if (!cur.sa_article_no) {
                            frappe.model.set_value(cdt, cdn, 'sa_article_no', res.sa_article_no);
                        }
                    }
                });
                update_quotation_totals(frm);
            }
        });
    }

    // ------------------------------------------------------------------
    // Refresh prices for ALL rows
    // ------------------------------------------------------------------
    function refresh_all_prices(frm) {
        (frm.doc.sa_items || []).forEach(function(row) {
            if (row.item_code) {
                fetch_item_prices(frm, row.doctype, row.name, row.item_code);
            }
        });
        frappe.show_alert({ message: __('Prices refreshed'), indicator: 'green' });
    }

    // ------------------------------------------------------------------
    // Apply quotation-level defaults to all rows then recalculate
    // ------------------------------------------------------------------
    function apply_defaults_and_recalculate(frm) {
        var rows = frm.doc.sa_items || [];
        rows.forEach(function(row) {
            if (flt(frm.doc.sa_default_discount) > 0) {
                frappe.model.set_value(row.doctype, row.name, 'supplier_discount',
                    flt(frm.doc.sa_default_discount));
            }
            if (flt(frm.doc.sa_default_margin) > 0) {
                frappe.model.set_value(row.doctype, row.name, 'margin_percent',
                    flt(frm.doc.sa_default_margin));
            }
            if (flt(frm.doc.sa_default_customs) > 0) {
                frappe.model.set_value(row.doctype, row.name, 'customs_rate',
                    flt(frm.doc.sa_default_customs));
            }
        });
        recalculate_all_rows(frm);
    }

    // ------------------------------------------------------------------
    // Two-pass shipping allocation + per-row calculation (§3)
    //
    // Percent of Basic: shipping_i = basic_i × rate / 100
    //   → reduces to the current per-row flat-rate formula
    // Lump Sum:         shipping_i = basic_i × total_shipping / Σbasic
    //   → requires all basics first (pass 1), then allocate (pass 2)
    // ------------------------------------------------------------------
    function recalculate_all_rows(frm) {
        var rows = frm.doc.sa_items || [];
        var mode = frm.doc.sa_shipping_mode || 'Percent of Basic';
        var allocations = {};

        if (mode === 'Lump Sum') {
            var total_basic = 0;
            var basics = {};
            var total_shipping = flt(frm.doc.sa_total_shipping_eur) || 0;

            rows.forEach(function(row) {
                var ex = flt(row.ex_price);
                if (!ex) { basics[row.name] = 0; return; }
                var b = flt(ex * (flt(row.qty) || 1) * (1 - flt(row.supplier_discount) / 100));
                basics[row.name] = b;
                total_basic += b;
            });

            rows.forEach(function(row) {
                allocations[row.name] = total_basic > 0
                    ? flt(basics[row.name] * total_shipping / total_basic, 4)
                    : 0;
            });
        }

        rows.forEach(function(row) {
            if (flt(row.ex_price) > 0) {
                calculate_row(frm, row.doctype, row.name,
                    mode === 'Lump Sum' ? allocations[row.name] : null);
            }
        });
    }

    // ------------------------------------------------------------------
    // Debounce helper per row
    // In Lump Sum mode, recalculate all rows (shipping is interdependent)
    // ------------------------------------------------------------------
    var _debounce_timers = {};
    function debounced_recalc(frm, cdt, cdn) {
        var key = cdn;
        if (_debounce_timers[key]) clearTimeout(_debounce_timers[key]);
        _debounce_timers[key] = setTimeout(function() {
            var mode = frm.doc.sa_shipping_mode || 'Percent of Basic';
            if (mode === 'Lump Sum') {
                recalculate_all_rows(frm);
            } else {
                calculate_row(frm, cdt, cdn, null);
            }
            delete _debounce_timers[key];
        }, 350);
    }

    // ------------------------------------------------------------------
    // Client-side pricing chain (mirrors pricing_engine.py)
    //   allocated_shipping: pre-computed EUR value (lump-sum mode)
    //                       or null (percent mode → compute from rate)
    // ------------------------------------------------------------------
    function calculate_row(frm, cdt, cdn, allocated_shipping) {
        var row = frappe.get_doc(cdt, cdn);
        if (!row) return;

        var ex_price = flt(row.ex_price);
        if (!ex_price || ex_price <= 0) return;

        var qty              = flt(row.qty) || 1;
        var supplier_disc    = flt(row.supplier_discount);
        var additional_disc  = flt(row.additional_discount);
        var customs_rate     = flt(row.customs_rate);
        var margin_percent   = flt(row.margin_percent) || flt(frm.doc.sa_default_margin) || 50;
        var shipping_rate    = flt(frm.doc.sa_shipping_rate) || 12;
        var eur_egp_rate     = flt(frm.doc.sa_eur_egp_rate) || 50;

        var cf = (frappe.boot.systemair_config && frappe.boot.systemair_config.combined_cost_factor)
                 ? flt(frappe.boot.systemair_config.combined_cost_factor) : 1.1235;
        var vat_rate = (frappe.boot.systemair_config && frappe.boot.systemair_config.vat_rate)
                       ? flt(frappe.boot.systemair_config.vat_rate) : 14;

        // Step 4 — Basic EX
        var basic_ex = flt(ex_price * qty * (1 - supplier_disc / 100), 4);
        // Step 6 — Final EX
        var final_ex = flt(basic_ex * (1 - additional_disc / 100), 4);
        // Step 7 — Shipping
        var shipping;
        if (allocated_shipping !== null && allocated_shipping !== undefined) {
            shipping = flt(allocated_shipping, 4);
        } else {
            shipping = flt(basic_ex * (shipping_rate / 100), 4);
        }
        // Step 8 — CIF
        var cif = flt(final_ex + shipping, 4);
        // Steps 11-13
        var vat_mult     = flt(1 + vat_rate / 100, 6);
        var customs_mult = flt(1 + customs_rate / 100, 6);
        var ddp          = flt(cif * cf * eur_egp_rate * vat_mult * customs_mult, 2);
        // Steps 14-16
        var margin_mult  = flt(1 + margin_percent / 100, 6);
        var total_egp    = flt(cif * cf * margin_mult * eur_egp_rate * vat_mult * customs_mult, 2);
        var unit_egp     = flt(total_egp / qty, 2);

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
    // Update quotation-level totals (mirrors Excel row 2 mirror block)
    // ------------------------------------------------------------------
    function update_quotation_totals(frm) {
        if (!frm.doc.is_systemair_quotation) return;

        var total_basic = 0, total_cif = 0, total_ddp = 0, grand_total = 0;

        (frm.doc.sa_items || []).forEach(function(row) {
            total_basic  += flt(row.basic_ex_price);
            total_cif    += flt(row.cif);
            total_ddp    += flt(row.ddp_cost);
            grand_total  += flt(row.total_price_egp);
        });
        (frm.doc.sa_accessories || []).forEach(function(row) {
            grand_total += flt(row.total_price_egp);
        });

        var eff_margin = (grand_total > 0)
            ? flt((grand_total - total_ddp) / grand_total * 100, 2)
            : 0;

        frm.doc.sa_total_basic_eur  = flt(total_basic, 2);
        frm.doc.sa_total_cif_eur    = flt(total_cif, 2);
        frm.doc.sa_total_ddp_egp    = flt(total_ddp, 2);
        frm.doc.sa_grand_total_egp  = flt(grand_total, 2);
        frm.doc.sa_effective_margin = eff_margin;

        frm.refresh_field('sa_total_basic_eur');
        frm.refresh_field('sa_total_cif_eur');
        frm.refresh_field('sa_total_ddp_egp');
        frm.refresh_field('sa_grand_total_egp');
        frm.refresh_field('sa_effective_margin');
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
        var color_class = margin >= 40 ? 'margin-green'
                        : margin >= 25 ? 'margin-orange'
                        : 'margin-red';

        var grid_row = frm.fields_dict['sa_items'] &&
                       frm.fields_dict['sa_items'].grid &&
                       frm.fields_dict['sa_items'].grid.get_row(cdn);
        if (grid_row && grid_row.columns && grid_row.columns.margin_percent) {
            var $cell = grid_row.columns.margin_percent.$cell;
            if ($cell) {
                $cell.removeClass('margin-green margin-orange margin-red').addClass(color_class);
            }
        }
    }

    // ------------------------------------------------------------------
    // Attribute mapping helpers
    // ------------------------------------------------------------------

    // Map Item.sa_type_of_fan → quotation row fan_type Select options
    function _map_type_of_fan(val) {
        if (!val) return '';
        var lc = val.toLowerCase().trim();
        var m = {
            'centrifugal fan':      'Centrifugal Fan',
            'centrifugal roof top': 'Centrifugal Roof Top',
            'inline fan':           'Inline Fan',
            'axial inline':         'Axial Inline',
            'wall mounted':         'Wall Mounted',
            'induction jet fan':    'Induction Jet Fan',
            'impulse jet fan':      'Impulse Jet Fan',
            'impulse jet fan':      'Impulse Jet Fan',
            'accessories':          'Accessories',
            'centrifugal box fan':  'Centrifugal Box Fan',
        };
        return m[lc] || '';
    }

    // Map Item.sa_primary_factory → quotation row origin Select options
    function _map_factory_to_origin(val) {
        if (!val) return '';
        var lc = val.toLowerCase().trim();
        var m = {
            'germany':            'Germany',
            'sweden':             'Sweden',
            'malaysia':           'Malaysia',
            'malaysia and india': 'Malaysia',
            'slovenia':           'Slovenia',
            'china':              'China',
            'italy':              'Italy',
            'uae':                'UAE',
            'egypt':              'Egypt',
            'turkey':             'Turkey',
            'ukraine':            'Ukraine',
        };
        return m[lc] || '';
    }

    // Map Item.sa_temperature_rate → quotation row smoke_rating Select options
    // Spec: none → Ambient; explicit values map 1:1 with case adjustment
    function _map_temperature_to_smoke(val) {
        if (!val) return 'Ambient';
        var lc = val.toLowerCase().trim();
        var m = {
            '300°c/2hr':          '300°C/2Hr',
            '400°c/2hr':          '400°C/2Hr',
            '120°c continuous':   '120°C',
            'explosion proof':    'Explosion',
            '600°c/2hr':          '',  // no matching smoke_rating option
        };
        if (lc in m) return m[lc] || 'Ambient';
        return 'Ambient';
    }

})();
