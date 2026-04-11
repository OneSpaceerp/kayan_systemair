frappe.ui.form.on('SystemAir Price Config', {
    cost_factor_1: function(frm) {
        update_combined_cost_factor(frm);
    },
    cost_factor_2: function(frm) {
        update_combined_cost_factor(frm);
    },
    refresh: function(frm) {
        update_combined_cost_factor(frm);
        frm.set_intro(
            __('These settings control the global pricing defaults for all SystemAir quotations. ' +
               'Changes take effect immediately for new quotations.'),
            'blue'
        );
    }
});

function update_combined_cost_factor(frm) {
    var cf1 = flt(frm.doc.cost_factor_1);
    var cf2 = flt(frm.doc.cost_factor_2);
    if (cf1 && cf2) {
        frm.set_value('combined_cost_factor', flt(cf1 * cf2, 6));
    }
}
