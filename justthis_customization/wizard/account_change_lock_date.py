from odoo import models, fields, api


class AccountChangeLockDate(models.TransientModel):
    _inherit = 'account.change.lock.date'

    current_period_lock_date = fields.Date(string='Current Lock Date for Non-Advisers',
        default=lambda self: self.env.user.company_id.period_lock_date)
    current_fiscalyear_lock_date = fields.Date(
        string='Current Lock Date for All Users',
        default=lambda self: self.env.user.company_id.fiscalyear_lock_date)
