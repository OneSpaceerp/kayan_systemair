frappe.pages['price-list-import'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('SystemAir Price List Import'),
        single_column: true
    });

    new PriceListImportPage(page, wrapper);
};

PriceListImportPage = class PriceListImportPage {
    constructor(page, wrapper) {
        this.page = page;
        this.wrapper = wrapper;
        this.file_url = null;
        this.selected_price_list = null;
        this.sheet_name = null;
        this.setup();
    }

    setup() {
        this.render_layout();
        this.bind_events();
        this.load_price_lists();
    }

    render_layout() {
        $(this.wrapper).find('.layout-main-section').html(`
            <div class="sa-import-page" style="max-width: 900px; margin: 0 auto; padding: 20px;">

                <!-- Step 1: Select Price List -->
                <div class="card mb-4" style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px;">
                    <h5 style="color: #1a73e8; margin-bottom: 15px;">
                        <i class="fa fa-list"></i> ${__('Step 1: Select Target Price List')}
                    </h5>
                    <div class="form-group">
                        <label>${__('Price List')}</label>
                        <select id="price-list-select" class="form-control" style="max-width: 400px;">
                            <option value="">${__('-- Select Price List --')}</option>
                        </select>
                    </div>
                </div>

                <!-- Step 2: Upload File -->
                <div class="card mb-4" style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px;">
                    <h5 style="color: #1a73e8; margin-bottom: 15px;">
                        <i class="fa fa-upload"></i> ${__('Step 2: Upload Excel File (.xlsx)')}
                    </h5>
                    <div class="form-group">
                        <input type="file" id="excel-file-input" accept=".xlsx" class="form-control-file">
                        <small class="text-muted">${__('Accepted format: SystemAir price list .xlsx file (Germany or Malaysia)')}</small>
                    </div>
                    <button id="btn-preview" class="btn btn-default mt-2" disabled>
                        <i class="fa fa-eye"></i> ${__('Preview (first 20 rows)')}
                    </button>
                </div>

                <!-- Preview Table -->
                <div id="preview-section" style="display:none;" class="card mb-4"
                     style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px;">
                    <h5 style="color: #1a73e8; margin-bottom: 15px;">
                        <i class="fa fa-table"></i> ${__('Preview')}
                    </h5>
                    <div id="preview-info" class="text-muted mb-2"></div>
                    <div class="table-responsive">
                        <table class="table table-bordered table-sm">
                            <thead id="preview-thead" class="thead-light"></thead>
                            <tbody id="preview-tbody"></tbody>
                        </table>
                    </div>
                    <button id="btn-import" class="btn btn-primary mt-3">
                        <i class="fa fa-cloud-upload"></i> ${__('Start Import (Background Job)')}
                    </button>
                </div>

                <!-- Import Progress -->
                <div id="import-status-section" style="display:none;" class="card mb-4"
                     style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px;">
                    <h5 style="color: #1a73e8; margin-bottom: 15px;">
                        <i class="fa fa-spinner fa-spin"></i> ${__('Import Status')}
                    </h5>
                    <div id="import-status-content"></div>
                </div>

                <!-- Recent Import Logs -->
                <div class="card" style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px;">
                    <h5 style="color: #1a73e8; margin-bottom: 15px;">
                        <i class="fa fa-history"></i> ${__('Recent Import Logs')}
                    </h5>
                    <div id="import-logs-section">
                        <em class="text-muted">${__('Loading...')}</em>
                    </div>
                </div>

            </div>
        `);

        this.load_recent_logs();
    }

    bind_events() {
        var me = this;

        // Price list selector
        $(this.wrapper).on('change', '#price-list-select', function() {
            me.selected_price_list = $(this).val();
            me.check_ready_to_preview();
        });

        // File input
        $(this.wrapper).on('change', '#excel-file-input', function(e) {
            var file = e.target.files[0];
            if (file) {
                me.upload_file(file);
            }
        });

        // Preview button
        $(this.wrapper).on('click', '#btn-preview', function() {
            me.preview_file();
        });

        // Import button
        $(this.wrapper).on('click', '#btn-import', function() {
            me.start_import();
        });
    }

    load_price_lists() {
        var me = this;
        frappe.call({
            method: 'kayan_systemair.kayan_systemair.page.price_list_import.price_list_import.get_price_lists',
            callback: function(r) {
                if (r.message) {
                    var select = $(me.wrapper).find('#price-list-select');
                    r.message.forEach(function(pl) {
                        select.append(`<option value="${pl.name}">${pl.price_list_name} (${pl.currency})</option>`);
                    });
                }
            }
        });
    }

    upload_file(file) {
        var me = this;
        var formData = new FormData();
        formData.append('file', file, file.name);
        formData.append('is_private', '1');
        formData.append('folder', 'Home/Attachments');

        frappe.ui.set_route('');
        frappe.show_progress(__('Uploading...'), 0, 100);

        $.ajax({
            url: '/api/method/upload_file',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            headers: {
                'X-Frappe-CSRF-Token': frappe.csrf_token
            },
            xhr: function() {
                var xhr = new XMLHttpRequest();
                xhr.upload.onprogress = function(e) {
                    if (e.lengthComputable) {
                        frappe.show_progress(__('Uploading...'), e.loaded, e.total);
                    }
                };
                return xhr;
            },
            success: function(r) {
                frappe.hide_progress();
                if (r.message && r.message.file_url) {
                    me.file_url = r.message.file_url;
                    frappe.show_alert({message: __('File uploaded successfully'), indicator: 'green'});
                    me.check_ready_to_preview();
                } else {
                    frappe.show_alert({message: __('Upload failed'), indicator: 'red'});
                }
            },
            error: function() {
                frappe.hide_progress();
                frappe.show_alert({message: __('Upload failed'), indicator: 'red'});
            }
        });
    }

    check_ready_to_preview() {
        var ready = this.file_url && this.selected_price_list;
        $(this.wrapper).find('#btn-preview').prop('disabled', !ready);
    }

    preview_file() {
        var me = this;
        if (!me.file_url || !me.selected_price_list) {
            frappe.show_alert({message: __('Please select a price list and upload a file first'), indicator: 'orange'});
            return;
        }

        frappe.call({
            method: 'kayan_systemair.kayan_systemair.page.price_list_import.price_list_import.preview_excel',
            args: {
                file_url: me.file_url,
                price_list: me.selected_price_list
            },
            freeze: true,
            freeze_message: __('Reading Excel file...'),
            callback: function(r) {
                if (r.message) {
                    me.sheet_name = r.message.sheet_name;
                    me.render_preview(r.message);
                }
            }
        });
    }

    render_preview(data) {
        var me = this;
        var section = $(me.wrapper).find('#preview-section');
        section.show();

        $(me.wrapper).find('#preview-info').html(
            __('Sheet: <strong>{0}</strong> | Total rows: <strong>{1}</strong> (showing first 20)',
                [data.sheet_name, data.total_rows])
        );

        // Build header
        var thead = $(me.wrapper).find('#preview-thead');
        thead.html('<tr>' + data.columns.map(function(c) {
            return `<th>${c}</th>`;
        }).join('') + '</tr>');

        // Build rows
        var tbody = $(me.wrapper).find('#preview-tbody');
        tbody.empty();
        data.rows.forEach(function(row) {
            tbody.append(`<tr>
                <td>${frappe.utils.escape_html(row.item_name || '')}</td>
                <td>${flt(row.price, 2)}</td>
                <td>${frappe.utils.escape_html(row.article_no || '')}</td>
            </tr>`);
        });
    }

    start_import() {
        var me = this;
        frappe.confirm(
            __('Start importing {0} into <b>{1}</b>? This will run in the background.',
                [me.file_url, me.selected_price_list]),
            function() {
                frappe.call({
                    method: 'kayan_systemair.kayan_systemair.page.price_list_import.price_list_import.start_import',
                    args: {
                        file_url: me.file_url,
                        price_list: me.selected_price_list,
                        sheet_name: me.sheet_name
                    },
                    callback: function(r) {
                        if (r.message && r.message.log_name) {
                            frappe.show_alert({
                                message: __('Import job started. Log: {0}', [r.message.log_name]),
                                indicator: 'green'
                            });
                            me.poll_import_status(r.message.log_name);
                        }
                    }
                });
            }
        );
    }

    poll_import_status(log_name) {
        var me = this;
        var statusSection = $(me.wrapper).find('#import-status-section');
        statusSection.show();

        var pollInterval = setInterval(function() {
            frappe.call({
                method: 'kayan_systemair.kayan_systemair.page.price_list_import.price_list_import.get_import_status',
                args: { log_name: log_name },
                callback: function(r) {
                    if (!r.message) return;

                    var status = r.message.status;
                    var color = status === 'Completed' ? 'green' : status === 'Failed' ? 'red' : 'orange';

                    $(me.wrapper).find('#import-status-content').html(`
                        <div class="alert alert-${status === 'Completed' ? 'success' : status === 'Failed' ? 'danger' : 'warning'}">
                            <strong>${__('Status')}: ${status}</strong><br>
                            ${__('Created')}: ${r.message.records_created || 0} &nbsp;|&nbsp;
                            ${__('Updated')}: ${r.message.records_updated || 0} &nbsp;|&nbsp;
                            ${__('Skipped')}: ${r.message.records_skipped || 0}
                        </div>
                    `);

                    if (status === 'Completed' || status === 'Failed') {
                        clearInterval(pollInterval);
                        frappe.show_alert({
                            message: __('Import {0}. See log: {1}', [status, log_name]),
                            indicator: color
                        });
                        me.load_recent_logs();
                    }
                }
            });
        }, 3000);
    }

    load_recent_logs() {
        var me = this;
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'SystemAir Import Log',
                fields: ['name', 'price_list', 'status', 'records_created', 'records_updated', 'creation'],
                limit: 10,
                order_by: 'creation desc'
            },
            callback: function(r) {
                var container = $(me.wrapper).find('#import-logs-section');
                if (!r.message || !r.message.length) {
                    container.html(`<em class="text-muted">${__('No import logs yet.')}</em>`);
                    return;
                }

                var rows = r.message.map(function(log) {
                    var badge = log.status === 'Completed' ? 'success' :
                                log.status === 'Failed' ? 'danger' : 'warning';
                    return `<tr>
                        <td><a href="/app/systemair-import-log/${log.name}">${log.name}</a></td>
                        <td>${log.price_list}</td>
                        <td><span class="badge badge-${badge}">${log.status}</span></td>
                        <td>${log.records_created || 0}</td>
                        <td>${log.records_updated || 0}</td>
                        <td>${frappe.datetime.str_to_user(log.creation)}</td>
                    </tr>`;
                }).join('');

                container.html(`
                    <table class="table table-sm table-bordered">
                        <thead class="thead-light">
                            <tr>
                                <th>${__('Log')}</th>
                                <th>${__('Price List')}</th>
                                <th>${__('Status')}</th>
                                <th>${__('Created')}</th>
                                <th>${__('Updated')}</th>
                                <th>${__('Date')}</th>
                            </tr>
                        </thead>
                        <tbody>${rows}</tbody>
                    </table>
                `);
            }
        });
    }
};
