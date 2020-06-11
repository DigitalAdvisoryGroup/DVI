# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.

from odoo import models, api


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
