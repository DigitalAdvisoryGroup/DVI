# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields
import base64
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def get_partner_ledger_report(self, from_date=False, from_to=False):
        if self and from_date and from_to:
            partner_ledger_vals = {
                "partner_id": self.id,
                "date_from": from_date,
                "date_to": from_to
            }
            partner_ledger_id = self.env['account.financial.report.pdf'].create(partner_ledger_vals)
            res = partner_ledger_id.check_report()
            pdf = self.env.ref('justthis_customization.action_report_partnerledger_pdf').sudo().render_qweb_pdf(
                [partner_ledger_id],data=res.get("data"))
            b64_pdf = base64.b64encode(pdf[0])
            report_name = self.env.ref(
                'justthis_customization.action_report_partnerledger_pdf').report_action(
                self, data=res.get("data"))
            return {"status": True, 'base64_content': b64_pdf,'report_name': report_name.get('name')}
        return {'status': False,
                "msg": "Partner,Fromdate,Todate is required."}
