# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.

import ast
import re
import io

from odoo import models, fields, _, api
from babel.dates import get_quarter_names, parse_date
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    # TODO saas-17: remove the try/except to directly import from misc
    import xlsxwriter


class ReportAccountFinancialReportLine(models.Model):
    _inherit = "account.financial.html.report.line"

    account_id = fields.Many2one("account.account", "Account")
    x_ext_ledger_account = fields.Boolean(related="account_id.x_ext_ledger_account", store=True)


class AccountReportConfigured(models.Model):
    _name = 'account.report.configure'
    _description = "Report Configure"

    name = fields.Char("Name", required=True)
    account_ids = fields.Many2many("account.account", string="Account Lines", required=True)
    financial_id = fields.Many2one("account.financial.html.report", "Financial Report ID", readonly=True)
    generated_menu_id = fields.Many2one(related="financial_id.generated_menu_id",
                                        string='Menu Item', comodel_name='ir.ui.menu', copy=False, store=True,
                                        help="The menu item generated for this report, or None if there isn't any."
                                        )
    parent_id = fields.Many2one('ir.ui.menu', related="generated_menu_id.parent_id", readonly=False)
    state = fields.Selection([('created','Created')], string="State", default="")

    @api.model
    def create(self, vals):
        parent_id = vals.pop('parent_id', False)
        vals['state'] = 'created'
        res = super(AccountReportConfigured, self).create(vals)
        res._create_action_and_menu(parent_id)
        res._create_financial_report()
        return res

    @api.multi
    def write(self, vals):
        parent_id = vals.pop('parent_id', False)
        res = super(AccountReportConfigured, self).write(vals)
        if parent_id:
            for report in self:
                report._create_action_and_menu(parent_id)
        return res

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.generated_menu_id:
                rec.generated_menu_id.action.sudo().unlink()
                rec.generated_menu_id.sudo().unlink()
            if rec.financial_id:
                rec.financial_id.sudo().unlink()
        return super(AccountReportConfigured, self).unlink()


    def _create_action_and_menu(self, parent_id):
        # create action and menu with corresponding external ids, in order to
        # remove those entries when deinstalling the corresponding module
        module = self._context.get('install_module', 'l10n_ch_qr_report_cr')
        IMD = self.env['ir.model.data']

        for report in self:
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
                    'parent_id': parent_id or IMD.xmlid_to_res_id('account.menu_finance_reports'),
                    'action': 'ir.actions.client,%s' % (action.id,),
                }
                menu_xmlid = "%s.%s" % (module, 'account_financial_html_report_menu_' + str(report.id))
                data = dict(xml_id=menu_xmlid, values=menu_vals, noupdate=True)
                menu = self.env['ir.ui.menu'].sudo()._load_records([data])
                report.generated_menu_id = menu.id

    def _create_financial_report(self):
        for report in self:
            financial_line_vals = []
            count = 1
            for account in report.account_ids:
                financial_line_vals.append((0, 0, {
                    'name': account.name,
                    'sequence': count,
                    'level': 3,
                    'figure_type': 'float',
                    'show_domain': 'never',
                    'formulas': "balance = sum.balance",
                    'domain': "[('account_id', '=', %s)]" % (account.id),
                    'groupby': "account_id",
                    'special_date_changer': "normal",
                    'account_id': account.id
                }))
            financial_vals = {
                'name': report.name,
                'generated_menu_id': report.generated_menu_id.id,
                'line_ids': financial_line_vals
            }
            financial_id = self.env['account.financial.html.report'].create(financial_vals)
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
    filter_external = True

    @api.model
    def _get_report_name(self):
        report_id = self.env['account.financial.html.report'].browse(self.env.context.get("id"))
        if report_id:
            return _('%s') % (report_id.name)
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
        return ctx

    @api.model
    def _get_lines(self, options, line_id=None):
        print("-------options------------",options)
        lines = []
        report_id = self.env['account.financial.html.report'].browse(self.env.context.get("id"))
        if report_id:
            date_from = options.get("date").get("date_from")
            date_to = options.get("date").get("date_to")
            # if options.get("external") and options['external']:
            #     final_line_ids = report_id.line_ids.filtered(lambda lead: lead.account_id.x_ext_ledger_account)
            # else:
            #     final_line_ids = report_id.line_ids.filtered(lambda acc: not acc.account_id.x_ext_ledger_account)
            for line in report_id.line_ids:
                line_domain = ast.literal_eval(line.domain)[0][2]
                account_id = self.env['account.account'].browse(line_domain)
                # if account_id.x_code_external: continue
                domain = [('date','>=',date_from),('date','<=',date_to),('line_ids.account_id','=',account_id.id)]
                # if not options['external']:
                #     domain.append(('line_ids.account_id.x_ext_ledger_account','=',False))
                move_ids = self.env['account.move'].search(domain)
                print("---------move_ids----------",move_ids)
                main_account_balance = 0.0
                for move in move_ids:
                    flag_check = any(move.line_ids.filtered(lambda acc: not acc.account_id.x_ext_ledger_account))
                    print("--------flag_check--------------",flag_check)
                    if flag_check and not options['external']: continue
                    for aml in move.line_ids:
                        if aml.account_id.id == account_id.id:
                            main_account_balance += abs(aml.balance)
                        if not options['external'] and aml.account_id.x_ext_ledger_account:
                            main_account_balance -= aml.balance
                print("--------main_account_balance---------",main_account_balance)
                line_amount = line._compute_line({}, report_id)
                print("---------line_amount------------",line_amount)
                columns = [account_id.code, account_id.x_code_external, account_id.name,
                           self.format_value(main_account_balance), '']
                lines.append({
                    'id': str(line.id),
                    'name': '',
                    'columns': [{'name': v} for v in columns],
                })
        return lines

    # def _get_reports_buttons(self):
    #     res = super(ReportConfigure, self)._get_reports_buttons()
    #     res.append({'name': _('Export (SAP)'), 'action': 'print_pdf'})
    #     return res

    def _get_templates(self):
        templates = super(ReportConfigure, self)._get_templates()
        templates['main_template'] = 'l10n_ch_qr_report_cr.main_template_account_configure_report'
        templates['line_template'] = 'l10n_ch_qr_report_cr.line_template_account_configure_report'
        templates['search_template'] = 'l10n_ch_qr_report_cr.search_template_account_configure_report'
        return templates

    def _get_columns_name(self, options):
        columns = [{}]
        columns.append({'name': _('Account Code'), 'class': 'text'})
        columns.append({'name': _('Account External Code'), 'class': 'text'})
        columns.append({'name': _('Account Name'), 'class': 'text'})
        columns.append({'name': _('Balance'), 'class': 'number'})
        columns.append({'name': _('External Balance'), 'class': 'number'})
        return columns

    def get_custome_xlsx(self, options, response, json_data):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet(self._get_report_name()[:31])

        default_col1_style = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})
        title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
        currency_format = workbook.add_format({'num_format': '##0.00'})
        super_columns = self._get_super_columns(options)
        y_offset = bool(super_columns.get('columns')) and 1 or 0

        sheet.write(y_offset, 0, '', title_style)
        headers = list(json_data[0].keys())
        x = 0
        for h in headers:
            header_label = h
            sheet.write(y_offset, x, header_label, title_style)
            sheet.set_column(x, x, 20)
            x += 1

        y = 1
        for data in json_data:
            count = 0
            for d in data.values():
                if ((data.get("External Balance") and d and data['External Balance']) or (data.get("Saldo Kontoführung") and d and data['Saldo Kontoführung'])) == d:
                    d = re.sub("[^\d\.]", "", d)
                    d = float(d)
                    sheet.write(y, count, d, currency_format)
                elif ((data.get("Balance") and d and data['Balance']) or (data.get("Saldo") and d and data['Saldo'])) == d:
                    d = re.sub("[^\d\.]", "", d)
                    d = float(d)
                    sheet.write(y, count, d, currency_format)
                else:
                    sheet.write(y, count, d, default_col1_style)
                count += 1
            y += 1
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
