from odoo import _, api, fields, models

class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    overhead_costs_hour = fields.Monetary(string='Overhead Hourly Cost', currency_field='currency_id', default=0.0)