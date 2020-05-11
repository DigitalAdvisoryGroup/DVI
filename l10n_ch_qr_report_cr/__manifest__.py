# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.

{
    'name': "Switzerland - Accounting With QR Report",
    'version': '1.0',
    'summary': """
        Swiss localization with QR Code Report
    """,
    'description': """

Swiss localization
==================
Swiss localization

Description
-----------
    - This module will allow user to print QR code payment report.

    """,

    'author': "Candidroot Solutions Pvt. Ltd.",
    'website': "https://candidroot.com/",
    'category': 'Localization',
    'depends': ['l10n_ch_reports'],
    'data': [
            "security/ir.model.access.csv",
            "views/res_config_settings_views.xml",
            "report/swissqr_report.xml",
            "views/report_menu_view.xml",
            "views/account_reports_configure_view.xml",
            "views/report_financial.xml",
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False
}
