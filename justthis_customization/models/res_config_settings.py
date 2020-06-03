# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_ch_qr_code = fields.Boolean(string='Print QR Code',
                                     related="company_id.l10n_ch_qr_code", readonly=False)
