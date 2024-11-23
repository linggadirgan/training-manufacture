from odoo import _, api, fields, models

class MrpCosting(models.AbstractModel):
    _name = 'mrp.costing'
    _description = 'MRP Costing'

    production_id = fields.Many2one('mrp.production', string='Manufacturing Order', index=True, copy=False)
    bom_id = fields.Many2one('mrp.bom', string='Bill of Material', index=True, copy=False)
    operation_id = fields.Many2one('mrp.routing.workcenter', string='Operation', index=True, copy=False)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self:self.env.company.currency_id)
    planned_hour = fields.Float('Planned Hours')
    actual_hour = fields.Float('Actual Hours')
    cost = fields.Monetary('Cost per Hour')
    total_cost = fields.Monetary('Total Cost', compute='_total_cost')
    total_actual_cost = fields.Monetary('Total Actual Cost', compute='_total_actual_cost')

    @api.depends('planned_hour','cost')
    def _total_cost(self):
        for rec in self:
            rec.total_cost = rec.planned_hour * rec.cost

    @api.depends('actual_hour','cost')
    def _total_actual_cost(self):
        for rec in self:
            rec.total_actual_cost = rec.actual_hour * rec.cost

class MrpCostingOverhead(models.Model):
    _name = 'mrp.costing.overhead'
    _inherit = 'mrp.costing'
    _description = 'MRP Costing Overhead'
