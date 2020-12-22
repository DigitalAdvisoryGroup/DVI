# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.

import ast
import datetime
import io
import json
import os
import re
import tempfile
from time import gmtime, strftime

from odoo import models, fields, _, api
from odoo.exceptions import UserError

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    # TODO saas-17: remove the try/except to directly import from misc
    import xlsxwriter


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    x_code_external = fields.Char(related="account_id.x_code_external", store=True)
    is_reversal_line = fields.Boolean("Is Reversal Line")
    is_depreciate_line = fields.Boolean("Is Depreciate Line")

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
    state = fields.Selection([('created', 'Created')], string="State", default="")

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
        module = self._context.get('install_module', 'justthis_customization')
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

    def export_sap(self, options):
        return {
            'type': 'ir_actions_account_report_download',
            'data': {'model': self.env.context.get('model'),
                     'options': json.dumps(options),
                     'output_format': 'sap',
                     'financial_id': self.env.context.get('id'),
                     }
        }

    def _set_context(self, options):
        ctx = super(ReportConfigure, self)._set_context(options)
        ctx.update({'id': self.id})
        return ctx

    @api.model
    def _get_lines(self, options, line_id=None):
        lines = []
        report_id = self.env['account.financial.html.report'].browse(self.env.context.get("id"))
        if report_id:
            date_from = options.get("date").get("date_from")
            date_to = options.get("date").get("date_to")
            for line in report_id.line_ids:
                line_domain = ast.literal_eval(line.domain)[0][2]
                account_id = self.env['account.account'].browse(line_domain)
                domain = [('date', '>=', date_from), ('date', '<=', date_to),
                          ('line_ids.account_id', '=', account_id.id)]
                move_ids = self.env['account.move'].search(domain)
                main_account_balance = 0.0
                for move in move_ids:
                    aml_ids = self.env['account.move.line'].search(
                        [('move_id', '=', move.id), ('account_id.x_ext_ledger_account', '=', True)])
                    if aml_ids and not options['external']: continue
                    for aml in move.line_ids:
                        if aml.account_id.id == account_id.id:
                            main_account_balance += aml.balance
                columns = [account_id.code, account_id.x_code_external, account_id.name,
                           self.format_value(main_account_balance), '','','']
                lines.append({
                    'id': str(line.id),
                    'name': '',
                    'columns': [{'name': v} for v in columns],
                })
        return lines

    def _get_reports_buttons(self):
        res = super(ReportConfigure, self)._get_reports_buttons()
        res.append({'name': _('Export (SAP)'), 'action': 'export_sap'})
        res.append({'name': _('View Items (SAP)'), 'action': 'export_view_items'})
        return res

    def export_view_items(self, options):
        report_id = self.env['account.financial.html.report'].browse(self.env.context.get("id"))
        aml_views_ids = self.env['account.move.line']
        if report_id:
            date_from = options.get("date").get("date_from")
            date_to = options.get("date").get("date_to")
            for line in report_id.line_ids:
                line_domain = ast.literal_eval(line.domain)[0][2]
                account_id = self.env['account.account'].browse(line_domain)
                analytic_account_ids = self.env['account.analytic.account'].search([])
                analytic_dict = {}
                for analytic in analytic_account_ids.ids+[False]:
                    analytic_dict[analytic] = []
                    aml_ids = self.env['account.move.line'].search(
                        [
                            ('move_id.date', '>=', date_from),
                            ('move_id.date', '<=', date_to),
                            ('move_id.state', '=', 'posted'),
                            ('analytic_account_id', '=', analytic),
                            ('account_id', '=', account_id.id),
                            ('account_id.x_ext_ledger_account', '=', False),
                            '|', ('debit', '!=', 0.0), ('credit', '!=', 0.0)
                        ]

                    )
                    aml_views_ids |= aml_ids
        action = self.env.ref('justthis_customization.action_account_moves_custom').read()[0]
        action['domain'] = str([('id', 'in', aml_views_ids.ids)])
        return action

    def _get_templates(self):
        templates = super(ReportConfigure, self)._get_templates()
        templates['main_template'] = 'justthis_customization.main_template_account_configure_report'
        templates['line_template'] = 'justthis_customization.line_template_account_configure_report'
        templates['search_template'] = 'justthis_customization.search_template_account_configure_report'
        return templates

    def _get_columns_name(self, options):
        columns = [{}]
        columns.append({'name': _('Account Code'), 'class': 'text'})
        columns.append({'name': _('Account External Code'), 'class': 'text'})
        columns.append({'name': _('Account Name'), 'class': 'text'})
        columns.append({'name': _('Balance'), 'class': 'number vdb-balance'})
        columns.append({'name': _('External Balance'), 'class': 'number external-balance-vdb'})
        columns.append({'name': _('Total Balance'), 'class': 'total-balance'})
        columns.append({'name': _('External Note'), 'class': 'text'})
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
                if d and ((data.get("External Balance") and data['External Balance'] or False) or (
                        data.get("Saldo extern") and data['Saldo extern'] or False)) == d:
                    d = re.sub("[^\d\.]", "", d)
                    d = float(d)
                    sheet.write(y, count, d, currency_format)
                elif d and ((data.get("Balance") and data['Balance'] or False) or (
                        data.get("Saldo") and data['Saldo'] or False)) == d:
                    sign = 1
                    if '-' in d:
                        sign = -1
                    d = re.sub("[^\d\.]", "", d)
                    d = float(d)
                    sheet.write(y, count, d * sign, currency_format)
                elif d and ((data.get("Total Balance") and data['Total Balance'] or False) or (
                        data.get("Saldo") and data['Saldo'] or False)) == d:
                    sign = 1
                    if '-' in d:
                        sign = -1
                    d = re.sub("[^\d\.]", "", d)
                    d = float(d)
                    sheet.write(y, count, d * sign, currency_format)
                else:
                    sheet.write(y, count, d, default_col1_style)
                count += 1
            y += 1
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

    def get_sap_txt(self, options, json_data):
        if options['external']:
            raise UserError(_('Please select external ledger filter as Excluded.'))
        content = ''
        try:
            file_path = tempfile.gettempdir()+'/sap.txt'
            with open(file_path, 'a') as f:
                company = self.env.user.company_id
                header = 'A'
                header += company.x_acc_area.x_code.ljust(4, ' ')
                header += '01'
                header += company.x_ledger_name.ljust(60, ' ')
                header += '/'.ljust(1, " ")
                f.write(header + '\n')
                self.with_context(id=self.id).get_sap_export_lines(options, f)
            content = open(file_path).read()
            os.remove(file_path)
        except:
            os.remove(file_path)
        return content

    def get_sap_export_lines(self, options, f):
        report_id = self.env['account.financial.html.report'].browse(self.env.context.get("id"))
        if report_id:
            date_from = options.get("date").get("date_from")
            date_to = options.get("date").get("date_to")
            final_data = []
            account_ids = self.env['account.account']
            for line in report_id.line_ids:
                line_domain = ast.literal_eval(line.domain)[0][2]
                account_id = self.env['account.account'].browse(line_domain)
                account_ids |= account_id
                analytic_account_ids = self.env['account.analytic.account'].search([])
                analytic_dict = {}
                for analytic in analytic_account_ids.ids + [False]:
                    analytic_dict[analytic] = []
                    aml_ids = self.env['account.move.line'].search(
                        [
                         ('move_id.date', '>=', date_from),
                         ('move_id.date', '<=', date_to),
                         ('move_id.state', '=', 'posted'),
                         ('analytic_account_id', '=',analytic),
                         ('account_id', '=', account_id.id),
                         ('account_id.x_ext_ledger_account', '=', False),
                         '|',('debit','!=',0.0),('credit','!=',0.0)
                        ]

                    )
                    amount_dict = {}
                    for aml in aml_ids:
                        if aml.debit > 0.0:
                            if not analytic:
                                counter_aml_ids = aml.move_id.line_ids.filtered(
                                    lambda cml: cml.id != aml.id and cml.credit > 0.0 and not cml.analytic_account_id and not cml.account_id.x_ext_ledger_account)
                            else:
                                counter_aml_ids = aml.move_id.line_ids.filtered(
                                    lambda cml: cml.id != aml.id and cml.credit > 0.0)
                            aml_dict = {
                                aml.account_id.x_code_external:{'id':str(aml.id),'debit':aml.debit,'credit':0, 'account_id':aml.account_id,'account_code':aml.x_code_external or aml.account_id.x_code_external,'analytic_account_id': aml.analytic_account_id},
                                counter_aml_ids.account_id.x_code_external:{'id':str(aml.id),'debit':0,'credit':aml.debit,'account_id':counter_aml_ids.account_id,'account_code':counter_aml_ids.x_code_external or counter_aml_ids.account_id.x_code_external,'analytic_account_id': counter_aml_ids.analytic_account_id}
                            }
                        else:
                            if not analytic:
                                counter_aml_ids = aml.move_id.line_ids.filtered(
                                    lambda cml: cml.id != aml.id and cml.debit > 0.0 and not cml.analytic_account_id and not cml.account_id.x_ext_ledger_account)
                            else:
                                counter_aml_ids = aml.move_id.line_ids.filtered(
                                    lambda cml: cml.id != aml.id and cml.debit > 0.0)
                            aml_dict = {
                                aml.account_id.x_code_external: {'id':str(aml.id),'debit': 0, 'credit': aml.credit,'account_id':aml.account_id,'account_code':aml.x_code_external or aml.account_id.x_code_external,'analytic_account_id': aml.analytic_account_id},
                                counter_aml_ids.account_id.x_code_external: {'id':str(aml.id),'debit': aml.credit, 'credit': 0,'account_id':counter_aml_ids.account_id,'account_code':counter_aml_ids.x_code_external or counter_aml_ids.account_id.x_code_external,'analytic_account_id': counter_aml_ids.analytic_account_id}
                            }
                        if not counter_aml_ids: continue
                        if len(counter_aml_ids) == 1:
                            account_key_pair = '-'.join([aml.account_id.x_code_external,counter_aml_ids.account_id.x_code_external])
                            rev_account_key_pair = '-'.join([counter_aml_ids.account_id.x_code_external,aml.account_id.x_code_external])
                            if rev_account_key_pair in amount_dict:
                                pass
                            elif account_key_pair in amount_dict:
                                amount_dict[account_key_pair][aml.account_id.x_code_external]['debit'] +=aml_dict[aml.account_id.x_code_external]['debit']
                                amount_dict[account_key_pair][aml.account_id.x_code_external]['credit'] +=aml_dict[aml.account_id.x_code_external]['credit']
                                amount_dict[account_key_pair][aml.account_id.x_code_external]['id'] +='-'+aml_dict[aml.account_id.x_code_external]['id']
                                amount_dict[account_key_pair][counter_aml_ids.account_id.x_code_external]['debit'] +=aml_dict[counter_aml_ids.account_id.x_code_external]['debit']
                                amount_dict[account_key_pair][counter_aml_ids.account_id.x_code_external]['credit'] +=aml_dict[counter_aml_ids.account_id.x_code_external]['credit']
                                amount_dict[account_key_pair][counter_aml_ids.account_id.x_code_external]['id'] +='-'+aml_dict[counter_aml_ids.account_id.x_code_external]['id']
                            else:
                                amount_dict[account_key_pair] = aml_dict
                    if aml_ids :
                        analytic_dict[analytic].append(amount_dict)
                final_data.append(analytic_dict)
            res = self.parse_sap_move_lines(self.format_final_dict(final_data), self.env.user.company_id, date_to,f)

    def format_final_dict(self,final_dict):
        import pprint
        final_dict_format = []
        rev_final_format = []
        for f_key in final_dict:
            for fd_key,fd_value in f_key.items():
                for fd_value_inner in fd_value:
                    for fd_key_inner,f_value in fd_value_inner.items():
                        if not fd_key:
                            rev_final_format.append(fd_key_inner)
                            rev_fd_key_inner = fd_key_inner.split("-")
                            rev_fd_key_inner = rev_fd_key_inner[1]+"-"+rev_fd_key_inner[0]
                        if not fd_key and rev_fd_key_inner in rev_final_format:continue
                        final_dict_format.append(list(f_value.values()))
        return final_dict_format
    #
    def parse_sap_move_lines(self, final_data, company, date_to,f):
        total_debit_credit_amt = 0.0
        total_je = 0.0
        total_records = 1
        for final_d in final_data:
            datetime_seq = ((datetime.datetime.today().strftime("%Y-%m-%d %H:%M").replace("-", "")).replace(':', '')).replace(" ", '') + str(1).rjust(2, '0')
            total_amount = final_d[0]['credit'] or final_d[0]['debit']
            if final_d[0]['debit'] and final_d[0]['credit']:
                total_amount = abs(final_d[0]['debit'] - final_d[0]['credit'])
            total_je += 1
            total_records += 1
            total_debit_credit_amt += abs(total_amount)
            position_header = '1SV'
            position_header += company.x_acc_area.x_code.ljust(4, ' ')
            position_header += datetime_seq.ljust(16, ' ')
            position_header += date_to.replace("-", "").ljust(8, ' ')
            position_header += ''.ljust(10, ' ')
            position_header += ''.ljust(12, ' ')
            position_header += ''.ljust(10, ' ')
            position_header += str(total_amount).ljust(16, ' ')
            position_header += ''.ljust(50, ' ')
            position_header += ''.ljust(1, ' ')
            position_header += date_to.replace("-", "").ljust(8, ' ')
            position_header += ''.ljust(3, ' ')
            position_header += ''.ljust(24, ' ')
            f.write(position_header + '\n')
            for line in final_d:
                month_year_string = date_to.split("-")
                month_year_string = month_year_string[1]+"."+month_year_string[0]
                aml_ids = str(line['id']).split('-')
                for aml in aml_ids:
                    aml_ids = self.env['account.move.line'].browse(int(aml))
                    aml_ids.x_sap_export_seq = datetime_seq
                profit_center_code = line['analytic_account_id'] and line['analytic_account_id'].code or ''
                amount = line['debit'] or line['credit']
                if line['debit'] and line['credit']:
                    amount = abs(line['debit'] - line['credit'])
                dc_type = (line['debit'] - line['credit']) > 0.0 and 'S' or 'H'
                total_records += 1
                position = '9'
                position += ''.ljust(2, ' ')
                position += ''.ljust(4, ' ')
                position += ''.ljust(16, ' ')
                position += ''.ljust(8, ' ')
                position += ''.ljust(10, ' ')
                position += profit_center_code.ljust(12, ' ')
                position += line['account_code'].ljust(10, ' ')
                position += str(amount).ljust(16, ' ')
                position += (company.x_sap_export_posting_text + ' ' + month_year_string).ljust(50, ' ')
                position += dc_type.ljust(1, ' ')
                position += ''.ljust(8, ' ')
                position += ''.ljust(3, ' ')
                position += ''.ljust(24, ' ')
                f.write(position + '\n')

        current_time = strftime("%H:%M:%S", gmtime())
        position_footer = 'Z'
        position_footer += (datetime.date.today().strftime("%d-%m-%Y").replace("-", "")).ljust(8, ' ')
        position_footer += (current_time.replace(":", "")).ljust(6, " ")
        position_footer += company.x_sap_export_name.ljust(50, ' ')
        position_footer += (company.x_sap_export_path + company.x_sap_export_file + datetime.date.today().strftime("%Y-%m-%d").replace("-", ""))[:50].ljust(50, ' ')
        position_footer += ''.ljust(10, ' ')
        position_footer += ''.ljust(10, ' ')
        position_footer += ''.ljust(8, ' ')
        position_footer += ''.ljust(8, ' ')
        position_footer += str(int(total_je)).ljust(8, ' ')
        position_footer += ''.ljust(8, ' ')
        position_footer += ''.ljust(8, ' ')
        position_footer += str(int(total_records+1)).ljust(8, ' ')
        position_footer += str(total_debit_credit_amt).ljust(16, ' ')
        position_footer += str(total_debit_credit_amt).ljust(16, ' ')
        f.write(position_footer)