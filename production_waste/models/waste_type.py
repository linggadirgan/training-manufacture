from odoo import _, api, fields, models

class WasteType(models.Model):
    _name = 'waste.type'
    _description = 'Waste Type'

    name = fields.Char(string="Waste Type", required=True)
    description = fields.Text(string="Description")
