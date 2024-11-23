from odoo import _, api, fields, models

class WasteMitigation(models.Model):
    _name = 'waste.mitigation'
    _description = 'Waste Mitigation Method'

    name = fields.Char(string="Mitigation Method", required=True)
    description = fields.Text(string="Description")
