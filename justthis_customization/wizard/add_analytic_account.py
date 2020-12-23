# -*- coding: utf-8 -*-

from odoo import api, models, fields

class AnalyticAccountUpdate(models.TransientModel):
    _name = "update.analytic.account"
    _description = "Update Analytic Account"

    analytic_account_id = fields.Many2one("account.analytic.account", "Analytic Account")


    @api.multi
    def update_analytic_account(self):
        for rec in self:
            for aml in self.env[self.env.context['active_model']].browse(self.env.context['active_ids']):
                move_id = aml.move_id
                move_id.button_cancel()
                aml.analytic_account_id = rec.analytic_account_id.id
                move_id.action_post()
