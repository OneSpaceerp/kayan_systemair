frappe.ui.form.on("SystemAir Price Config", {
    cost_factor_1(frm) { update_combined(frm); },
    cost_factor_2(frm) { update_combined(frm); }
});

function update_combined(frm) {
    let cf1 = parseFloat(frm.doc.cost_factor_1) || 0;
    let cf2 = parseFloat(frm.doc.cost_factor_2) || 0;
    frm.set_value("combined_cost_factor", cf1 * cf2);
}
