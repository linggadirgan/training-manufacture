from odoo import _, api, fields, models

class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    overhead_cost_ids = fields.One2many('mrp.costing.overhead', 'bom_id', string='Direct Overhead Cost')