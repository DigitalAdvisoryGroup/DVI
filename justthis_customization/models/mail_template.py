# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.

import base64

from odoo import api, models
from odoo.tools import pycompat


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    @api.multi
    def generate_email(self, res_ids, fields=None):
        res = super(MailTemplate, self).generate_email(res_ids, fields)
        multi_mode = True
        if isinstance(res_ids, pycompat.integer_types):
            res_ids = [res_ids]
            multi_mode = False
        res_ids_to_templates = self.get_email_template(res_ids)
        for res_id in res_ids:
            related_model = self.env[self.model_id.model].browse(res_id)
            if related_model._name == 'account.invoice' and related_model.l10n_ch_isr_valid:
                # We add an attachment containing the QR Code
                template = res_ids_to_templates[res_id]
                report_name = 'QR-Code-' + self._render_template(template.report_name, template.model, res_id) + '.pdf'

                pdf = self.env.ref('justthis_customization.l10n_ch_qr_code_report').render_qweb_pdf([res_id])[0]
                pdf = base64.b64encode(pdf)

                attachments_list = multi_mode and res[res_id].get('attachments', False) or res.get('attachments', False)
                if attachments_list:
                    attachments_list.append((report_name, pdf))
                else:
                    res[res_id]['attachments'] = [(report_name, pdf)]
        return res
