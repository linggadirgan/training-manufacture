from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description):
        res = super(StockMove, self)._generate_valuation_lines_data(partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description)
        if not self._is_production():
            return res
        currency = self.company_id.currency_id
        
        base_vals = {
            'name': description,
            'ref': description,
            'partner_id': partner_id,
        }
        if not currency.is_zero(self.workorder_id._cal_cost()): # check jika nilainya 0, skip
            res['credit_line_vals']['balance'] += self.workorder_id._cal_cost()
            
            accounts_data = self.product_id.product_tmpl_id.get_product_accounts()
            if not accounts_data['employee'] or not accounts_data['energy'] or not accounts_data['overhead']:
                raise ValidationError(_('Please check Production, Overhead, Employee, and Energy account on product category configuration!'))
            
            employee_cost_account_id = accounts_data['employee']
            employee_cost = sum(self.workorder_id.time_ids.mapped('total_cost'))
            res['employee_credit_line'] = {
                **base_vals,
                'balance': -employee_cost,
                'account_id': employee_cost_account_id.id,
            }

            energy_cost_account_id = accounts_data['energy']
            energy_cost = (sum(self.workorder_id.time_ids.mapped('duration')) / 60.0) * self.workorder_id.workcenter_id.costs_hour
            res['energy_credit_line'] = {
                **base_vals,
                'balance': -energy_cost,
                'account_id': energy_cost_account_id.id,
            }

            overhead_cost_account_id = accounts_data['overhead']
            overhead_cost = sum(self.production_id.overhead_cost_ids.mapped('total_actual_cost'))
            res['overhead_credit_line'] = {
                **base_vals,
                'balance': -overhead_cost,
                'account_id': overhead_cost_account_id.id,
            }

        return res