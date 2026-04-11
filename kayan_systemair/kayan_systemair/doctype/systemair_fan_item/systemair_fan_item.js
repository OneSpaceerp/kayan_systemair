// SystemAir Fan Item — Client-Side Controller
// Provides live model code preview, item existence check, price/weight auto-fetch.

frappe.ui.form.on('SystemAir Fan Item', {

    // -----------------------------------------------------------------------
    // Form lifecycle
    // -----------------------------------------------------------------------
    refresh: function(frm) {
        set_form_banners(frm);
        setup_create_item_button(frm);
    },

    // -----------------------------------------------------------------------
    // Type-key field triggers — all rebuild model code on change
    // -----------------------------------------------------------------------
    fan_model:         function(frm) { update_model_code(frm); },
    nominal_diameter:  function(frm) {
        update_model_code(frm);
        fetch_weight(frm);
    },
    num_blades:        function(frm) { update_model_code(frm); },
    blade_angle:       function(frm) { update_model_code(frm); },
    num_poles:         function(frm) { update_model_code(frm); },
    smoke_rating:      function(frm) { update_model_code(frm); },
    guide_vane:        function(frm) { update_model_code(frm); },
    plus_impeller:     function(frm) { update_model_code(frm); },
    medium_casing:     function(frm) { update_model_code(frm); },
    reversible:        function(frm) { update_model_code(frm); },
    config_suffix:     function(frm) { update_model_code(frm); },
});

// -----------------------------------------------------------------------
// Model code assembly (mirrors Python assemble_model_code exactly)
// -----------------------------------------------------------------------
function update_model_code(frm) {
    var d = frm.doc;
    if (!d.fan_model || !d.nominal_diameter || !d.num_blades || !d.blade_angle || !d.num_poles) {
        return;
    }

    var code = d.fan_model + ' ' + d.nominal_diameter;
    code += '-' + d.num_blades + '/' + d.blade_angle + '\u00b0';
    code += '-' + d.num_poles;

    if (d.smoke_rating && d.smoke_rating !== 'None') {
        code += '(' + d.smoke_rating + ')';
    }
    if (d.guide_vane) {
        code += '-PV';
    }
    if (d.medium_casing) {
        code += ' MC';
    }
    if (d.config_suffix && d.config_suffix !== 'None') {
        code += d.config_suffix;
    }
    if (d.reversible) {
        code += '-TR';
    }

    frm.set_value('model_code', code);
    check_item_exists(frm, code);
}

// -----------------------------------------------------------------------
// Item existence check
// -----------------------------------------------------------------------
function check_item_exists(frm, model_code) {
    if (!model_code) return;

    frappe.call({
        method: 'kayan_systemair.api.check_item_exists',
        args: { model_code: model_code },
        callback: function(r) {
            var exists = !!(r.message);
            frm.set_value('item_exists', exists ? 1 : 0);
            if (exists) {
                frm.set_value('erp_item', r.message);
            } else {
                frm.set_value('erp_item', '');
            }
            set_form_banners(frm);
            if (exists) {
                fetch_prices(frm, model_code);
            }
        }
    });
}

// -----------------------------------------------------------------------
// Price fetch
// -----------------------------------------------------------------------
function fetch_prices(frm, model_code) {
    if (!model_code) return;
    frappe.call({
        method: 'kayan_systemair.api.get_item_prices',
        args: { item_code: model_code },
        callback: function(r) {
            if (r.message) {
                frm.set_value('germany_price', r.message.germany || 0);
                frm.set_value('malaysia_price', r.message.malaysia || 0);
            }
        }
    });
}

// -----------------------------------------------------------------------
// Weight fetch
// -----------------------------------------------------------------------
function fetch_weight(frm) {
    var diameter = frm.doc.nominal_diameter;
    if (!diameter) return;
    frappe.call({
        method: 'kayan_systemair.api.get_weight_for_diameter',
        args: { diameter: diameter },
        callback: function(r) {
            if (r.message && r.message.min_weight_kg !== undefined) {
                var mid = (flt(r.message.min_weight_kg) + flt(r.message.max_weight_kg)) / 2.0;
                frm.set_value('approx_weight', flt(mid, 2));
            }
        }
    });
}

// -----------------------------------------------------------------------
// Banner management
// -----------------------------------------------------------------------
function set_form_banners(frm) {
    frm.dashboard.clear_headline();
    if (frm.doc.item_exists) {
        frm.dashboard.set_headline_alert(
            __('Item <b>{0}</b> already exists in ERPNext.', [frm.doc.model_code || '']),
            'blue'
        );
    } else if (frm.doc.model_code) {
        frm.dashboard.set_headline_alert(
            __('New item — submit this document to register <b>{0}</b> in ERPNext.', [frm.doc.model_code]),
            'orange'
        );
    }
}

// -----------------------------------------------------------------------
// "Create ERPNext Item" button — only on submitted docs where item doesn't exist
// -----------------------------------------------------------------------
function setup_create_item_button(frm) {
    if (frm.doc.docstatus === 1 && !frm.doc.item_exists) {
        frm.add_custom_button(__('Create ERPNext Item'), function() {
            frappe.confirm(
                __('Create ERPNext Item <b>{0}</b> now?', [frm.doc.model_code]),
                function() {
                    frappe.call({
                        method: 'frappe.client.submit',
                        // The item is created server-side on_submit; if somehow missed, re-trigger:
                        args: { doc: frm.doc },
                        callback: function() {
                            frm.reload_doc();
                        }
                    });
                }
            );
        }, __('Actions'));
    }
}
