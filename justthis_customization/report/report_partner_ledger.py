# -*- coding: utf-8 -*-

import time
from odoo import api, models, _
from odoo.exceptions import UserError


class ReportPartnerLedgerPdf(models.AbstractModel):
    _name = 'report.justthis_customization.report_partnerledger_pdf'

    def main_headers_total(self, data,partner):
        final_data = []
        res_invoice = self.get_invoices_data(data, partner)
        # print("-----res_invoice--res---------", res_invoice)
        res_deposit = self.get_deposits_data(data, partner)
        # print("----res_deposit---res---------", res_deposit)
        res_assets = self.get_assets_data(data, partner)
        # print("-------res---res_assets------", res_assets)
        for i in ["Balance", "Invoices","Deposits","Assets"]:
            if i == "Balance":
                final_data.append({
                    "name": (_("Balance")),
                    "debit": sum([x['debit'] for x in res_invoice]) + sum([x['debit'] for x in res_deposit]) + sum([x['debit'] for x in res_assets]),
                    "credit": sum([x['credit'] for x in res_invoice]) + sum([x['credit'] for x in res_deposit]) + sum([x['credit'] for x in res_assets]),
                    "balance": sum([x['balance'] for x in res_invoice]) + sum([x['balance'] for x in res_deposit]) + sum([x['balance'] for x in res_assets]),

                })
            elif i == "Invoices":
                final_data.append({
                    "name": (_("Invoices")),
                    "debit": sum([x['debit'] for x in res_invoice]),
                    "credit": sum([x['credit'] for x in res_invoice]),
                    "balance": sum([x['balance'] for x in res_invoice]),

                })
            elif i == "Deposits":
                final_data.append({
                    "name": (_("Deposits")),
                    "debit": sum([x['debit'] for x in res_deposit]),
                    "credit": sum([x['credit'] for x in res_deposit]),
                    "balance": sum([x['balance'] for x in res_deposit]),

                })
            elif i == "Assets":
                final_data.append({
                    "name": (_("Assets")),
                    "debit": sum([x['debit'] for x in res_assets]),
                    "credit": sum([x['credit'] for x in res_assets]),
                    "balance": sum([x['balance'] for x in res_assets]),

                })

        return final_data


    def main_headers(self, data, partner):
        final_data = []
        # for i in ("Assets","Invoices", "Deposits"):
        for i in ["Invoices","Deposits","Assets"]:
            if i == "Invoices":
                final_data.append({
                    "name": (_("Invoices")),
                    "lines": self.get_invoices_data(data,partner)
                })
            elif i == "Deposits":
                final_data.append({
                    "name": (_("Deposits")),
                    "lines": self.get_deposits_data(data, partner)
                })
            elif i == "Assets":
                final_data.append({
                    "name": (_("Assets")),
                    "lines": self.get_assets_data(data, partner)
                })
        return final_data

    def get_assets_data(self, data,partner):
        final_data = []
        cr_invoice_ids = self.env['account.invoice'].search([('date_invoice', '>=', data['form']['date_from']),
                                                              ('date_invoice', '<=', data['form']['date_to']),
                                                              ('state', 'in', ('open', 'paid')),
                                                              ('type', '=', 'out_refund'),
                                                              ('residual', '!=', 0.0),
                                                              ('journal_id', 'in', data['form']['journal_ids']),
                                                              ('partner_id', '=', partner.id),
                                                              ('company_id', '=', data['form']['company_id'][0])
                                                              ])
        # print("--------cr_invoice_ids------------",cr_invoice_ids)
        if cr_invoice_ids:
            for inv in cr_invoice_ids:
                # print("--------inv----------------",inv)
                inv_vals = {
                    "id":inv.id,
                    "date":inv.date_invoice,
                    "x_jt_main1_id":inv.x_jt_main1_id,
                    "x_jt_main2_id":inv.x_jt_main2_id,
                    "x_jt_deposit_id":inv.x_jt_deposit_id,
                    "code":inv.journal_id.code,
                    "a_code":inv.account_id.code,
                    "a_name":inv.account_id.name,
                    "ref":inv.reference,
                    "move_name":inv.move_id.name,
                    "name":inv.name,
                    "state": inv.state,
                    "debit":inv.residual,
                    "credit":0.0,
                    "balance": inv.residual,
                    "amount_currency":0.0,
                    "currency_id":inv.currency_id,
                    "currency_code":False,
                    "progress": 0.0,
                    "displayed_name":'-'.join(field_name for field_name in (inv.move_id.name, inv.reference, '') if field_name not in (False,None, '', '/')),
                    "lines": []
                }
                final_data.append(inv_vals)
        payment_ids = self.env['account.payment'].search([('partner_id','=',partner.id),
                                                         ('state','in',('posted','reconciled')),
                                                         ('payment_type','=','inbound'),
                                                        ])
        # print("---------payment_ids----------------",payment_ids)
        if payment_ids:
            unlink_payment_ids = payment_ids.filtered(lambda p: not p.has_invoices)
            # print("-------unlink_payment_ids---------",unlink_payment_ids)
            if unlink_payment_ids:
                for payment in unlink_payment_ids:
                    payment_vals = {
                        "id": payment.id,
                        "date": payment.payment_date,
                        "x_jt_main1_id": payment.x_jt_main1_id,
                        "x_jt_main2_id": payment.x_jt_main2_id,
                        "x_jt_deposit_id": payment.x_jt_deposit_id,
                        "code": payment.journal_id.code,
                        "a_code": payment.destination_account_id.code,
                        "a_name": payment.destination_account_id.name,
                        "ref": '',
                        "move_name": payment.name,
                        "name": payment.name,
                        "state": payment.state,
                        "debit": payment.amount,
                        "credit": 0.0,
                        "balance": payment.amount,
                        "amount_currency": 0.0,
                        "currency_id": payment.currency_id,
                        "currency_code": False,
                        "progress": 0.0,
                        # "displayed_name": '-'.join(field_name for field_name in (inv.move_id.name, inv.reference, '') if field_name not in (False, None, '', '/')),
                        "lines": []
                    }
                    final_data.append(payment_vals)
        return final_data

    def get_deposits_data(self, data, partner):

        self.env.cr.execute("""
                        SELECT a.id
                        FROM account_account a
                        WHERE a.internal_type IN %s
                        AND NOT a.deprecated""", (tuple(["payable"]),))
        account_ids = [a for (a,) in self.env.cr.fetchall()]
        payable_aml_ids = self.env['account.move.line'].search([('date_maturity','>=',data['form']['date_from']),
                                                                ('date_maturity', '<=', data['form']['date_to']),
                                                                ('partner_id', '=', partner.id),
                                                                ('account_id','in',account_ids),
                                                                ('company_id', '=', data['form']['company_id'][0]),
                                                                ('move_id.state','=','posted'),
                                                                ])
        full_account = []
        if payable_aml_ids:
            temp = {}
            for line in payable_aml_ids:
                if line.x_jt_deposit_id in temp:
                    temp[line.x_jt_deposit_id] |= line
                else:
                    temp[line.x_jt_deposit_id] = line
            for k,v in temp.items():
                aml_lines = []
                previous_aml_ids = self.env['account.move.line'].search([('id','not in',v.ids),
                                                                ('partner_id', '=', partner.id),
                                                                ('x_jt_deposit_id', '=', k),
                                                                ('date_maturity','<',data['form']['date_from']),
                                                                ('company_id', '=', data['form']['company_id'][0]),
                                                                ('move_id.state','=','posted'),
                                                                ])
                sum_total_debit = 0.0
                sum_total_credit = 0.0
                sum_total_balance = 0.0
                if previous_aml_ids:
                    aml_lines.append({
                        "date": False,
                        "name": (_("Opening balance")),
                        "x_jt_main1_id": False,
                        "x_jt_main2_id": False,
                        "x_jt_deposit_id": k,
                        "account_name": False,
                        "account_code": False,
                        "analytic_account_name": False,
                        "qty": 1,
                        "amount": 0.0,
                        "debit": sum([x.debit for x in previous_aml_ids]),
                        "credit": sum([x.credit for x in previous_aml_ids]),
                        "balance": sum([x.balance for x in previous_aml_ids]),
                        "is_reversal": False,
                        "is_depreciate": False,
                        "item_type": "D",
                    })
                    sum_total_debit += sum([x.debit for x in previous_aml_ids])
                    sum_total_credit += sum([x.credit for x in previous_aml_ids])
                    sum_total_balance += sum([x.balance for x in previous_aml_ids])
                for pay_aml in v:
                    aml_lines.append({
                        "date": pay_aml.date_maturity,
                        "name": pay_aml.move_id.name + '-' + pay_aml.name,
                        "x_jt_main1_id": pay_aml.x_jt_main1_id,
                        "x_jt_main2_id": pay_aml.x_jt_main2_id,
                        "x_jt_deposit_id": pay_aml.x_jt_deposit_id,
                        "account_name": pay_aml.account_id.name,
                        "account_code": pay_aml.account_id.code,
                        "analytic_account_name": pay_aml.analytic_account_id.name,
                        "qty": pay_aml.quantity,
                        "amount": pay_aml.debit > 0.0 and pay_aml.debit or pay_aml.credit,
                        "debit": pay_aml.debit,
                        "credit": pay_aml.credit,
                        "balance": pay_aml.balance,
                        "is_reversal": pay_aml.is_reversal_line,
                        "is_depreciate": pay_aml.is_depreciate_line,
                        "item_type": "D",
                    })
                    sum_total_debit += pay_aml.debit
                    sum_total_credit += pay_aml.credit
                    sum_total_balance += pay_aml.balance
                full_account.append({
                    "id": False,
                    "date": False,
                    "x_jt_main1_id": False,
                    "x_jt_main2_id": False,
                    "x_jt_deposit_id": k,
                    "code": False,
                    "a_code": False,
                    "a_name": False,
                    "ref": False,
                    "move_name": k,
                    "name": False,
                    "state": False,
                    "debit": sum_total_debit,
                    "credit": sum_total_credit,
                    "balance": sum_total_balance,
                    "amount_currency": 0.0,
                    "currency_id": v[0].move_id.currency_id,
                    "currency_code": False,
                    "progress": 0.0,
                    "displayed_name": k,
                    "lines": aml_lines,
                    # "item_type": "D",
                })
        return full_account



    def get_invoices_data(self, data, partner):
        invoice_ids = self.env['account.invoice'].search([('date_invoice', '>=', data['form']['date_from']),
                                                          ('date_invoice', '<=', data['form']['date_to']),
                                                          ('state', 'in', ('open', 'paid')),
                                                          ('type', '=', 'out_invoice'),
                                                          ('journal_id', 'in', data['form']['journal_ids']),
                                                          ('partner_id', '=', partner.id),
                                                          ('company_id', '=', data['form']['company_id'][0])
                                                          ])
        full_account = []
        for inv in invoice_ids:
            # print("--------inv----------------",inv)
            inv_vals = {
                "id":inv.id,
                "date":inv.date_invoice,
                "x_jt_main1_id":inv.x_jt_main1_id,
                "x_jt_main2_id":inv.x_jt_main2_id,
                "x_jt_deposit_id":inv.x_jt_deposit_id,
                "code":inv.journal_id.code,
                "a_code":inv.account_id.code,
                "a_name":inv.account_id.name,
                "ref":inv.reference,
                "move_name":inv.move_id.name,
                "name":inv.name,
                "state": inv.state,
                "debit":inv.amount_total,
                "credit":inv.amount_total - inv.residual,
                "balance": inv.residual,
                "amount_currency":0.0,
                "currency_id":inv.currency_id,
                "currency_code":False,
                "progress": 0.0,
                "displayed_name":'-'.join(field_name for field_name in (inv.move_id.name, inv.reference, '') if field_name not in (False,None, '', '/')),
                "lines": []
            }
            inv_lines = []
            for line in inv.invoice_line_ids:
                inv_lines.append({
                    "date": inv.date_invoice,
                    "name": line.product_id.name,
                     "x_jt_main1_id":inv.x_jt_main1_id,
                     "x_jt_main2_id":inv.x_jt_main2_id,
                     "x_jt_deposit_id":inv.x_jt_deposit_id,
                     "account_name": line.account_id.name,
                    "account_code": line.account_id.code,
                    "analytic_account_name": line.account_analytic_id.name,
                    "qty": line.quantity,
                    "amount": line.price_total,
                    "debit": 0.0,
                    "credit": 0.0,
                    "balance": 0.0,
                    "is_reversal": line.is_reversal,
                    "is_depreciate": line.is_depreciation,
                    "item_type": "I",
                })

            if inv.payment_move_line_ids:
                for aml in inv.payment_move_line_ids:
                    # print("--------aml-------------",aml)
                    # print("--------aml----debit---------",aml.debit)
                    # print("--------aml----credit---------",aml.credit)
                    amount = sum([p.amount for p in aml.matched_debit_ids if p.debit_move_id in inv.move_id.line_ids])
                    # print("--------amount_currency-----------",amount)
                    # amount1 = sum(
                    #     [p.amount for p in aml.matched_credit_ids if p.credit_move_id in inv.move_id.line_ids])
                    # print("---------amount1------------",amount1)
                    inv_lines.append({
                        "date": aml.date_maturity,
                        "name": aml.move_id.name+'-'+aml.name,
                        "x_jt_main1_id": aml.x_jt_main1_id,
                        "x_jt_main2_id": aml.x_jt_main2_id,
                        "x_jt_deposit_id": aml.x_jt_deposit_id,
                        "account_name": aml.account_id.name,
                        "account_code": aml.account_id.code,
                        "analytic_account_name": aml.analytic_account_id.name,
                        "qty": aml.quantity,
                        "amount": amount,
                        "debit": amount,
                        "credit": 0.0,
                        "balance": 0.0,
                        "is_reversal": aml.is_reversal_line,
                        "is_depreciate": aml.is_depreciate_line,
                        "item_type": (aml.is_reversal_line or aml.is_depreciate_line) and "C" or "P",
                    })
            inv_vals['lines'] = inv_lines
            full_account.append(inv_vals)
        return full_account




    # def _lines(self, data, partner):
    #     full_account = []
    #     self.env.cr.execute("""
    #                 SELECT a.id
    #                 FROM account_account a
    #                 WHERE a.internal_type IN %s
    #                 AND NOT a.deprecated""", (tuple(["payable"]),))
    #     account_ids = [a for (a,) in self.env.cr.fetchall()]
    #     payable_aml_ids = self.env['account.move.line'].search([('date_maturity','>=',data['form']['date_from']),
    #                                                             ('date_maturity', '<=', data['form']['date_to']),
    #                                                             ('partner_id', '=', partner.id),
    #                                                             ('account_id','in',account_ids),
    #                                                             ('company_id', '=', data['form']['company_id'][0]),
    #                                                             ('move_id.state','=','posted'),
    #                                                             ])
    #     invoice_ids = self.env['account.invoice'].search([('date_invoice','>=',data['form']['date_from']),
    #                                                       ('date_invoice', '<=',data['form']['date_to']),
    #                                                       ('state','in',('open','paid')),
    #                                                       ('type','=','out_invoice'),
    #                                                       ('journal_id','in',data['form']['journal_ids']),
    #                                                       ('partner_id','=',partner.id),
    #                                                       ('company_id','=',data['form']['company_id'][0])
    #                                                       ])
    #     cr_invoice_ids = self.env['account.invoice'].search([('date_invoice', '>=', data['form']['date_from']),
    #                                                       ('date_invoice', '<=', data['form']['date_to']),
    #                                                       ('state', 'in', ('open', 'paid')),
    #                                                       ('type', '=', 'out_refund'),
    #                                                       ('residual', '!=', 0.0),
    #                                                       ('journal_id', 'in', data['form']['journal_ids']),
    #                                                       ('partner_id', '=', partner.id),
    #                                                       ('company_id', '=', data['form']['company_id'][0])
    #                                                       ])
    #     print("--------cr_invoice_ids------------",cr_invoice_ids)
    #     payment_ids = self.env['account.payment'].search([
    #                                                              ('partner_id','=',partner.id),
    #                                                              ('state','in',('posted','reconciled')),
    #                                                              ('payment_type','=','inbound'),
    #                                                              ])
    #     print("---------payment_ids----------------",payment_ids)
    #     if payment_ids:
    #         unlink_payment_ids = payment_ids.filtered(lambda p: not p.has_invoices)
    #         print("-------unlink_payment_ids---------",unlink_payment_ids)
    #
    #     # stop
    #
    #     for inv in invoice_ids:
    #         print("--------inv----------------",inv)
    #         inv_vals = {
    #             "id":inv.id,
    #             "date":inv.date_invoice,
    #             "x_jt_main1_id":inv.x_jt_main1_id,
    #             "x_jt_main2_id":inv.x_jt_main2_id,
    #             "x_jt_deposit_id":inv.x_jt_deposit_id,
    #             "code":inv.journal_id.code,
    #             "a_code":inv.account_id.code,
    #             "a_name":inv.account_id.name,
    #             "ref":inv.reference,
    #             "move_name":inv.move_id.name,
    #             "name":inv.name,
    #             "state": inv.state,
    #             "debit":inv.amount_total,
    #             "credit":inv.amount_total - inv.residual,
    #             "balance": inv.residual,
    #             "amount_currency":0.0,
    #             "currency_id":inv.currency_id,
    #             "currency_code":False,
    #             "progress": 0.0,
    #             "displayed_name":'-'.join(field_name for field_name in (inv.move_id.name, inv.reference, '') if field_name not in (False,None, '', '/')),
    #             "lines": []
    #         }
    #         inv_lines = []
    #         for line in inv.invoice_line_ids:
    #             inv_lines.append({
    #                 "date": inv.date_invoice,
    #                 "name": line.product_id.name,
    #                  "x_jt_main1_id":inv.x_jt_main1_id,
    #                  "x_jt_main2_id":inv.x_jt_main2_id,
    #                  "x_jt_deposit_id":inv.x_jt_deposit_id,
    #                  "account_name": line.account_id.name,
    #                 "account_code": line.account_id.code,
    #                 "analytic_account_name": line.account_analytic_id.name,
    #                 "qty": line.quantity,
    #                 "amount": line.price_total,
    #                 "debit": 0.0,
    #                 "credit": 0.0,
    #                 "balance": 0.0,
    #                 "is_reversal": line.is_reversal,
    #                 "is_depreciate": line.is_depreciation,
    #                 "item_type": "I",
    #             })
    #
    #         if inv.payment_move_line_ids:
    #             for aml in inv.payment_move_line_ids:
    #                 print("--------aml-------------",aml)
    #                 print("--------aml----debit---------",aml.debit)
    #                 print("--------aml----credit---------",aml.credit)
    #                 amount = sum([p.amount for p in aml.matched_debit_ids if p.debit_move_id in inv.move_id.line_ids])
    #                 print("--------amount_currency-----------",amount)
    #                 # amount1 = sum(
    #                 #     [p.amount for p in aml.matched_credit_ids if p.credit_move_id in inv.move_id.line_ids])
    #                 # print("---------amount1------------",amount1)
    #                 inv_lines.append({
    #                     "date": aml.date_maturity,
    #                     "name": aml.move_id.name+'-'+aml.name,
    #                     "x_jt_main1_id": aml.x_jt_main1_id,
    #                     "x_jt_main2_id": aml.x_jt_main2_id,
    #                     "x_jt_deposit_id": aml.x_jt_deposit_id,
    #                     "account_name": aml.account_id.name,
    #                     "account_code": aml.account_id.code,
    #                     "analytic_account_name": aml.analytic_account_id.name,
    #                     "qty": aml.quantity,
    #                     "amount": amount,
    #                     "debit": amount,
    #                     "credit": 0.0,
    #                     "balance": 0.0,
    #                     "is_reversal": aml.is_reversal_line,
    #                     "is_depreciate": aml.is_depreciate_line,
    #                     "item_type": (aml.is_reversal_line or aml.is_depreciate_line) and "C" or "P",
    #                 })
    #         inv_vals['lines'] = inv_lines
    #         full_account.append(inv_vals)
    #     if payable_aml_ids:
    #         temp = {}
    #
    #         for line in payable_aml_ids:
    #             if line.x_jt_deposit_id in temp:
    #                 temp[line.x_jt_deposit_id] |= line
    #             else:
    #                 temp[line.x_jt_deposit_id] = line
    #         for k,v in temp.items():
    #             aml_lines = []
    #             previous_aml_ids = self.env['account.move.line'].search([('id','not in',v.ids),
    #                                                             ('partner_id', '=', partner.id),
    #                                                             ('x_jt_deposit_id', '=', k),
    #                                                             ('date_maturity','<',data['form']['date_from']),
    #                                                             ('company_id', '=', data['form']['company_id'][0]),
    #                                                             ('move_id.state','=','posted'),
    #                                                             ])
    #             sum_total_debit = 0.0
    #             sum_total_credit = 0.0
    #             sum_total_balance = 0.0
    #             if previous_aml_ids:
    #                 aml_lines.append({
    #                     "date": False,
    #                     "name": "Opening balance",
    #                     "x_jt_main1_id": False,
    #                     "x_jt_main2_id": False,
    #                     "x_jt_deposit_id": k,
    #                     "account_name": False,
    #                     "account_code": False,
    #                     "analytic_account_name": False,
    #                     "qty": 1,
    #                     "amount": 0.0,
    #                     "debit": sum([x.debit for x in previous_aml_ids]),
    #                     "credit": sum([x.credit for x in previous_aml_ids]),
    #                     "balance": sum([x.balance for x in previous_aml_ids]),
    #                     "is_reversal": False,
    #                     "is_depreciate": False,
    #                     "item_type": "D",
    #                 })
    #                 sum_total_debit += sum([x.debit for x in previous_aml_ids])
    #                 sum_total_credit += sum([x.credit for x in previous_aml_ids])
    #                 sum_total_balance += sum([x.balance for x in previous_aml_ids])
    #             for pay_aml in v:
    #                 aml_lines.append({
    #                     "date": pay_aml.date_maturity,
    #                     "name": pay_aml.move_id.name + '-' + pay_aml.name,
    #                     "x_jt_main1_id": pay_aml.x_jt_main1_id,
    #                     "x_jt_main2_id": pay_aml.x_jt_main2_id,
    #                     "x_jt_deposit_id": pay_aml.x_jt_deposit_id,
    #                     "account_name": pay_aml.account_id.name,
    #                     "account_code": pay_aml.account_id.code,
    #                     "analytic_account_name": pay_aml.analytic_account_id.name,
    #                     "qty": pay_aml.quantity,
    #                     "amount": pay_aml.debit > 0.0 and pay_aml.debit or pay_aml.credit,
    #                     "debit": pay_aml.debit,
    #                     "credit": pay_aml.credit,
    #                     "balance": pay_aml.balance,
    #                     "is_reversal": pay_aml.is_reversal_line,
    #                     "is_depreciate": pay_aml.is_depreciate_line,
    #                     "item_type": "D",
    #                 })
    #                 sum_total_debit += pay_aml.debit
    #                 sum_total_credit += pay_aml.credit
    #                 sum_total_balance += pay_aml.balance
    #             full_account.append({
    #                 "id": False,
    #                 "date": False,
    #                 "x_jt_main1_id": False,
    #                 "x_jt_main2_id": False,
    #                 "x_jt_deposit_id": k,
    #                 "code": False,
    #                 "a_code": False,
    #                 "a_name": False,
    #                 "ref": False,
    #                 "move_name": k,
    #                 "name": False,
    #                 "state": False,
    #                 "debit": sum_total_debit,
    #                 "credit": sum_total_credit,
    #                 "balance": sum_total_balance,
    #                 "amount_currency": 0.0,
    #                 "currency_id": v[0].move_id.currency_id,
    #                 "currency_code": False,
    #                 "progress": 0.0,
    #                 "displayed_name": k,
    #                 "lines": aml_lines,
    #                 # "item_type": "D",
    #             })
    #     # import pprint
    #     # print("------full_account--------------",pprint.pformat(full_account))
    #     return full_account

    def _sum_partner(self, data, partner, field):
        if field not in ['debit', 'credit', 'balance']:
            return
        result = 0.0
        query_get_data = self.env['account.move.line'].with_context(data['form'].get('used_context', {}))._query_get()
        reconcile_clause = "" if data['form']['reconciled'] else ' AND "account_move_line".full_reconcile_id IS NULL '

        params = [partner.id, tuple(data['computed']['move_state']), tuple(data['computed']['account_ids'])] + query_get_data[2]
        query = """SELECT sum(""" + field + """)
                FROM """ + query_get_data[0] + """, account_move AS m
                WHERE "account_move_line".partner_id = %s
                    AND m.id = "account_move_line".move_id
                    AND m.state IN %s
                    AND account_id IN %s
                    AND """ + query_get_data[1] + reconcile_clause
        self.env.cr.execute(query, tuple(params))

        contemp = self.env.cr.fetchone()
        if contemp is not None:
            result = contemp[0] or 0.0
        return result

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        data['computed'] = {}

        obj_partner = self.env['res.partner']
        query_get_data = self.env['account.move.line'].with_context(data['form'].get('used_context', {}))._query_get()
        data['computed']['move_state'] = ['draft', 'posted']
        if data['form'].get('target_move', 'all') == 'posted':
            data['computed']['move_state'] = ['posted']
        result_selection = data['form'].get('result_selection', False)
        print("----result_selection--------",result_selection)
        if result_selection == 'supplier':
            data['computed']['ACCOUNT_TYPE'] = ['payable']
        elif result_selection == 'customer':
            data['computed']['ACCOUNT_TYPE'] = ['receivable']
        else:
            print("------esle------------")
            data['computed']['ACCOUNT_TYPE'] = ['payable', 'receivable']

        self.env.cr.execute("""
            SELECT a.id
            FROM account_account a
            WHERE a.internal_type IN %s
            AND NOT a.deprecated""", (tuple(data['computed']['ACCOUNT_TYPE']),))
        data['computed']['account_ids'] = [a for (a,) in self.env.cr.fetchall()]
        params = [tuple(data['computed']['move_state']), tuple(data['computed']['account_ids'])] + query_get_data[2]
        reconcile_clause = "" if data['form']['reconciled'] else ' AND "account_move_line".full_reconcile_id IS NULL '
        query = """
            SELECT DISTINCT "account_move_line".partner_id
            FROM """ + query_get_data[0] + """, account_account AS account, account_move AS am
            WHERE "account_move_line".partner_id IS NOT NULL
                AND "account_move_line".account_id = account.id
                AND am.id = "account_move_line".move_id
                AND am.state IN %s
                AND "account_move_line".account_id IN %s
                AND NOT account.deprecated
                AND """ + query_get_data[1] + reconcile_clause
        self.env.cr.execute(query, tuple(params))
        partner_ids = [res['partner_id'] for res in self.env.cr.dictfetchall()]
        # partners = obj_partner.browse(partner_ids)
        partners = obj_partner.browse(data['form']['partner_id'][0])
        partners = sorted(partners, key=lambda x: (x.ref or '', x.name or ''))

        return {
            'doc_ids': partner_ids,
            'doc_model': self.env['res.partner'],
            'data': data,
            'docs': partners,
            'time': time,
            'main_headers': self.main_headers,
            'main_headers_total': self.main_headers_total,
            # 'lines': self._lines,
            'sum_partner': self._sum_partner,
        }
