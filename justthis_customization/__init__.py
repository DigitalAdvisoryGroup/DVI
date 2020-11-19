# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard
from . import report

from odoo import api, SUPERUSER_ID


def _set_journals_cancel(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    journals = env['account.journal'].search([])
    if journals:
        journals.write({'update_posted': True})