# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError


class AccountInvoiceReversal(models.TransientModel):
    """Reversal Notes"""

    _name = "account.invoice.reversal"
    _description = "Reversal Note"

    @api.model
    def _get_inv(self):
        context = dict(self._context or {})
        return context.get('active_id', False)

    @api.model
    def _get_reason(self):
        context = dict(self._context or {})
        active_id = context.get('active_id', False)
        if active_id:
            inv = self.env['account.invoice'].browse(active_id)
            return inv.x_reason_rev and inv.x_reason_rev.x_name or False
        return ''

    @api.model
    def _get_inv_comment(self):
        context = dict(self._context or {})
        active_id = context.get('active_id', False)
        if active_id:
            inv = self.env['account.invoice'].browse(active_id)
            return inv.x_comment_rev or False
        return ''

    @api.model
    def _get_inv_user(self):
        context = dict(self._context or {})
        active_id = context.get('active_id', False)
        if active_id:
            inv = self.env['account.invoice'].browse(active_id)
            return inv.x_user_rev or False
        return ''


    date_invoice = fields.Date(string='Reversal Note Date',default=fields.Date.context_today,required=True)
    date = fields.Date(string='Accounting Date')
    description = fields.Char(string='Reason', required=True,default=_get_reason)
    inv_comment = fields.Char(string='Comment', required=True,default=_get_inv_comment)
    inv_user = fields.Char(string='User', required=True,default=_get_inv_user)
    invoice_id = fields.Many2one("account.invoice",string='Invoice', required=True,default=_get_inv)
    invoice_line_ids = fields.Many2many("account.invoice.line", string="Invoice Lines", required=True)


    def _get_reversal_refund(self, inv):
        self.ensure_one()
        if inv.state in ['draft', 'cancel']:
            raise UserError(_('Cannot create Depreciation note for the draft/cancelled invoice.'))
        date = self.date or False
        description = self.description or inv.name
        return inv.with_context(sel_invoice_lines=self.invoice_line_ids).refund(self.date_invoice, date, description, inv.journal_id.id)

    @api.multi
    def invoice_reversal(self):
        created_inv = []
        for rec in self:
            if not rec.invoice_line_ids:
                raise UserError(_(
                    'Cannot create Reversal note. Please select atleast one invoice line.'))
            context = dict(self._context or {})
            active_id = context.get('active_id', False)
            if active_id:
                inv = self.env['account.invoice'].browse(active_id)
                refund = rec._get_reversal_refund(inv)
                created_inv.append(refund.id)
                movelines = inv.move_id.line_ids
                to_reconcile_ids = {}
                to_reconcile_lines = self.env['account.move.line']
                for line in movelines:
                    if line.account_id.id == inv.account_id.id:
                        to_reconcile_lines += line
                        to_reconcile_ids.setdefault(line.account_id.id,
                                                    []).append(line.id)
                    if line.reconciled:
                        line.remove_move_reconcile()
                refund.action_invoice_open()
                for tmpline in refund.move_id.line_ids:
                    tmpline.write({'x_reason_rev':inv.x_reason_rev and inv.x_reason_rev.id,
                                   'x_comment_rev': inv.x_comment_rev,
                                   'x_user_rev': inv.x_user_rev,
                                   'is_reversal_line': True,
                                   })
                    if tmpline.account_id.id == inv.account_id.id:
                        to_reconcile_lines += tmpline
                to_reconcile_lines.filtered(
                    lambda l: l.reconciled == False).reconcile()
                result = self.env.ref('account.action_invoice_out_refund').read()[0]
                invoice_domain = safe_eval(result['domain'])
                invoice_domain.append(('id', 'in', created_inv))
                result['domain'] = invoice_domain
                rec.invoice_line_ids.write({'is_reversal': True})
                return result