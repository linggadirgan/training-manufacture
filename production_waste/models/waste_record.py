from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from datetime import datetime

STATUS = [
        ('draft', 'Planned'),
        ('in_progress', 'In Progress'),
        ('done', 'Completed'),
        ('cancel', 'Cancelled'),
    ]

class WasteRecord(models.Model):
    _name = 'waste.record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Production Waste Record'
    _order = 'name desc, id desc'

    name = fields.Char(string='Reference', copy=False, index=True, tracking=True,
                       default=(_('New')))
    production_id = fields.Many2one('mrp.production', string='Production Order', required=True, tracking=True)
    date_planned = fields.Datetime('Date Planned', required=True, index=True, tracking=True, default=datetime.now())
    date_deadline = fields.Datetime('Date Deadline', required=True, index=True, tracking=True)
    user_id = fields.Many2one('res.users', string='Responsible', required=True, tracking=True, default=lambda self:self.env.uid)
    waste_type_id = fields.Many2one('waste.type', string='Waste Type', required=True, tracking=True)
    waste_component_ids = fields.One2many(comodel_name='waste.component', inverse_name='waste_id', string='Waste Components', tracking=True)
    mitigation_ids = fields.Many2many(
        comodel_name='waste.mitigation', 
        relation='record_mitigation_rel', 
        column1='waste_id', 
        column2='mitigation_id',
        string='Mitigation Methods',
        tracking=True)
    total_quantity = fields.Float(string='Total Quantity', compute='_compute_total_quantity', store=True)
    state = fields.Selection(STATUS, string='Status', default=STATUS[0][0], required=True, copy=False, index=True, tracking=True)

    @api.depends('waste_component_ids.quantity')
    def _compute_total_quantity(self):
        for rec in self:
            rec.total_quantity = sum(rec.waste_component_ids.mapped('quantity'))

    def _sequence_number(self):
        if self.name in (False, '/', _('New')):
            self.name = self.env['ir.sequence'].next_by_code('waste.record')
    
    def _validation_component(self):
        if not self.waste_component_ids:
            raise ValidationError(_('Component detail cannot empty!'))

    def action_confirm(self):
        self._validation_component()
        self._sequence_number()
        self.state = 'in_progress'
    
    def action_draft(self):
        self.state = 'draft'
    
    def action_cancel(self):
        self.state = 'cancel'

    def action_done(self):
        self.state = 'done'

    @api.model
    def auto_done(self):
        records_to_update = self.search([
            ('state', '=', 'in_progress'), 
            ('date_deadline', '<=', fields.Datetime.now())
        ])

        for record in records_to_update:
            record.write({'state': 'done'})
            message = 'Auto Done by System Scheduler'
            record.message_post(body=message)

    @api.model
    def waste_record_list(self, params):
        values = []
        limit = params.get('limit', 0)
        offset = params.get('offset', 0)
        waste_type_id = params.get('waste_type_id', 0)
        user_id = params.get('user_id', 0)
        production_id = params.get('production_id', 0)
        name = params.get('name', '')

        domain = []

        if name:
            domain += [('name','ilike',name)]
        if production_id:
            domain += [('production_id','=',production_id)]
        if waste_type_id:
            domain += [('waste_type_id','=',waste_type_id)]
        if user_id:
            domain += [('user_id','=',user_id)]

        records = self.search(domain, limit=limit, offset=offset)
        records_count = self.search_count(domain)

        for rec in records:
            values.append({
                'id': rec.id,
                'name': rec.name,
                'date_planned': rec.date_planned,
                'date_deadline': rec.date_deadline,
                'user_id': rec.user_id.id,
                'waste_type_id': rec.waste_type_id.id,
                'mitigation_ids': [
                    {
                        'id': x.id,
                        'name': x.name,
                    } for x in rec.mitigation_ids
                ],
                'state': rec.state
            })

        return {
            'total_data': records_count,
            'current_total_data': len(records) + offset,
            'record_more': False if (len(records) + offset) >= records_count else True,
            'current_page': offset + 1,
            'data': values
        }

class WasteComponent(models.Model):
    _name = 'waste.component'
    _description = 'Waste Component'

    waste_id = fields.Many2one('waste.record', string='Waste Record', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    name = fields.Char(string='Description', required=True)
    quantity = fields.Float(string='Quantity', required=True)
    uom_id = fields.Many2one('uom.uom', string='UoM', required=True)

    @api.onchange('product_id')
    def onchange_product(self):
        self.uom_id = self.product_id.uom_id.id
        self.name = self.product_id.display_name