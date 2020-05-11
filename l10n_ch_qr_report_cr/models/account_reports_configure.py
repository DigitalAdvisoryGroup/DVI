# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _, api
import ast

class AccountAccount(models.Model):
    _inherit = 'account.account'

    external_amount = fields.Float("External Amount")


class AccountReportConfigured(models.Model):
    _name = 'account.report.configure'
    _description = "Report Configure"

    name = fields.Char("Name", required=True)
    account_ids = fields.Many2many("account.account",string="Account Lines", required=True)
    financial_id = fields.Many2one("account.financial.html.report", "Financial Report ID", readonly=True)
    generated_menu_id = fields.Many2one(related="financial_id.generated_menu_id",
        string='Menu Item', comodel_name='ir.ui.menu', copy=False, store=True,
        help="The menu item generated for this report, or None if there isn't any."
    )

    @api.model
    def create(self, vals):
        res = super(AccountReportConfigured, self).create(vals)
        res._create_action_and_menu()
        res._create_financial_report()
        return res

    def _create_action_and_menu(self):
        # create action and menu with corresponding external ids, in order to
        # remove those entries when deinstalling the corresponding module
        module = self._context.get('install_module', 'l10n_ch_qr_report_cr')
        IMD = self.env['ir.model.data']

        for report in self:
            print("----report.generated_menu_id----1----------",report.generated_menu_id)
            if not report.generated_menu_id:
                action_vals = {
                    'name': report.name,
                    'tag': 'account_report',
                    'context': {
                        'model': 'account.report.configure.report',
                        'id': report.id,
                    },
                }
                action_xmlid = "%s.%s" % (module, 'account_financial_html_report_action_' + str(report.id))
                data = dict(xml_id=action_xmlid, values=action_vals, noupdate=True)
                action = self.env['ir.actions.client'].sudo()._load_records([data])

                menu_vals = {
                    'name': report.name,
                    'parent_id': IMD.xmlid_to_res_id('account.menu_finance_reports'),
                    'action': 'ir.actions.client,%s' % (action.id,),
                }
                print("---------menu_vals--------------",menu_vals)
                menu_xmlid = "%s.%s" % (module, 'account_financial_html_report_menu_' + str(report.id))
                data = dict(xml_id=menu_xmlid, values=menu_vals, noupdate=True)
                menu = self.env['ir.ui.menu'].sudo()._load_records([data])
                print("--------menu------------",menu)
                report.generated_menu_id = menu.id

    def _create_financial_report(self):
        for report in self:
            print("-------report------------",report)
            print("-------report------------",report.generated_menu_id)
            financial_line_vals = []
            count = 1
            for account in report.account_ids:
                financial_line_vals.append((0,0,{
                    'name': account.name,
                    'sequence': count,
                    'level': 3,
                    'figure_type': 'float',
                    'show_domain': 'never',
                    'formulas': "balance = sum.balance",
                    'domain': "[('account_id', '=', %s)]"%(account.id),
                    'groupby': "account_id",
                    'special_date_changer': "normal",
                }))
            financial_vals = {
                'name': report.name,
                'generated_menu_id': report.generated_menu_id.id,
                'line_ids': financial_line_vals
            }
            financial_id = self.env['account.financial.html.report'].create(financial_vals)
            print("--------financial_id-------------",financial_id)
            report.financial_id = financial_id.id
            act_ctx = ast.literal_eval(report.generated_menu_id.action.context)
            act_ctx['id'] = financial_id.id
            report.sudo().generated_menu_id.action.context = act_ctx





class ReportConfigure(models.AbstractModel):
    _inherit = "account.report"
    _name = "account.report.configure.report"
    _description = "Account Configure Report"

    filter_date = {'date_from': '', 'date_to': '', 'filter': 'this_year'}
    filter_all_entries = True

    @api.model
    def _get_report_name(self):
        report_id = self.env['account.financial.html.report'].browse(self.env.context.get("id"))
        if report_id:
            return _('%s')%(report_id.name)
        return _('Account Configure Report')

    @api.multi
    def get_html(self, options, line_id=None, additional_context=None):
        """
        Override
        Compute and return the content in HTML of the followup for the partner_id in options
        """
        if additional_context is None:
            additional_context = {}
        additional_context['company_accounting_area'] = self.env.user.company_id.x_acc_area.x_code
        return super(ReportConfigure, self).get_html(options, line_id=line_id,
                                                           additional_context=additional_context)

    def _set_context(self, options):
        ctx = super(ReportConfigure, self)._set_context(options)
        ctx.update({'id': self.id})
        print("--------ctx-----------custom---",ctx)
        return ctx

    @api.model
    def _get_lines(self, options, line_id=None):
        lines = []
        print("-----------self.env.context-----------",self.env.context)
        report_id = self.env['account.financial.html.report'].browse(self.env.context.get("id"))
        if report_id:
            for line in report_id.line_ids:
                line_domain = ast.literal_eval(line.domain)[0][2]
                account_id = self.env['account.account'].browse(line_domain)
                line_amount = line._compute_line({},report_id)
                columns = [account_id.code,account_id.x_code_external,account_id.name,self.format_value(line_amount.get('balance')),'']
                lines.append({
                    'id': str(line.id),
                    'name': '',
                    'columns': [{'name': v} for v in columns],
                })
        print("--------lines---custom--------",lines)
        return lines

    def _get_reports_buttons(self):
        res = super(ReportConfigure, self)._get_reports_buttons()
        res.append({'name': _('Export (SAP)'), 'action': 'print_pdf'})
        return res

    def _get_templates(self):
        templates = super(ReportConfigure, self)._get_templates()
        templates['main_template'] = 'l10n_ch_qr_report_cr.main_template_account_configure_report'
        templates['line_template'] = 'l10n_ch_qr_report_cr.line_template_account_configure_report'
        return templates

    def _get_columns_name(self, options):
        columns = [{}]
        columns.append({'name': _('Account Code'), 'class': 'text'})
        columns.append({'name': _('Account External Code'), 'class': 'text'})
        columns.append({'name': _('Account Name'), 'class': 'text'})
        columns.append({'name': _('Balance'), 'class': 'number'})
        columns.append({'name': _('External Balance'), 'class': 'number'})
        return columns



