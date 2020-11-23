# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields, _
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang
import json


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    def add_open_invoice_lines(self, product_id=False):
        self.ensure_one()
        if product_id and self and self.state in ("open", "paid"):
            payment_ids = []
            payment_vals = json.loads(self.payments_widget) and json.loads(
                self.payments_widget).get("content") or False
            if payment_vals:
                for payment in payment_vals:
                    payment_ids.append(payment.get('account_payment_id'))
            self.action_invoice_cancel()
            self.action_invoice_draft()
            self.refresh()
            product_id = self.env["product.product"].browse(int(product_id))
            if product_id:
                line_values = {
                    'product_id': product_id.id,
                    'price_unit': product_id.lst_price,
                    'invoice_id': self.id,
                }
                invoice_line = self.env['account.invoice.line'].new(
                    line_values)
                invoice_line._onchange_product_id()
                line_values = invoice_line._convert_to_write(
                    {name: invoice_line[name] for name in invoice_line._cache})
                line_values['price_unit'] = product_id.lst_price
                self.env['account.invoice.line'].create(line_values)
            self.action_invoice_open()
            if payment_ids:
                payments = self.env['account.payment'].browse(payment_ids)
                move_lines = payments.mapped('move_line_ids').filtered(
                    lambda line: not line.reconciled and line.credit > 0.0)
                for line in move_lines:
                    self.assign_outstanding_credit(line.id)
            return {"invoice_id" : self.id}


    def set_open_invoice_due_date(self, date=False):
        if date and self and self.state in ("open","paid"):
            payment_ids = []
            payment_vals = json.loads(self.payments_widget) and json.loads(self.payments_widget).get("content") or False
            if payment_vals:
                for payment in payment_vals:
                    payment_ids.append(payment.get('account_payment_id'))
            self.action_invoice_cancel()
            self.action_invoice_draft()
            self.date_due = date
            self.action_invoice_open()
            if payment_ids:
                payments = self.env['account.payment'].browse(payment_ids)
                move_lines = payments.mapped('move_line_ids').filtered(
                    lambda line: not line.reconciled and line.credit > 0.0)
                for line in move_lines:
                    self.assign_outstanding_credit(line.id)
            return {"invoice_id" : self.id}
        return False



    def display_swiss_qr_code(self):
        self.ensure_one()
        qr_parameter = self.env['ir.config_parameter'].sudo().get_param('justthis_customization.print_qr_code')
        return self.partner_id.country_id.code == 'CH' and qr_parameter

    @api.multi
    def open_depreciation_wizard(self):
        for inv in self:
            if self.env.user.name == inv.x_user_dep:
                raise UserError(_('You can not depreciation your own invoice'))
            action = self.env.ref('justthis_customization.action_account_invoice_depreciation').read()[0]
            return action

    @api.multi
    def open_reversal_wizard(self):
        for inv in self:
            if self.env.user.name == inv.x_user_rev:
                raise UserError(_('You can not reversal your own invoice'))
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
                        line['text_name'] = payment.is_reversal_line and _("Reverted on: ") or payment.is_depreciate_line and _("Depreciated on: ") or _("Paid on: ")
        return res

    @api.multi
    def invoice_validate(self):
        res = super(AccountInvoice, self).invoice_validate()
        for inv in self:
            if inv.move_id and inv.move_id.line_ids:
                invoice_dict = {
                    'x_jt_crt_uname': inv.x_jt_crt_uname,
                    'x_jt_crt_uid': inv.x_jt_crt_uid,
                    'x_jt_upd_uname': inv.x_jt_upd_uname,
                    'x_jt_upd_uid': inv.x_jt_upd_uid,
                    'x_acc_template_id': inv.x_acc_template_id,
                    'x_acc_upd_template_id': inv.x_acc_upd_template_id,
                    'x_jt_activity_id': inv.x_jt_activity_id,
                    'x_jt_main1_id': inv.x_jt_main1_id,
                    'x_jt_main2_id': inv.x_jt_main2_id,
                    'x_jt_deposit_id': inv.x_jt_deposit_id,
                    'x_reason_rev': inv.x_reason_rev.id,
                    'x_comment_rev': inv.x_comment_rev,
                    'x_user_rev': inv.x_user_rev,
                    'x_reason_dep': inv.x_reason_dep.id,
                    'x_amount_dep': inv.x_amount_dep,
                    'x_comment_dep': inv.x_comment_dep,
                    'x_user_dep': inv.x_user_dep,
                }
                inv.move_id.write(invoice_dict)
                inv.move_id.line_ids.write(invoice_dict)
        return res

    @api.multi
    @api.returns('self')
    def refund_dep(self, date_invoice=None, date=None, description=None,
               journal_id=None, dep_product_id=False,dep_amount=0.0,account_analytic_id=False):
        new_invoices = self.browse()
        for invoice in self:
            # create the new invoice
            values = self._prepare_refund(invoice, date_invoice=date_invoice,
                                          date=date,
                                          description=description,
                                          journal_id=journal_id)
            values['invoice_line_ids'] = [(0,0,{'name': dep_product_id.name,'product_id': dep_product_id.id,
                                                'account_id': self.env.user.company_id.x_dep_default_account.id,
                                                'quantity': 1.0,
                                                'price_unit': dep_amount,'account_analytic_id': account_analytic_id})]
            refund_invoice = self.create(values)
            if invoice.type == 'out_invoice':
                message = _(
                    "This customer invoice depreciation note has been created from: <a href=# data-oe-model=account.invoice data-oe-id=%d>%s</a><br>Reason: %s") % (
                          invoice.id, invoice.number, description)
            refund_invoice.message_post(body=message)
            new_invoices += refund_invoice
        return new_invoices


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    is_reversal = fields.Boolean("Is Reversal")
    is_depreciation = fields.Boolean("Is Depreciation")



