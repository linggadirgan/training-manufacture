from odoo import _, api, fields, models

class ProductCategory(models.Model):
    _inherit = 'product.category'

    employee_cost_account_id = fields.Many2one('account.account', string='Employee Cost', company_dependent=True,
        domain="[('deprecated', '=', False)]", check_company=True)
    overhead_cost_account_id = fields.Many2one('account.account', string='Overhead Cost', company_dependent=True,
        domain="[('deprecated', '=', False)]", check_company=True)
    energy_cost_account_id = fields.Many2one('account.account', string='Energy Cost', company_dependent=True,
        domain="[('deprecated', '=', False)]", check_company=True)