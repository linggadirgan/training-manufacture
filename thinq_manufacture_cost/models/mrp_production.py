from odoo import _, api, fields, models

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    overhead_cost_ids = fields.One2many('mrp.costing.overhead', 'production_id', string='Direct Overhead Cost')

    @api.onchange('bom_id','product_id')
    def _get_cost_from_bom(self):
        for rec in self:
            bom_overhead_cost = []
            for cost in rec.bom_id.overhead_cost_ids:
                bom_overhead_cost.append((0,0,{
                    'operation_id': cost.operation_id.id,
                    'planned_hour': cost.planned_hour,
                    'cost': cost.cost
                }))
            rec.overhead_cost_ids = [(6,0,[])]
            rec.overhead_cost_ids = bom_overhead_cost