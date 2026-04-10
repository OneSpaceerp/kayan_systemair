frappe.pages['price-list-import'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('Price List Import'),
        single_column: true
    });

    $(wrapper).bind('show', function() {
        setup_page(page);
    });
};

function setup_page(page) {
    page.main.html(`
        <div class="price-list-import-container" style="padding: 15px;">
            <p>${__('Upload the SystemAir EX Price List (Excel).')}</p>
            <div class="row">
                <div class="col-md-4">
                    <div class="form-group">
                        <label>${__('Price List Name')}</label>
                        <select id="sa_price_list" class="form-control">
                            <option value="Systemair Germany 2026">Systemair Germany 2026</option>
                            <option value="Systemair Malaysia 2026">Systemair Malaysia 2026</option>
                        </select>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="form-group">
                        <label>${__('Sheet Name')}</label>
                        <input type="text" id="sa_sheet_name" class="form-control" value="Germany">
                    </div>
                </div>
            </div>
            
            <button class="btn btn-primary" id="btn-upload-price-list">${__('Upload & Import')}</button>
            <div id="import-status" style="margin-top: 20px;"></div>
        </div>
    `);

    page.main.find('#btn-upload-price-list').on('click', function() {
        let price_list = page.main.find('#sa_price_list').val();
        let sheet = page.main.find('#sa_sheet_name').val();

        new frappe.ui.FileUploader({
            allow_multiple: false,
            on_success: (file) => {
                frappe.call({
                    method: 'kayan_systemair.kayan_systemair.page.price_list_import.price_list_import.import_price_list',
                    args: {
                        file_content: file.file_url, // For real usage, you'd fetch the file bytes/content
                        price_list_name: price_list,
                        sheet_name: sheet
                    },
                    callback: (r) => {
                        if(r.message) {
                            frappe.msgprint(r.message.message);
                            page.main.find('#import-status').html(`<div class="alert alert-success">${r.message.message}</div>`);
                        }
                    }
                });
            }
        });
    });
}
