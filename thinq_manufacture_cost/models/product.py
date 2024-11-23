from odoo import _, api, fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_product_accounts(self):
        accounts = super()._get_product_accounts()
        accounts.update({
            'overhead': self.categ_id.overhead_cost_account_id,
            'employee': self.categ_id.employee_cost_account_id,
            'energy': self.categ_id.energy_cost_account_id,
        })
        return accounts