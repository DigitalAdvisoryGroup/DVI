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
            year = datetime.strptime(from_date, DEFAULT_SERVER_DATE_FORMAT)
            report_obj = self.env['account.partner.ledger']
            options = {'account_type': [
                {'id': 'receivable', 'name': 'Receivable', 'selected': False},
                {'id': 'payable', 'name': 'Payable', 'selected': False}],
                       'all_entries': False, 'analytic': None,
                       'cash_basis': False, 'comparison': None,
                       'date': {'date_from': from_date, 'date_to': from_to,
                                'filter': 'this_year',
                                'string': '%s' % year.year}, 'hierarchy': None,
                       'journals': None, 'partner': True,
                       'partner_categories': [], 'partner_ids': [self.id],
                       'unfold_all': False, 'unreconciled': False,
                       'unfolded_lines': ['partner_%s' % self.id],
                       'selected_partner_ids': [self.name],
                       'selected_partner_categories': [],
                       'unposted_in_period': True}
            report_name = report_obj.get_report_filename(options)
            response = report_obj.get_pdf(options)
            pdf = base64.b64encode(response)
            return {"status": True, 'base64_content': pdf,'report_name': report_name}
        return {'status': False,
                "msg": "Partner,Fromdate,Todate is required."}
