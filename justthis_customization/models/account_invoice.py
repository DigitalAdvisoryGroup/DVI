# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    def display_swiss_qr_code(self):
        self.ensure_one()
        qr_parameter = self.env['ir.config_parameter'].sudo().get_param('justthis_customization.print_qr_code')
        return self.partner_id.country_id.code == 'CH' and qr_parameter

    @api.multi
    def open_depreciation_wizard(self):
        for inv in self:
            action = self.env.ref('justthis_customization.action_account_invoice_depreciation').read()[0]
            return action

    @api.multi
    def open_reversal_wizard(self):
        for inv in self:
            action = self.env.ref('justthis_customization.action_account_invoice_reversal').read()[0]
            return action

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None,
                        description=None, journal_id=None):
        res = super(AccountInvoice, self)._prepare_refund(invoice=invoice,date_invoice=date_invoice,date=date,description=description,journal_id=journal_id)
        ctx = dict(self._context or {})
        if ctx and ctx.get("sel_invoice_lines"):
            res['invoice_line_ids'] = self._refund_cleanup_lines(ctx['sel_invoice_lines'])
        return res

    @api.model
    def _get_payments_vals(self):
        res = super(AccountInvoice, self)._get_payments_vals()
        if self.payment_move_line_ids and res:
            for payment in self.payment_move_line_ids:
                for line in res:
                    if line['payment_id'] == payment.id:
                        line['text_name'] = payment.is_reversal_line and "Reverted" or payment.is_depreciate_line and "Depreciated" or "Paid"
        return res


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    is_reversal = fields.Boolean("Is Reversal")