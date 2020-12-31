# -*- coding: utf-8 -*-

import time
from odoo import api, models, _
from odoo.exceptions import UserError


class ReportPartnerLedgerPdf(models.AbstractModel):
    _name = 'report.justthis_customization.report_partnerledger_pdf'

    def _lines(self, data, partner):
        full_account = []
        self.env.cr.execute("""
                    SELECT a.id
                    FROM account_account a
                    WHERE a.internal_type IN %s
                    AND NOT a.deprecated""", (tuple(["payable"]),))
        account_ids = [a for (a,) in self.env.cr.fetchall()]
        print("------account_ids------------",account_ids)
        payable_aml_ids = self.env['account.move.line'].search([('date_maturity','>=',data['form']['date_from']),
                                                                ('date_maturity', '<=', data['form']['date_to']),
                                                                ('partner_id', '=', partner.id),
                                                                ('account_id','in',account_ids),
                                                                ('company_id', '=', data['form']['company_id'][0]),
                                                                ('move_id.state','=','posted'),
                                                                ])
        invoice_ids = self.env['account.invoice'].search([('date_invoice','>=',data['form']['date_from']),
                                                          ('date_invoice', '<=',data['form']['date_to']),
                                                          ('state','in',('open','paid')),
                                                          ('type','=','out_invoice'),
                                                          ('journal_id','in',data['form']['journal_ids']),
                                                          ('partner_id','=',partner.id),
                                                          ('company_id','=',data['form']['company_id'][0])
                                                          ])



        for inv in invoice_ids:
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
            # payment_vals = inv._get_payments_vals()
            # print("---------payment-------",payment_vals)
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
                    "is_reversal": line.is_reversal,
                    "is_depreciate": line.is_depreciation
                })

            if inv.payment_move_line_ids:
                for aml in inv.payment_move_line_ids:
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
                        "amount": aml.debit > 0.0 and aml.debit or aml.credit,
                        "is_reversal": aml.is_reversal_line,
                        "is_depreciate": aml.is_depreciate_line
                    })
            inv_vals['lines'] = inv_lines
            full_account.append(inv_vals)
        if payable_aml_ids:
            for pay_aml in payable_aml_ids:
                full_account.append({
                    "id": pay_aml.id,
                    "date": pay_aml.date_maturity,
                    "x_jt_main1_id": pay_aml.x_jt_main1_id,
                    "x_jt_main2_id": pay_aml.x_jt_main2_id,
                    "x_jt_deposit_id": pay_aml.x_jt_deposit_id,
                    "code": pay_aml.move_id.journal_id.code,
                    "a_code": pay_aml.account_id.code,
                    "a_name": pay_aml.account_id.name,
                    "ref": pay_aml.move_id.ref,
                    "move_name": pay_aml.move_id.name,
                    "name": pay_aml.name,
                    "state": pay_aml.move_id.state,
                    "debit": pay_aml.debit,
                    "credit": pay_aml.credit,
                    "balance": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": pay_aml.move_id.currency_id,
                    "currency_code": False,
                    "progress": 0.0,
                    "displayed_name": '-'.join(field_name for field_name in (pay_aml.move_id.name, pay_aml.move_id.ref, '') if field_name not in (False, None, '', '/')),
                    "lines": []
                })



                # full_account.append({
                #     "date": pay_aml.date_maturity,
                #     "name": pay_aml.move_id.name + '-' + pay_aml.name,
                #     "x_jt_main1_id": pay_aml.x_jt_main1_id,
                #     "x_jt_main2_id": pay_aml.x_jt_main2_id,
                #     "x_jt_deposit_id": pay_aml.x_jt_deposit_id,
                #     "account_name": pay_aml.account_id.name,
                #     "account_code": pay_aml.account_id.code,
                #     "analytic_account_name": pay_aml.analytic_account_id.name,
                #     "qty": pay_aml.quantity,
                #     "amount": pay_aml.debit > 0.0 and pay_aml.debit or pay_aml.credit,
                #     "is_reversal": pay_aml.is_reversal_line,
                #     "is_depreciate": pay_aml.is_depreciate_line
                # })

        import pprint
        print("------full_account--------------",pprint.pformat(full_account))

        # stop
        # currency = self.env['res.currency']
        # print("-------data--all----",data)
        # data['computed']['ACCOUNT_TYPE'] = ['receivable','payable']
        # print("-------data['computed']----",data['computed'])
        # query_get_data = self.env['account.move.line'].with_context(data['form'].get('used_context', {}))._query_get()
        # reconcile_clause = "" if data['form']['reconciled'] else ' AND "account_move_line".full_reconcile_id IS NULL '
        # params = [partner.id, tuple(data['computed']['move_state']), tuple(data['computed']['account_ids'])] + query_get_data[2]
        # query = """
        #     SELECT "account_move_line".id, "account_move_line".invoice_id, "account_move_line".date,"account_move_line".x_jt_main1_id,"account_move_line".x_jt_main2_id,"account_move_line".x_jt_deposit_id, j.code, acc.code as a_code, acc.name as a_name, "account_move_line".ref, m.name as move_name, "account_move_line".name, "account_move_line".debit, "account_move_line".credit, "account_move_line".amount_currency,"account_move_line".currency_id, c.symbol AS currency_code
        #     FROM """ + query_get_data[0] + """
        #     LEFT JOIN account_journal j ON ("account_move_line".journal_id = j.id)
        #     LEFT JOIN account_account acc ON ("account_move_line".account_id = acc.id)
        #     LEFT JOIN res_currency c ON ("account_move_line".currency_id=c.id)
        #     LEFT JOIN account_move m ON (m.id="account_move_line".move_id)
        #     WHERE "account_move_line".partner_id = %s
        #         AND m.state IN %s
        #         AND "account_move_line".account_id IN %s AND """ + query_get_data[1] + reconcile_clause + """
        #         ORDER BY "account_move_line".date"""
        # print("--------query--------------",query)
        # print("--------params--------------",params)
        # self.env.cr.execute(query, tuple(params))
        # res = self.env.cr.dictfetchall()
        # print("-------res-------------------",res)
        # stop
        # sum = 0.0
        # lang_code = self.env.context.get('lang') or 'en_US'
        # lang = self.env['res.lang']
        # lang_id = lang._lang_get(lang_code)
        # date_format = lang_id.date_format
        # for r in res:
        #     r['date'] = r['date']
        #     r['displayed_name'] = '-'.join(
        #         r[field_name] for field_name in ('move_name', 'ref', 'name')
        #         if r[field_name] not in (None, '', '/')
        #     )
        #     sum += r['debit'] - r['credit']
        #     r['progress'] = sum
        #     r['currency_id'] = currency.browse(r.get('currency_id'))
        #     full_account.append(r)
        return full_account

    def _sum_partner(self, data, partner, field):
        if field not in ['debit', 'credit', 'debit - credit']:
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
            'lines': self._lines,
            'sum_partner': self._sum_partner,
        }
