# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields, _


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
    x_move_id = fields.Many2one('account.move',string="Journal entry id")
    x_name = fields.Char(string="Booking number")
    x_reason_nok = fields.Char(string="Reason for not posting")
    x_sgtxt = fields.Char(string="Posting text")
    x_shkzg = fields.Char(string="Debit / Credit flag (S/H)")
    x_stblg = fields.Char(string="Reversal voucher")
    x_xblnr = fields.Char(string="ELBA reference")
    x_zz_jt_refn = fields.Char(string="ELBA JustThis reference")
    x_zz_jt_ukon = fields.Char(string="Justthis sub account")
    x_zz_zuweis = fields.Char(string="ELBA assignment")

    def compute_x_elba_inbound_lines(self):
        for record in self: 
            if record['x_shkzg'] == 'H':
                record['x_elba_inbound_lines'] = self.env['x_inbound_elba'].search([('x_belnr','=',record['x_belnr']),('x_shkzg','=','S')]).ids

    def create_je_elba_message(self):
        for rec in self:
            aml_lines = [(0,0,{'account_id':rec.x_account_credit_id.id,'credit':rec.x_dmbtr})]
            if rec.x_shkzg == "H":
                for line in rec.x_elba_inbound_lines:
                    account_id = rec.x_account_credit_id.id
                    if line.x_shkzg == 'H':
                        account_id = line.x_account_credit_id.id
                    else:
                        account_id = line.x_account_debit_id.id
                    line_data = {'account_id':account_id}
                    if line.x_shkzg == "H":
                        line_data.update({'credit':line.x_dmbtr})
                    else:
                        line_data.update({'debit':line.x_dmbtr})
                    aml_lines.append((0,0,line_data))
            self.env['account.move'].create({'journal_id':rec.x_journal_id.id,'ref':rec.x_belnr,'line_ids':aml_lines})
            

class InboundIsrMsg(models.Model):
    _name = "inbound_isr_msg"




