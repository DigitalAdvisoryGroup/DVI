# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError


class AccountInvoiceDepreciation(models.TransientModel):
    """Depreciation Notes"""

    _name = "account.invoice.depreciation"
    _description = "Depreciation Note"

    @api.model
    def _get_reason(self):
        context = dict(self._context or {})
        active_id = context.get('active_id', False)
        if active_id:
            inv = self.env['account.invoice'].browse(active_id)
            return inv.x_reason_dep and inv.x_reason_dep.x_name or False
        return ''

    @api.model
    def _get_inv_comment(self):
        context = dict(self._context or {})
        active_id = context.get('active_id', False)
        if active_id:
            inv = self.env['account.invoice'].browse(active_id)
            return inv.x_comment_dep or False
        return ''

    @api.model
    def _get_inv_user(self):
        context = dict(self._context or {})
        active_id = context.get('active_id', False)
        if active_id:
            inv = self.env['account.invoice'].browse(active_id)
            return inv.x_user_dep or False
        return ''

    @api.model
    def _get_deault_account_id(self):
        context = dict(self._context or {})
        active_id = context.get('active_id', False)
        if active_id:
            inv = self.env['account.invoice'].browse(active_id)
            return inv.company_id.x_dep_default_account and inv.company_id.x_dep_default_account.id or False
        return False

    @api.model
    def _get_deault_analytic_id(self):
        context = dict(self._context or {})
        active_id = context.get('active_id', False)
        if active_id:
            inv = self.env['account.invoice'].browse(active_id)
            if inv.invoice_line_ids:
                return inv.invoice_line_ids[0].account_analytic_id and inv.invoice_line_ids[0].account_analytic_id.id or False
        return False

    date_invoice = fields.Date(string='Depreciation Note Date',default=fields.Date.context_today,required=True)
    date = fields.Date(string='Accounting Date')
    description = fields.Char(string='Reason', required=True,default=_get_reason)
    inv_comment = fields.Char(string='Comment', required=True,default=_get_inv_comment)
    inv_user = fields.Char(string='User', required=True,default=_get_inv_user)
    depreciation_account_id = fields.Many2one("account.account",'Depreciation Account', required=True,default=_get_deault_account_id)
    analytic_account_id = fields.Many2one("account.analytic.account",'Analytic Account', required=True,default=_get_deault_analytic_id)


    def _get_depreciation_refund(self, inv,analytic_account_id):
        self.ensure_one()
        if inv.state in ['draft', 'cancel']:
            raise UserError(_('Cannot create Depreciation note for the draft/cancelled invoice.'))
        # if inv.reconciled:
        #     raise UserError(_(
        #         'Cannot create a Depreciation note for the invoice which is already reconciled, invoice should be unreconciled first, then only you can add Depreciation note for this invoice.'))
        date = self.date or False
        description = self.description or inv.name
        return inv.refund_dep(self.date_invoice, date, description, inv.journal_id.id, self.env.user.company_id.x_dep_default_prd,inv.x_amount_dep,analytic_account_id)

    @api.multi
    def invoice_depreciation(self):
        created_inv = []
        for rec in self:
            context = dict(self._context or {})
            active_id = context.get('active_id', False)
            if active_id:
                inv = self.env['account.invoice'].browse(active_id)
                if inv.x_amount_dep > inv.amount_total:
                    raise UserError(_(
                        'Cannot create depreciation note for amount is higher than invoice.'))

                if not self.env.user.company_id.x_dep_default_prd:
                    raise UserError(_(
                        'Please define depreciation product in the company.'))
                refund = rec._get_depreciation_refund(inv,rec.analytic_account_id.id)
                created_inv.append(refund.id)
                # for ref_line in refund.invoice_line_ids:
                #     ref_line.account_id = rec.depreciation_account_id.id
                #     ref_line.account_analytic_id = rec.analytic_account_id.id
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
                    tmpline.write({
                                  'x_reason_dep': inv.x_reason_dep and inv.x_reason_dep.id,
                                  'x_comment_dep': inv.x_comment_dep,
                                  'x_user_dep': inv.x_user_dep,
                                  'x_amount_dep': inv.x_amount_dep,
                                  'is_depreciate_line': True,
                                      })
                    if tmpline.account_id.id == inv.account_id.id:
                        to_reconcile_lines += tmpline
                to_reconcile_lines.filtered(
                    lambda l: l.reconciled == False).reconcile()
                res_justthis_vals = {
                    "x_jt_crt_uname": inv.x_jt_crt_uname,
                    "x_jt_crt_uid": inv.x_jt_crt_uid,
                    "x_jt_upd_uname": inv.x_jt_upd_uname,
                    "x_jt_upd_uid": inv.x_jt_upd_uid,
                    "x_acc_template_id": inv.x_acc_template_id,
                    "x_acc_upd_template_id": inv.x_acc_upd_template_id,
                    "x_jt_activity_id": inv.x_jt_activity_id,
                    "x_jt_main1_id": inv.x_jt_main1_id,
                    "x_jt_main2_id": inv.x_jt_main2_id,
                    "x_orig_isr_number": inv.x_orig_isr_number,

                }
                refund.write(res_justthis_vals)
                x_jt_dep_status = "dep"
                if inv.x_amount_dep < inv.amount_total:
                    x_jt_dep_status = "dep_part"
                refund.x_jt_dep_status = x_jt_dep_status
                inv.x_jt_dep_status = x_jt_dep_status
                if refund.move_id:
                    refund.move_id.write(res_justthis_vals)
                result = self.env.ref('account.action_invoice_out_refund').read()[0]
                invoice_domain = safe_eval(result['domain'])
                invoice_domain.append(('id', 'in', created_inv))
                result['domain'] = invoice_domain
                inv.invoice_line_ids.write({'is_depreciation': True})
                return result