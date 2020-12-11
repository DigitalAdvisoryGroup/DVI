# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.


import json

from odoo import http
from odoo.addons.web.controllers.main import _serialize_exception
from odoo.http import content_disposition, request
from odoo.tools import html_escape


class FinancialReportController(http.Controller):

    @http.route('/custom/account_reports', type='http', auth='user', methods=['POST'], csrf=False)
    def get_custom_report(self, model, options, output_format, token, json_data, financial_id=None, **kw):
        uid = request.session.uid
        json_data = json.loads(json_data)
        report_obj = request.env[model].sudo(uid)
        options = json.loads(options)
        if financial_id and financial_id != 'null':
            report_obj = report_obj.browse(int(financial_id))
        report_name = report_obj.get_report_filename(options)
        try:
            if output_format == 'xlsx':
                response = request.make_response(
                    None,
                    headers=[
                        ('Content-Type', 'application/vnd.ms-excel'),
                        ('Content-Disposition', content_disposition(report_name + '.xlsx'))
                    ]
                )
                report_obj.get_custome_xlsx(options, response, json_data)
            if output_format == 'pdf':
                response = request.make_response(
                    report_obj.get_pdf(options),
                    headers=[
                        ('Content-Type', 'application/pdf'),
                        ('Content-Disposition', content_disposition(report_name + '.pdf'))
                    ]
                )
            if output_format == 'sap':
                content = report_obj.get_sap_txt(options, json_data)
                end_date = options.get("date").get("date_to").replace("-","")
                report_name = request.env.user.company_id.x_sap_export_file+end_date
                response = request.make_response(
                    content,
                    headers=[
                        ('Content-Type', 'text/plain'),
                        ('Content-Disposition', content_disposition(report_name + '.data')),
                        ('Content-Length', len(content))
                    ]
                )
            response.set_cookie('fileToken', token)
            return response
        except Exception as e:
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': 'Odoo Server Error',
                'data': se
            }
            return request.make_response(html_escape(json.dumps(error)))
