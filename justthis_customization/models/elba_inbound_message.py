# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields, _
from odoo.exceptions import UserError


class InboundElbaMsg(models.Model):
    _name = 'inbound_elba_msg'


    x_acc_template_id = fields.Char(string="Accounting Events Template")
    x_account_credit_id = fields.Many2one('account.account',string="Credit account")
    x_account_debit_id = fields.Many2one('account.account',string="Debit account")
    x_belnr = fields.Char(string="ELBA voucher")
    x_belnr_id = fields.Many2one('account.move',string="Journal ref id")
    x_blart = fields.Char(string="ELBA voucher type")
    x_budat = fields.Char(string="ELBA booking date")
    x_comment = fields.Char(string="Comment")
    x_cpudt = fields.Char(string="Update ELBA record date")
    x_cputm = fields.Char(string="Update ELBA record time")
    x_dmbtr = fields.Float(string="Amount")
    x_elba_inbound_lines = fields.Many2many('inbound_elba_msg',string="Debit line item",compute="compute_x_elba_inbound_lines")
    x_elba_msg_timestamp = fields.Datetime(string="ELBA webservice msg timestamp")
    x_elba_transfer_session_date = fields.Datetime(string="ELBA webservice session timestamp")
    x_elba_transfer_session_id = fields.Char(string="ELBA webservice session id")
    x_hkont = fields.Char(string="ELBA GL account")
    x_journal_id = fields.Many2one('account.journal',string="Journal")
    x_move_id = fields.Many2one('account.move',string="Journal entry id", compute="_get_move_name", store=True)
    x_name = fields.Char(string="Booking number")
    x_reason_nok = fields.Char(string="Reason for not posting")
    x_sgtxt = fields.Char(string="Posting text")
    x_shkzg = fields.Char(string="Debit / Credit flag (S/H)")
    x_stblg = fields.Char(string="Reversal voucher")
    x_xblnr = fields.Char(string="ELBA reference")
    x_zz_jt_refn = fields.Char(string="ELBA JustThis reference")
    x_zz_jt_ukon = fields.Char(string="Justthis sub account")
    x_zz_zuweis = fields.Char(string="ELBA assignment")

    @api.depends("x_name")
    def _get_move_name(self):
        for record in self:
            move_id = self.env['account.move'].search([('name', '=', record['x_name'])], limit=1)
            record['x_move_id'] = move_id and move_id.id or False

    def compute_x_elba_inbound_lines(self):
        for record in self: 
            if record['x_shkzg'] == 'H':
                record['x_elba_inbound_lines'] = self.env['inbound_elba_msg'].search([('x_belnr','=',record['x_belnr']),('x_shkzg','=','S')]).ids

    @api.onchange("x_zz_jt_refn")
    def onchange_x_zz_jt_refn(self):
        if self.x_zz_jt_refn and self.x_elba_inbound_lines:
            self.x_elba_inbound_lines.write({"x_zz_jt_refn":self.x_zz_jt_refn})



    def create_je_elba_message(self):
        for rec in self:
            if rec.x_shkzg == "S" or rec.x_move_id:
                raise UserError(_('You can not create Journal Entry for Debit lines or Has already Booking number'))
            aml_lines = [(0,0,{'account_id':rec.x_account_credit_id.id,
                               'credit':rec.x_dmbtr,
                               'x_blart': rec.x_blart,
                               'x_belnr': rec.x_belnr,
                               'x_budat': rec.x_budat,
                               'x_sgtxt': rec.x_sgtxt,
                               'x_hkont': rec.x_hkont,
                               'x_zz_jt_ukon': rec.x_zz_jt_ukon,
                               'x_zz_jt_refn': rec.x_zz_jt_refn,
                               'x_zz_zuweis': rec.x_zz_zuweis,
                               'x_xblnr': rec.x_xblnr,
                               'x_stblg': rec.x_stblg
                               })]
            if rec.x_shkzg == "H":
                for line in rec.x_elba_inbound_lines:
                    aml_lines.append((0,0,{'account_id':line.x_account_debit_id.id,
                                           'debit':line.x_dmbtr,
                                           'x_blart': line.x_blart,
                                           'x_belnr': line.x_belnr,
                                           'x_budat': line.x_budat,
                                           'x_sgtxt': line.x_sgtxt,
                                           'x_hkont': line.x_hkont,
                                           'x_zz_jt_ukon': line.x_zz_jt_ukon,
                                           'x_zz_jt_refn': line.x_zz_jt_refn,
                                           'x_zz_zuweis': line.x_zz_zuweis,
                                           'x_xblnr': line.x_xblnr,
                                           'x_stblg': line.x_stblg
                                           }))
            move_id = self.env['account.move'].create({'journal_id':rec.x_journal_id.id,'ref':rec.x_belnr,'line_ids':aml_lines})
            if move_id:
                move_id.action_post()
                rec.x_name = move_id.name
                rec.x_elba_inbound_lines.write({"x_name":move_id.name})


            

class InboundIsrMsg(models.Model):
    _name = "inbound_isr_msg"

    def set_invoice(self,x_invoice_id):
        self.write({'x_invoice_id':x_invoice_id})
        if self.x_invoice_id:
            self.x_payment_id.cancel()
            self.x_payment_id.action_draft()
            self.x_payment_id.write({'partner_id':self.x_invoice_id.partner_id.id})
            self.x_payment_id.post()
            for line in self.x_payment_id.move_line_ids:
                if line.account_id.id == self.x_invoice_id.account_id.id:
                    self.x_invoice_id.assign_outstanding_credit(line.id)
        else:
            raise UserError(_("Please set invoice record."))









