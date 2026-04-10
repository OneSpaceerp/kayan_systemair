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
                    method: "kayan_systemair.kayan_systemair.doctype.systemair_fan_item.systemair_fan_item.create_item_from_doc",
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
            frm.set_intro(__("New item \u2014 submit to register in ERPNext."), "orange");
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
    frappe.call({
        method: "kayan_systemair.api.get_weight_for_diameter",
        args: { diameter: frm.doc.nominal_diameter },
        callback(r) {
            if (r.message && r.message.max_weight_kg) {
                frm.set_value("approx_weight", r.message.max_weight_kg);
            }
        }
    });
}
