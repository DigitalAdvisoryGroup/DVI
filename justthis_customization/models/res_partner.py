# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.
import json

from odoo import models, api, fields
import base64
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def get_partner_ledger_report(self, from_date=False, from_to=False):
        if self and from_date and from_to:
            partner_ledger_vals = {
                "partner_id": self.id,
                "date_from": from_date,
                "date_to": from_to
            }
            partner_ledger_id = self.env['account.financial.report.pdf'].create(partner_ledger_vals)
            res = partner_ledger_id.check_report()
            pdf = self.env.ref('justthis_customization.action_report_partnerledger_pdf').sudo().render_qweb_pdf(
                [partner_ledger_id],data=res.get("data"))
            b64_pdf = base64.b64encode(pdf[0])
            report_name = self.env.ref(
                'justthis_customization.action_report_partnerledger_pdf').report_action(
                self, data=res.get("data"))
            return {"status": True, 'base64_content': b64_pdf,'report_name': report_name.get('name')}
        return {'status': False,
                "msg": "Partner,Fromdate,Todate is required."}


    def get_assets_data(self, date_from=False, date_to=False):
        jounral_id = self.env['account.journal'].sudo().search([('company_id', '=', self.company_id.id)])
        final_data = []
        cr_invoice_ids = self.env['account.invoice'].sudo().search([('date_invoice', '>=', date_from),
                                                             ('date_invoice', '<=', date_to),
                                                             ('state', 'in', ('open', 'paid')),
                                                             ('type', '=', 'out_refund'),
                                                             ('residual', '!=', 0.0),
                                                             ('journal_id', 'in', jounral_id.ids),
                                                             ('partner_id', '=', self.id),
                                                             ('company_id', '=', self.env.user.company_id.id)
                                                             ])
        if cr_invoice_ids:
            for inv in cr_invoice_ids:
                inv_vals = {
                    "id": inv.id,
                    "date": inv.date_invoice,
                    "x_jt_main1_id": inv.x_jt_main1_id,
                    "x_jt_main2_id": inv.x_jt_main2_id,
                    "x_jt_deposit_id": inv.x_jt_deposit_id,
                    "code": inv.journal_id.code,
                    "a_code": inv.account_id.code,
                    "a_name": inv.account_id.name,
                    "ref": inv.reference,
                    "move_name": inv.move_id.name,
                    "name": inv.name,
                    "state": inv.state,
                    "debit": inv.residual,
                    "credit": 0.0,
                    "balance": inv.residual,
                    "amount_currency": 0.0,
                    "currency_id": inv.currency_id,
                    "currency_code": False,
                    "progress": 0.0,
                    "displayed_name": '-'.join(field_name for field_name in (inv.move_id.name, inv.reference, '') if field_name not in (False, None, '', '/')),
                    "lines": []
                }
                final_data.append(inv_vals)
        payment_ids = self.env['account.payment'].search([('partner_id', '=', self.id),
                                                          ('state', 'in', ('posted', 'reconciled')),
                                                          ('payment_type', '=', 'inbound'),
                                                          ])
        if payment_ids:
            for payment in payment_ids:
                if payment.amount > sum([x.amount_total - x.residual for x in payment.invoice_ids]):
            # unlink_payment_ids = payment_ids.filtered(lambda p: not p.has_invoices)
            # if unlink_payment_ids:
            #     for payment in unlink_payment_ids:
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
                        "credit": payment.amount - sum([x.amount_total - x.residual for x in payment.invoice_ids]),
                        "debit": 0.0,
                        "balance": 0.0 - (payment.amount - sum([x.amount_total - x.residual for x in payment.invoice_ids])),
                        "amount_currency": 0.0,
                        "currency_id": payment.currency_id.name,
                        "currency_code": False,
                        "progress": 0.0,
                        "lines": []
                    }
                    final_data.append(payment_vals)
        self.env.cr.execute("""
                                        SELECT a.id
                                        FROM account_account a
                                        WHERE a.internal_type IN %s
                                        AND NOT a.deprecated""", (tuple(["receivable"]),))
        account_ids = [a for (a,) in self.env.cr.fetchall()]
        print("---------account_ids------------", account_ids)
        asset_aml_ids = self.env['account.move.line'].search([('partner_id', '=', self.id),
                                                              ('date_maturity', '>=', date_from),
                                                              ('date_maturity', '<=', date_to),
                                                              ('invoice_id', '=', False),
                                                              ('matched_credit_ids', '=', False),
                                                              ('matched_debit_ids', '=', False),
                                                              ('account_id', 'in', account_ids),
                                                              ('move_id.state', '=', 'posted'),
                                                              ('company_id', '=', self.env.user.company_id.id)
                                                              ])
        print("-------asset_aml_ids-----------", asset_aml_ids)
        if asset_aml_ids:
            for line in asset_aml_ids:
                final_data.append({
                    "id": line.id,
                    "date": line.date_maturity,
                    "x_jt_main1_id": line.x_jt_main1_id,
                    "x_jt_main2_id": line.x_jt_main2_id,
                    "x_jt_deposit_id": line.x_jt_deposit_id,
                    "code": line.move_id.journal_id.code,
                    "a_code": line.account_id.code,
                    "a_name": line.account_id.name,
                    "ref": line.name,
                    "move_name": line.move_id.name,
                    "name": False,
                    "state": False,
                    "debit": line.debit,
                    "credit": line.credit,
                    "balance": line.balance,
                    "amount_currency": 0.0,
                    "currency_id": line.move_id.currency_id.name,
                    "currency_code": False,
                    "progress": 0.0,
                    "displayed_name": line.move_id.name,
                    "lines": [],
                })
        return final_data


