# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Company(models.Model):
    _inherit = "res.company"

    l10n_ch_qr_code = fields.Boolean(string='QR Code', compute='_compute_l10n_ch_qr_code',
                                     inverse='_set_l10n_ch_qr_code')

    def _compute_l10n_ch_qr_code(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        for company in self:
            company.l10n_ch_qr_code = bool(get_param('justthis_customization.print_qr_code', default=False))

    def _set_l10n_ch_qr_code(self):
        set_param = self.env['ir.config_parameter'].sudo().set_param
        for company in self:
            set_param("justthis_customization.print_qr_code", company.l10n_ch_qr_code)