class account_journal(models.Model):
    _inherit = "account.journal"

    is_isr_journal = fields.Boolean("Is ISR Journal?")
    update_posted = fields.Boolean(string='Allow Cancelling Entries',default=True,
                                   help="Check this box if you want to allow the cancellation the entries related to this journal or of the invoice related to this journal")

    
    @api.multi
    def get_journal_dashboard_datas(self):
        reversal_count = self.env['account.invoice'].search([('type','=','out_invoice'),('x_reason_rev','!=',False),('invoice_line_ids.is_reversal','=',False),('state','!=','cancel')])
        depreciation_count = self.env['account.invoice'].search([('type','=','out_invoice'),('x_reason_dep','!=',False),('invoice_line_ids.is_depreciation','=',False),('state','!=','cancel')])
        reversed_invoice_count = self.env['account.invoice'].search([('type','=','out_invoice'),('invoice_line_ids.is_reversal','=',True),('state','!=','cancel')])
        fully_invoice_count = self.env['account.invoice'].search([('type','=','out_invoice'),('invoice_line_ids.is_depreciation','=',True),('residual','<',1),('state','!=','cancel')])
        partial_invoice_count = self.env['account.invoice'].search([('type','=','out_invoice'),('invoice_line_ids.is_depreciation','=',True),('residual','>',0.0),('state','!=','cancel')])
        isr_record_count = self.env['inbound_isr_msg'].search([('x_invoice_id','=',False)])
        currency = self.currency_id or self.company_id.currency_id
        reversal_count_sum = formatLang(self.env, currency.round(sum(reversal_count.mapped('amount_total'))) + 0.0, currency_obj=currency)
        depreciation_count_sum = formatLang(self.env, currency.round(sum(depreciation_count.mapped('amount_total'))) + 0.0, currency_obj=currency)
        reversed_invoice_count_sum = formatLang(self.env, currency.round(sum(reversed_invoice_count.mapped('amount_total'))) + 0.0, currency_obj=currency) 
        fully_invoice_count_sum = formatLang(self.env, currency.round(sum(fully_invoice_count.mapped('amount_total'))) + 0.0, currency_obj=currency) 
        partial_invoice_count_sum = formatLang(self.env, currency.round(sum(partial_invoice_count.mapped('amount_total'))) + 0.0, currency_obj=currency) 
        data = dict(
            super(account_journal, self).get_journal_dashboard_datas(),
            reversal_count=len(reversal_count),
            depreciation_count=len(depreciation_count),
            reversed_invoice_count=len(reversed_invoice_count),
            fully_invoice_count=len(fully_invoice_count),
            partial_invoice_count=len(partial_invoice_count),
            isr_record_count=len(isr_record_count),
            reversal_count_sum=reversal_count_sum,
            depreciation_count_sum=depreciation_count_sum,
            reversed_invoice_count_sum=reversed_invoice_count_sum,
            fully_invoice_count_sum=fully_invoice_count_sum,
            partial_invoice_count_sum=partial_invoice_count_sum,

        )
        return data


    @api.multi
    def open_action_justthis(self):
        """return action based on type for related appointment states"""
        action_name = self._context.get('action_name', False)
        ctx = self._context.copy()
        ctx.update({})
        [action] = self.env.ref(action_name).read()
        action['context'] = ctx
        action_type = self._context.get('action_type')
        if action_type == 'reversal':
            action['domain'] = [('type','=','out_invoice'),('x_reason_rev','!=',False),('invoice_line_ids.is_reversal','=',False),('state','!=','cancel')]
        elif action_type == 'depreciation':
            action['domain'] = [('type','=','out_invoice'),('x_reason_dep','!=',False),('invoice_line_ids.is_depreciation','=',False),('state','!=','cancel')]
        elif action_type == 'reversed_invoice':
            action['domain'] = [('invoice_line_ids.is_reversal','=',True),('state','!=','cancel')]
        elif action_type == 'full_depreciation':
            action['domain'] = [('invoice_line_ids.is_depreciation','=',True),('residual','<',1),('state','!=','cancel')]
        elif action_type == 'partial_depreciation':
            action['domain'] = [('invoice_line_ids.is_depreciation','=',True),('residual','>',0.0),('state','!=','cancel')]
        elif action_type == 'isr_invoice':
            action['domain'] = [('x_invoice_id','=',False)]

        return action


class AccountPayment(models.Model):
    _inherit = 'account.payment'


    def post(self):
        res = super(AccountPayment,self).post()
        move_data = {
            'x_jt_crt_uname':self.x_jt_crt_uname,
            'x_jt_crt_uid':self.x_jt_crt_uid,
            'x_jt_upd_uname':self.x_jt_upd_uname,
            'x_jt_upd_uid':self.x_jt_upd_uid,
            'x_acc_template_id':self.x_acc_template_id,
            'x_acc_upd_template_id':self.x_acc_upd_template_id,
            'x_jt_activity_id':self.x_jt_activity_id,
            'x_jt_main1_id':self.x_jt_main1_id,
            'x_jt_main2_id':self.x_jt_main2_id,
            'x_jt_deposit_id':self.x_jt_deposit_id,
        }
        for move in self.move_line_ids:
            move.write(move_data)
        return res
