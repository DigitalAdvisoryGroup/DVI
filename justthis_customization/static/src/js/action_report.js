odoo.define('justthis_customization.ActionManager', function (require) {
    "use strict";
    
    /**
     * The purpose of this file is to add the support of Odoo actions of type
     * 'ir_actions_account_report_download' to the ActionManager.
     */
    
    var ActionManager = require('web.ActionManager');
    var crash_manager = require('web.crash_manager');
    var framework = require('web.framework');
    var accountReportsWidget = require('account_reports.account_report')

    var core = require('web.core');
    var ListController = require('web.ListController');
    var rpc = require('web.rpc');
    var session = require('web.session');
    var _t = core._t;

    var FormRenderer = require("web.FormRenderer");
    var dialogs = require('web.view_dialogs');
    var Dialog = require('web.Dialog');

    accountReportsWidget.include({
        events: _.extend({}, accountReportsWidget.prototype.events, {
            'change .external-balance-vdb': '_onChangeExternal',
        }),

        _onChangeExternal:function(event){
            var vdb_balance = $(event.target).closest('tr').find('.vdb-balance').find('span').text();
            var input = parseFloat($(event.target).val());
//            var balance = vdb_balance.replace("CHF","").replace(",","");
//            var balance = parseFloat(balance.replace(",",""))
            var balance = vdb_balance.replace("CHF","").replace(",","").replace("'","");
            var balance = parseFloat(balance.replace(",","").replace("'",""))
            var total = balance-input;
            var total = total.toFixed(2);
            $(event.target).closest('tr').find('.total-balance').find('input').val(total.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",")+" CHF");
        }
    })
    
    ActionManager.include({
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
    
        /**
         * Executes actions of type 'ir_actions_account_report_download'.
         *
         * @private
         * @param {Object} action the description of the action to execute
         * @returns {Deferred} resolved when the report has been downloaded ;
         *   rejected if an error occurred during the report generation
         */
        _executeAccountReportCustomAction: function (action) {
            framework.blockUI();
            var def = $.Deferred();
            var data =  this.tableToJson($('.o_account_reports_table'));
            var all_data = action.data;
            all_data['json_data'] = JSON.stringify(data);
            session.get_file({
                url: '/custom/account_reports',
                data: all_data,
                success: def.resolve.bind(def),
                error: function () {
                    crash_manager.rpc_error.apply(crash_manager, arguments);
                    def.reject();
                },
                complete: framework.unblockUI,
            });
            return def;
        },
        /**
         * Overrides to handle the 'ir_actions_account_report_download' actions.
         *ir_actions_account_report_download
         * @override
         * @private
         */
        _handleAction: function (action, options) {
            if (action.type === 'ir_actions_account_report_download' && action.data != undefined && action.data.model == "account.report.configure.report") {
                return this._executeAccountReportCustomAction(action, options);
            }
            return this._super.apply(this, arguments);
        },
        tableToJson:function(table) {
            // var data = []; // first row needs to be headers var headers = [];
            // for (var i=0; i<table.rows[0].cells.length; i++) {
            //  headers[i] = table.rows[0].cells[i].innerHTML.toLowerCase().replace(/ /gi,'');
            // }
            // // go through cells
            // for (var i=1; i<table.rows.length; i++) {
            // var tableRow = table.rows[i]; var rowData = {};
            // for (var j=0; j<tableRow.cells.length; j++) {
            // rowData[ headers[j] ] = tableRow.cells[j].innerHTML;
            // } data.push(rowData);
            // }
            // return data; 
            var headers = [];
            $('.o_account_reports_table thead tr th').each(function(e) {        
                if($(this).html().trim().length != 0){
                    headers.push($(this).html().trim());
                }
            })
            var data = []
            // var i = 1;
            var tbl2 = $('.o_account_reports_table tbody tr').each(function(e) {        
                var x = $(this).children();
                var itArr = {};
                var count = 0;
                x.each(function() {
                    var increase_count = false;
                    if($(this).find('span.o_account_report_column_value').length ==1){
                        itArr[headers[count]] = $(this).find('span.o_account_report_column_value').text().trim();
                        increase_count = true;
                    }
                    if($(this).find('input').length ==1){
                        itArr[headers[count]] = $(this).find('input').val() ;
                        increase_count = true;
                    }
                    if(increase_count){
                        count +=1;
                    }
                    
                });
                data.push(itArr);
            })
            return data
            }
    });

    FormRenderer.include({
        _renderTagButton: function (node) {
            var $button = this._super.apply(this, arguments);
            var self = this;
            var value = this.state.res_id;
            if(node.attrs.class == 'oe_inline set-invoice'){
                $button.click(function(){
                    new dialogs.SelectCreateDialog(self, {
                        res_model: 'account.invoice',
                        title: _t('Select a invoice'),
                        disable_multiple_selection: true,
                        domain: [['type', '=', 'out_invoice']],
                        on_selected: function (records) {
                            if(records && records.length ==1){
                                Dialog.confirm(self, (_t("Are you sure you want to set this invoice?")), {
                                    confirm_callback: function () {
                                        self._rpc({
                                            model: 'inbound_isr_msg',
                                            method: 'set_invoice',
                                            args: [[value],records[0].id],
                                        })
                                        .then(function (views) {
                                            self.__parentedParent.reload()
                                        });
                                    },
                                });
                            }
                        }
                    }).open();
                })
            }
            return $button;
        }
    })

    ListController.include({
       renderButtons: function($node) {
           this._super.apply(this, arguments);
               if (this.$buttons) {
                 this.$buttons.find('.oe_action_button_export').click(this.proxy('action_report_export')) ;
                 this.$buttons.find('.oe_action_button_closure').click(this.proxy('period_closure')) ;
               }
       },
       action_report_export: function (ev) {
            var userContext = this.getSession().user_context;
            var self =this
            var user = session.uid;
            return rpc.query({
                model: 'account.report.configure.report',
                method: 'export_sap',
                args: [[user],this.searchView.action.env.context.options],
                context: this.searchView.action.env.context
            }).then(function (result) {

            framework.blockUI();
            var def = $.Deferred();
            var all_data = result.data;
            all_data['json_data'] = JSON.stringify([{}]);
            session.get_file({
                url: '/custom/account_reports',
                data: all_data,
                success: def.resolve.bind(def),
                error: function () {
                    crash_manager.rpc_error.apply(crash_manager, arguments);
                    def.reject();
                },
                complete: framework.unblockUI,
            });
            return def;
        });
       },
       period_closure: function () {
            var self = this
            var user = session.uid;
            rpc.query({
                model: 'account.report.configure.report',
                method: 'period_closure',
                args: [[user],this.searchView.action.env.context.options],
                }).then(function (result) {
                    self.do_action(result);
                    window.location
                });
       },

    })
    
});

