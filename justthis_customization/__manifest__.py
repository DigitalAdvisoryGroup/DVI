# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.

{
    'name': "JustThis - business processing for Swiss public prosecutor",
    'version': '1.0',
    'summary': """
        Odoo customizations for JustThis project requirements (http://www.xplain.ch/wp/produkte/justthis/)
    """,
    'description': """

JustThis - Business processing for Swiss public prosecutor
==========================================================
Swiss localization

Description
-----------
    This module supports specific JustThis requirements
    - Swiss QR ISR
    - Financial Closure management 
    - Financial Closure export to SAP ledger
    - 4-eyes-check depreciation handling

    """,

    'author': "Digital Advisory Group GmbH, Candidroot Solutions Pvt. Ltd.",
    'website': "https://www.digitaladvisorygroup.io/",
    'category': 'Localization',
    'depends': ['l10n_ch_reports','account_reports','account_cancel','base'],
    'data': [
            "security/ir.model.access.csv",
            "views/asset_templates.xml",
            "views/res_config_settings_views.xml",
            "report/swissqr_report.xml",
            "views/report_menu_view.xml",
            "views/account_reports_configure_view.xml",
            "views/report_financial.xml",
            "views/invoice_depreciation_wizard_view.xml",
            "views/invoice_reversal_wizard_view.xml",
            "views/add_analytic_account_view.xml",
            "views/elba_inbound_message.xml",
            "wizard/account_report_wizard_view.xml",
            "report/report_partnerledger_pdf.xml",
            "views/account_journal_dashboard.xml"
    ],
    'demo': [
    ],
    'qweb': [
        'static/src/xml/payment.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'post_init_hook': '_set_journals_cancel',
}
