# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.

import ast
import datetime
import io
import json
import os
import re

from odoo import models, fields, _, api

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    # TODO saas-17: remove the try/except to directly import from misc
    import xlsxwriter


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    x_code_external = fields.Char(related="account_id.x_code_external", store=True)


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
                           self.format_value(main_account_balance), '']
                lines.append({
                    'id': str(line.id),
                    'name': '',
                    'columns': [{'name': v} for v in columns],
                })
        return lines

    def _get_reports_buttons(self):
        res = super(ReportConfigure, self)._get_reports_buttons()
        res.append({'name': _('Export (SAP)'), 'action': 'export_sap'})
        return res

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
                else:
                    sheet.write(y, count, d, default_col1_style)
                count += 1
            y += 1
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

    def get_sap_txt(self, options, json_data):
        print("-------self-----------", self)
        print("-------self-----------", self.env.context)
        print("-------options-----------", options)
        print("-------json_data-----------", json_data)
        with open('/tmp/sap.txt', 'a') as f:
            company = self.env.user.company_id
            header = 'A'
            header += company.x_acc_area.x_code.ljust(4, ' ')
            header += '01'
            header += company.x_ledger_name.ljust(60, ' ')
            header += '/'.ljust(1, " ")
            f.write(header + '\n')
            self.with_context(id=self.id).get_sap_export_lines(options, f)
        content = open('/tmp/sap.txt').read()
        os.remove("/tmp/sap.txt")
        return content

    def get_sap_export_lines(self, options, f):
        report_id = self.env['account.financial.html.report'].browse(self.env.context.get("id"))
        if report_id:
            date_from = options.get("date").get("date_from")
            date_to = options.get("date").get("date_to")
            final_move_dict = {}
            for line in report_id.line_ids:
                line_domain = ast.literal_eval(line.domain)[0][2]
                account_id = self.env['account.account'].browse(line_domain)
                domain = [('date', '>=', date_from), ('date', '<=', date_to),
                          ('line_ids.account_id', '=', account_id.id)]
                move_ids = self.env['account.move'].search(domain)
                for move in move_ids:
                    aml_ids = self.env['account.move.line'].search(
                        [('move_id', '=', move.id), ('account_id.x_ext_ledger_account', '=', True)])
                    if aml_ids and not options['external']: continue

                    move_acc_ids = move.mapped("line_ids").mapped('account_id').ids
                    move_acc_ids.sort()
                    print("------------move_acc_ids---------", move_acc_ids)
                    if move_acc_ids in final_move_dict.values():
                        for k, v in final_move_dict.items():
                            print("---------k,v------------", k, v)
                            if move_acc_ids == v:
                                final_move_dict[k + '-' + str(move.id)] = final_move_dict[k]
                                del final_move_dict[k]
                                break
                    else:
                        final_move_dict.update({str(move.id): move_acc_ids})

            print("----------final_move_dict----------", final_move_dict)
            singal_final_moves = []
            merge_final_moves = []
            for k in final_move_dict.keys():
                k = k.split("-")
                if len(k) > 1:
                    for key in k:
                        merge_final_moves.append(int(key))
                else:
                    singal_final_moves.append(int(k[0]))
            if merge_final_moves or singal_final_moves:
                final_sap_move, footer_data = self.parse_sap_move_lines(singal_final_moves, merge_final_moves)
                company = self.env.user.company_id
                if final_sap_move:
                    for sap_line in final_sap_move:
                        print("-----------sap_line----------", sap_line)
                        if sap_line.get("position_header"):
                            position_header = '1SV'
                            position_header += company.x_acc_area.x_code.ljust(4, ' ')
                            position_header += company.x_acc_area.x_code.ljust(16, ' ')
                            position_header += sap_line['position_header']['move_date'].ljust(8, ' ')
                            position_header += ''.ljust(10, ' ')
                            position_header += ''.ljust(12, ' ')
                            position_header += ''.ljust(10, ' ')
                            position_header += str(sap_line['position_header']['total']).ljust(16, ' ')
                            position_header += ''.ljust(50, ' ')
                            position_header += ''.ljust(1, ' ')
                            position_header += sap_line['position_header']['move_date'].ljust(8, ' ')
                            position_header += ''.ljust(3, ' ')
                            position_header += ''.ljust(24, ' ')
                            print("------position_header------", position_header)
                            f.write(position_header + '\n')
                        if sap_line.get("position_line"):
                            for line in sap_line['position_line']:
                                position = '9'
                                position += ''.ljust(2, ' ')
                                position += ''.ljust(4, ' ')
                                position += ''.ljust(16, ' ')
                                position += ''.ljust(8, ' ')
                                position += ''.ljust(10, ' ')
                                position += ''.ljust(12, ' ')
                                position += line['account_code'].ljust(10, ' ')
                                position += str(line['amount']).ljust(16, ' ')
                                position += (company.x_sap_export_posting_text + ' ' + "03.2020").ljust(50, ' ')
                                position += line['type'].ljust(1, ' ')
                                position += ''.ljust(8, ' ')
                                position += ''.ljust(3, ' ')
                                position += ''.ljust(24, ' ')
                                f.write(position + '\n')
                if footer_data:
                    from time import gmtime, strftime
                    current_time = strftime("%H:%M:%S", gmtime())
                    position_footer = 'Z'
                    position_footer += (datetime.date.today().strftime("%d-%m-%Y").replace("-", "")).ljust(8, ' ')
                    position_footer += (current_time.replace(":", "")).ljust(6, " ")
                    position_footer += company.x_sap_export_name.ljust(50, ' ')
                    position_footer += (
                                company.x_sap_export_path + company.x_sap_export_file + datetime.date.today().strftime(
                            "%Y-%m-%d").replace("-", "")).ljust(50, ' ')
                    position_footer += ''.ljust(10, ' ')
                    position_footer += ''.ljust(10, ' ')
                    position_footer += ''.ljust(8, ' ')
                    position_footer += ''.ljust(8, ' ')
                    position_footer += footer_data['no_je'].ljust(8, ' ')
                    position_footer += ''.ljust(8, ' ')
                    position_footer += ''.ljust(8, ' ')
                    position_footer += footer_data['total_records'].ljust(8, ' ')
                    position_footer += footer_data['total_debit'].ljust(16, ' ')
                    position_footer += footer_data['total_credit'].ljust(16, ' ')
                    f.write(position_footer)

    def parse_sap_move_lines(self, singal_final_moves, merge_final_moves):
        final_move_list = []
        footer_data = {'no_je': '2', 'total_records': '8', 'total_debit': '2400.00', 'total_credit': '2400.00'}
        if singal_final_moves:
            singal_move_ids = self.env['account.move'].browse(singal_final_moves)
            for move in singal_move_ids:
                move_dict = {
                    'position_header': {'move_date': move.date.strftime("%Y-%m-%d").replace("-", ""), 'total': "500.00"},
                    'position_line': []}
                for line in move.line_ids:
                    if line.debit != 0.0:
                        move_dict['position_line'].append(
                            {'account_code': line.x_code_external, 'amount': '{:.2f}'.format(line.debit), 'type': 'S'})

                    else:
                        move_dict['position_line'].append(
                            {'account_code': line.x_code_external, 'amount': '{:.2f}'.format(line.credit), 'type': 'H'})
                final_move_list.append(move_dict)
        if merge_final_moves:

            merge_move_ids = self.env['account.move'].browse(merge_final_moves)
            print("------merge_move_ids------------", merge_move_ids)
            move_dict = {
                'position_header': {'move_date': merge_move_ids[0].date.strftime("%Y-%m-%d").replace("-", ""),
                                    'total': '1900.00'},
                'position_line': []}
            account_moves_lines = self.env['account.move.line'].search_read([
                ('move_id', 'in', merge_move_ids.ids)], ['x_code_external', 'account_id', 'debit', 'credit', 'balance'])
            print("-------account_moves_lines------------", account_moves_lines)
            if account_moves_lines:
                temp_merge = {}
                for merge_line in account_moves_lines:
                    print("--------merge_line------------", merge_line)
                    if merge_line['account_id'][0] in temp_merge:
                        temp_merge[merge_line['account_id'][0]]['amount'] += merge_line['balance']
                    else:
                        temp_merge[merge_line['account_id'][0]] = {'account_code': merge_line['x_code_external'],
                                                                   'amount': merge_line['balance']}
                print("---------temp_merge----------",temp_merge)
                for m_l in temp_merge.values():
                    print("------m_l-----------------",m_l)
                    if m_l['amount'] < 0.0:
                        move_dict['position_line'].append(
                            {'account_code': m_l['account_code'], 'amount': '{:.2f}'.format(abs(m_l['amount'])), 'type': 'H'})
                    else:
                        move_dict['position_line'].append(
                            {'account_code': m_l['account_code'], 'amount': '{:.2f}'.format(m_l['amount']),
                             'type': 'S'})
                final_move_list.append(move_dict)
        print("-----------final_move_list---------",final_move_list)
        return final_move_list, footer_data
