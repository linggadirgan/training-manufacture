from collections import defaultdict, namedtuple
from math import log10

from odoo import api, fields, models, _
from odoo.tools.date_utils import add, subtract
from odoo.tools.float_utils import float_round
from odoo.osv.expression import OR, AND
from collections import OrderedDict
from odoo.exceptions import ValidationError

class MPS(models.Model):
    _name = 'mrp.production.schedule'
    _inherit = ['mrp.production.schedule','mail.thread', 'mail.activity.mixin']
    _rec_name = 'product_id'

    name = fields.Char(compute='_compute_name', store=True)
    total_forecast_qty = fields.Float('Total Demand Forecast', compute='_calc_forecast')
    total_replenish_qty = fields.Float('Total to Replenish', compute='_calc_replenish')
    rfq_count = fields.Integer(compute='_count_rfq')
    mo_count = fields.Integer(compute='_count_mo')
    categ_id = fields.Many2one('product.category', 'Product Category', related='product_id.categ_id', store=True)
    components_count = fields.Integer(compute='_count_components')
    orderpoint_ids = fields.Many2many(
        comodel_name="stock.warehouse.orderpoint",
        relation="mps_orderpoint_rel",
        column1="mps_id",
        column2="orderpoint_id",
        string='Replenishment')
    orderpoint_count = fields.Integer(compute='_count_orderpoint')

    # def _get_procurement_extra_values(self, forecast_values):
    #     res = super(MPS, self)._get_procurement_extra_values(forecast_values)
    #     res['job_unique_id'] = self.job_unique_id.id
    #     res['uniq_no'] = self.uniq_no
    #     res['sale_line_id'] = self.sale_line_id.id
    #     res['mps_id'] = self.id
    #     return res

    @api.depends('forecast_ids')
    def _calc_forecast(self):
        for rec in self:
            rec.total_forecast_qty = sum(rec.forecast_ids.mapped('forecast_qty'))

    @api.depends('forecast_ids')
    def _calc_replenish(self):
        for rec in self:
            rec.total_replenish_qty = sum(rec.forecast_ids.mapped('replenish_qty'))

    def action_view_forecast_detail(self):
        action = {
            'name': _('Detail Product Schedule'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'mrp.product.forecast',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('production_schedule_id', '=', self.id)],
            'context': dict(search_default_group_by_date=True, default_production_schedule_id=self.id,manual_mps=True)
        }
        # if not self.forecast_ids:
        #     action = {'type': 'ir.actions.act_window_close'}
        return action
    
    def _get_rfq_domain(self, date_start=False, date_stop=False):
        """ Return a domain used to compute the incoming quantity for a given
        product/warehouse/company.

        :param date_start: start date of the forecast domain
        :param date_stop: end date of the forecast domain
        """
        domain = [
            ('order_id.picking_type_id.default_location_dest_id', 'child_of', self.mapped('warehouse_id.view_location_id').ids),
            ('product_id', 'in', self.mapped('product_id').ids),
            ('state', 'in', ('draft', 'sent', 'to approve')),
        ]
        if date_start:
            domain += [('order_id.date_planned_mps', '>=', date_start)]
        if date_stop:
            domain += [('order_id.date_planned_mps', '<=', date_stop)]
        return domain

    def action_view_rfq(self):
        rfq_domain = self._get_rfq_domain()
        purchase_order_line_ids = self.env['purchase.order.line'].search(rfq_domain)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'views': [(False, 'list'), (False, 'form')],
            'view_mode': 'list,form',
            'target': 'current',
            'name': 'Request for Quotation',
            # 'context': {'create': False, 'delete': False},
            'domain': [('id', 'in', purchase_order_line_ids.mapped('order_id').ids)],
        }
    
    @api.depends('orderpoint_ids')
    def _count_orderpoint(self):
        for rec in self:
            rec.orderpoint_count = len(rec.orderpoint_ids)
    
    def action_view_orderpoint(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.warehouse.orderpoint',
            'views': [(False, 'list'), (False, 'form')],
            'view_mode': 'list,form',
            'target': 'current',
            'name': 'Replenishment',
            # 'context': {'create': False, 'delete': False},
            'domain': [('id', 'in', self.orderpoint_ids.ids)],
        }

    @api.depends('product_id')
    def _count_rfq(self):
        for rec in self:
            rfq_domain = rec._get_rfq_domain()
            purchase_order_line_ids = rec.env['purchase.order.line'].search(rfq_domain)
            rec.rfq_count = len(list(set(purchase_order_line_ids.mapped('order_id').ids)))
    
    def _get_moves_domain(self, date_start=False, date_stop=False, type=False):
        """ Return domain for incoming or outgoing moves """
        location = type == 'incoming' and 'location_dest_id' or 'location_id'
        location_dest = type == 'incoming' and 'location_id' or 'location_dest_id'
        domain = [
            (location, 'child_of', self.mapped('warehouse_id.view_location_id').ids),
            ('product_id', 'in', self.mapped('product_id').ids),
            ('state', '!=', 'cancel'), # remove draft state
            (location + '.usage', '!=', 'inventory'),
            '|',
                (location_dest + '.usage', 'not in', ('internal', 'inventory')),
                '&',
                (location_dest + '.usage', '=', 'internal'),
                '!',
                    (location_dest, 'child_of', self.mapped('warehouse_id.view_location_id').ids),
            ('is_inventory', '=', False),
        ]
        if date_start:
            domain += [('date', '>=', date_start)]
        if date_stop:
            domain += [('date', '<=', date_stop)]
        return domain
    
    def action_view_mo(self):
        domain_moves = self._get_moves_domain(type='incoming')
        move_ids = self.env['stock.move'].search(domain_moves)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
            'views': [(False, 'list'), (False, 'form')],
            'view_mode': 'list,form',
            'target': 'current',
            'name': 'Manufacturing Orders',
            'domain': [('id', 'in', move_ids.mapped('production_id').ids)],
        }

    @api.depends('product_id')
    def _count_mo(self):
        for rec in self:
            domain_moves = rec._get_moves_domain(type='incoming')
            move_ids = rec.env['stock.move'].search(domain_moves)
            rec.mo_count = len(list(set(move_ids.mapped('production_id').ids)))

    def _get_replenish_qty(self, after_forecast_qty):
        return 0

    def _get_components(self):
        component_ids = self.product_id.bom_ids.bom_line_ids.mapped('product_id.id')
        return component_ids
    
    def _count_components(self):
        for rec in self:
            component_ids = rec._get_components()
            rec.components_count = len(rec.search([('product_id', 'in', component_ids)]))
    
    def view_components(self):
        component_ids = self._get_components()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production.schedule',
            'views': [(False, 'list'), (False, 'form')],
            'view_mode': 'list,form',
            'target': 'current',
            'name': 'Components',
            # 'context': {'create': False, 'delete': False},
            'domain': [('product_id', 'in', component_ids),('project_id','=',self.project_id.id)],
        }
    
    def action_replenish(self, based_on_lead_time=False, date_start=False, date_stop=False):
        """ Run the procurement for production schedule in self. Once the
        procurements are launched, mark the forecast as launched (only used
        for state 'to_relaunch')

        :param based_on_lead_time: 2 replenishment options exists in MPS.
        based_on_lead_time means that the procurement for self will be launched
        based on lead times.
        e.g. period are daily and the product have a manufacturing period
        of 5 days, then it will try to run the procurements for the 5 first
        period of the schedule.
        If based_on_lead_time is False then it will run the procurement for the
        first period that need a replenishment
        """
        production_schedule_states = self.get_production_schedule_view_state(date_start, date_stop)
        production_schedule_states = {mps['id']: mps for mps in production_schedule_states}
        procurements = []
        forecasts_values = []
        forecasts_to_set_as_launched = self.env['mrp.product.forecast']
        for production_schedule in self:
            production_schedule_state = production_schedule_states[production_schedule.id]
            # Check for kit. If a kit and its component are both in the MPS we want to skip the
            # the kit procurement but instead only refill the components not in MPS
            bom = self.env['mrp.bom']._bom_find(
                production_schedule.product_id, company_id=production_schedule.company_id.id,
                bom_type='phantom')[production_schedule.product_id]
            product_ratio = []
            if bom:
                dummy, bom_lines = bom.explode(production_schedule.product_id, 1)
                product_ids = [l[0].product_id.id for l in bom_lines]
                product_ids_with_forecast = self.env['mrp.production.schedule'].search([
                    ('company_id', '=', production_schedule.company_id.id),
                    ('warehouse_id', '=', production_schedule.warehouse_id.id),
                    ('product_id', 'in', product_ids)
                ]).product_id.ids
                product_ratio += [
                    (l[0], l[0].product_qty * l[1]['qty'])
                    for l in bom_lines if l[0].product_id.id not in product_ids_with_forecast
                ]

            # Cells with values 'to_replenish' means that they are based on
            # lead times. There is at maximum one forecast by schedule with
            # 'forced_replenish', it's the cell that need a modification with
            #  the smallest start date.
            replenishment_field = based_on_lead_time and 'to_replenish' or 'forced_replenish'
            forecasts_to_replenish = filter(lambda f: f[replenishment_field], production_schedule_state['forecast_ids'])
            for forecast in forecasts_to_replenish:
                dt_start = date_start if date_start else forecast['date_start']
                dt_stop = date_stop if date_stop else forecast['date_stop']
                existing_forecasts = production_schedule.forecast_ids.filtered(lambda p:
                    p.date >= dt_start and p.date <= dt_stop
                )
                extra_values = production_schedule._get_procurement_extra_values(forecast)
                extra_values['date_planned'] = date_start if date_start else extra_values['date_planned']
                quantity = forecast['replenish_qty'] - forecast['incoming_qty']
                if self.env.ref('purchase_stock.route_warehouse0_buy').id in production_schedule.product_id.route_ids.ids:
                    replenish_id = self._replenishment(production_schedule, quantity)
                    production_schedule.orderpoint_ids = [(4,replenish_id.id)]
                    production_schedule.forecast_ids.filtered(lambda x:x.date == forecast['date_stop']).write({'procurement_launched': True, 'orderpoint': True})
                    continue
                if not bom:
                    procurements.append(self.env['procurement.group'].Procurement(
                        production_schedule.product_id,
                        quantity,
                        production_schedule.product_uom_id,
                        production_schedule.warehouse_id.lot_stock_id,
                        production_schedule.product_id.name,
                        'MPS', production_schedule.company_id, extra_values
                    ))
                else:
                    for bom_line, qty_ratio in product_ratio:
                        procurements.append(self.env['procurement.group'].Procurement(
                            bom_line.product_id,
                            quantity * qty_ratio,
                            bom_line.product_uom_id,
                            production_schedule.warehouse_id.lot_stock_id,
                            bom_line.product_id.name,
                            'MPS', production_schedule.company_id, extra_values
                        ))

                if existing_forecasts:
                    forecasts_to_set_as_launched |= existing_forecasts
                else:
                    forecasts_values.append({
                        'forecast_qty': 0,
                        'date': forecast['date_stop'],
                        'procurement_launched': True,
                        'production_schedule_id': production_schedule.id
                    })
        if procurements:
            self.env['procurement.group'].with_context(skip_lead_time=True).run(procurements)

        forecasts_to_set_as_launched.write({
            'procurement_launched': True,
        })
        if forecasts_values:
            self.env['mrp.product.forecast'].create(forecasts_values)

    def get_production_schedule_view_state(self, start_dt=False, stop_dt=False):
        """ Prepare and returns the fields used by the MPS client action.
        For each schedule returns the fields on the model. And prepare the cells
        for each period depending the manufacturing period set on the company.
        The forecast cells contains the following information:
        - forecast_qty: Demand forecast set by the user
        - date_start: First day of the current period
        - date_stop: Last day of the current period
        - replenish_qty: The quantity to replenish for the current period. It
        could be computed or set by the user.
        - replenish_qty_updated: The quantity to replenish has been set manually
        by the user.
        - starting_inventory_qty: During the first period, the quantity
        available. After, the safety stock from previous period.
        - incoming_qty: The incoming moves and RFQ for the specified product and
        warehouse during the current period.
        - outgoing_qty: The outgoing moves quantity.
        - indirect_demand_qty: On manufacturing a quantity to replenish could
        require a need for a component in another schedule. e.g. 2 product A in
        order to create 1 product B. If the replenish quantity for product B is
        10, it will need 20 product A.
        - safety_stock_qty:
        starting_inventory_qty - forecast_qty - indirect_demand_qty + replenish_qty
        """
        company_id = self.env.company
        date_range = []
        if start_dt and stop_dt:
            date_range = [(start_dt,start_dt),(stop_dt,stop_dt)]
        else:
            date_range = company_id._get_date_range()
        date_range_year_minus_1 = company_id._get_date_range(years=1)
        date_range_year_minus_2 = company_id._get_date_range(years=2)

        # We need to get the schedule that impact the schedules in self. Since
        # the state is not saved, it needs to recompute the quantity to
        # replenish of finished products. It will modify the indirect
        # demand and replenish_qty of schedules in self.
        schedules_to_compute = self.env['mrp.production.schedule'].browse(self.get_impacted_schedule()) | self

        # Dependencies between schedules
        indirect_demand_trees = schedules_to_compute._get_indirect_demand_tree()

        indirect_ratio_mps = schedules_to_compute._get_indirect_demand_ratio_mps(indirect_demand_trees)

        # Get the schedules that do not depends from other in first position in
        # order to compute the schedule state only once.
        indirect_demand_order = schedules_to_compute._get_indirect_demand_order(indirect_demand_trees)
        indirect_demand_qty = defaultdict(float)
        incoming_qty, incoming_qty_done = self._get_incoming_qty(date_range)
        outgoing_qty, outgoing_qty_done = self._get_outgoing_qty(date_range)
        dummy, outgoing_qty_year_minus_1 = self._get_outgoing_qty(date_range_year_minus_1)
        dummy, outgoing_qty_year_minus_2 = self._get_outgoing_qty(date_range_year_minus_2)
        read_fields = [
            'forecast_target_qty',
            'min_to_replenish_qty',
            'max_to_replenish_qty',
            'product_id',
        ]
        if self.env.user.has_group('stock.group_stock_multi_warehouses'):
            read_fields.append('warehouse_id')
        if self.env.user.has_group('uom.group_uom'):
            read_fields.append('product_uom_id')
        production_schedule_states = schedules_to_compute.read(read_fields)
        production_schedule_states_by_id = {mps['id']: mps for mps in production_schedule_states}
        for production_schedule in indirect_demand_order:
            # Bypass if the schedule is only used in order to compute indirect
            # demand.
            rounding = production_schedule.product_id.uom_id.rounding
            lead_time = production_schedule._get_lead_times()
            # Ignore "Days to Supply Components" when set demand for components since it's normally taken care by the
            # components themselves
            lead_time_ignore_components = lead_time - production_schedule.bom_id.days_to_prepare_mo
            production_schedule_state = production_schedule_states_by_id[production_schedule['id']]
            if production_schedule in self:
                procurement_date = add(fields.Date.today(), days=lead_time)
                precision_digits = max(0, int(-(log10(production_schedule.product_uom_id.rounding))))
                production_schedule_state['precision_digits'] = precision_digits
                production_schedule_state['forecast_ids'] = []

            starting_inventory_qty = production_schedule.product_id.with_context(warehouse=production_schedule.warehouse_id.id).qty_available
            if len(date_range):
                starting_inventory_qty -= incoming_qty_done.get((date_range[0], production_schedule.product_id, production_schedule.warehouse_id), 0.0)
                starting_inventory_qty += outgoing_qty_done.get((date_range[0], production_schedule.product_id, production_schedule.warehouse_id), 0.0)

            for index, (date_start, date_stop) in enumerate(date_range):
                forecast_values = {}
                key = ((date_start, date_stop), production_schedule.product_id, production_schedule.warehouse_id)
                key_y_1 = (date_range_year_minus_1[index], *key[1:])
                key_y_2 = (date_range_year_minus_2[index], *key[1:])
                existing_forecasts = production_schedule.forecast_ids.filtered(lambda p: p.date >= date_start and p.date <= date_stop)
                if production_schedule in self:
                    forecast_values['date_start'] = date_start
                    forecast_values['date_stop'] = date_stop
                    forecast_values['incoming_qty'] = float_round(incoming_qty.get(key, 0.0) + incoming_qty_done.get(key, 0.0), precision_rounding=rounding)
                    forecast_values['outgoing_qty'] = float_round(outgoing_qty.get(key, 0.0) + outgoing_qty_done.get(key, 0.0), precision_rounding=rounding)
                    forecast_values['outgoing_qty_year_minus_1'] = float_round(outgoing_qty_year_minus_1.get(key_y_1, 0.0), precision_rounding=rounding)
                    forecast_values['outgoing_qty_year_minus_2'] = float_round(outgoing_qty_year_minus_2.get(key_y_2, 0.0), precision_rounding=rounding)

                forecast_values['indirect_demand_qty'] = float_round(indirect_demand_qty.get(key, 0.0), precision_rounding=rounding, rounding_method='UP')
                replenish_qty_updated = False
                if existing_forecasts:
                    forecast_values['forecast_qty'] = float_round(sum(existing_forecasts.mapped('forecast_qty')), precision_rounding=rounding)
                    forecast_values['replenish_qty'] = float_round(sum(existing_forecasts.mapped('replenish_qty')), precision_rounding=rounding)

                    # Check if the to replenish quantity has been manually set or
                    # if it needs to be computed.
                    replenish_qty_updated = any(existing_forecasts.mapped('replenish_qty_updated'))
                    forecast_values['replenish_qty_updated'] = replenish_qty_updated
                else:
                    forecast_values['forecast_qty'] = 0.0

                if not replenish_qty_updated:
                    replenish_qty = production_schedule._get_replenish_qty(starting_inventory_qty - forecast_values['forecast_qty'] - forecast_values['indirect_demand_qty'])
                    forecast_values['replenish_qty'] = float_round(replenish_qty, precision_rounding=rounding)
                    forecast_values['replenish_qty_updated'] = False

                forecast_values['starting_inventory_qty'] = float_round(starting_inventory_qty, precision_rounding=rounding)
                forecast_values['safety_stock_qty'] = float_round(starting_inventory_qty - forecast_values['forecast_qty'] - forecast_values['indirect_demand_qty'] + forecast_values['replenish_qty'], precision_rounding=rounding)

                if production_schedule in self:
                    production_schedule_state['forecast_ids'].append(forecast_values)
                starting_inventory_qty = forecast_values['safety_stock_qty']
                if not forecast_values['replenish_qty']:
                    continue
                # Set the indirect demand qty for children schedules.
                for (product, ratio) in indirect_ratio_mps[(production_schedule.warehouse_id, production_schedule.product_id)].items():
                    related_date = max(subtract(date_start, days=lead_time_ignore_components), fields.Date.today())
                    if start_dt:
                        related_date = date_start
                    index = next(i for i, (dstart, dstop) in enumerate(date_range) if related_date <= dstart or (related_date >= dstart and related_date <= dstop))
                    related_key = (date_range[index], product, production_schedule.warehouse_id)
                    indirect_demand_qty[related_key] += ratio * forecast_values['replenish_qty']

            if production_schedule in self:
                # The state is computed after all because it needs the final
                # quantity to replenish.
                forecasts_state = production_schedule._get_forecasts_state(production_schedule_states_by_id, date_range, procurement_date)
                forecasts_state = forecasts_state[production_schedule.id]
                for index, forecast_state in enumerate(forecasts_state):
                    production_schedule_state['forecast_ids'][index].update(forecast_state)

                # The purpose is to hide indirect demand row if the schedule do not
                # depends from another.
                has_indirect_demand = any(forecast['indirect_demand_qty'] != 0 for forecast in production_schedule_state['forecast_ids'])
                production_schedule_state['has_indirect_demand'] = has_indirect_demand
        return [p for p in production_schedule_states if p['id'] in self.ids]


    def _replenishment(self, mps_id, quantity):
        orderpoint_obj = self.env['stock.warehouse.orderpoint'].sudo()
        exist = orderpoint_obj.search([
            ('product_id','=',mps_id.product_id.id),
            ('warehouse_id','=',mps_id.warehouse_id.id),
            ('active','=',True)
        ])
        orderpoint_id = None
        if exist:
            exist.update({
                'qty_to_order': exist.qty_to_order + quantity,
                'trigger': 'manual', # gw force yaaaa
            })
            orderpoint_id = exist
        else:
            orderpoint_id = orderpoint_obj.create({
                'name': 'Replenishment Report',
                'product_id': mps_id.product_id.id,
                'warehouse_id': mps_id.warehouse_id.id,
                'trigger': 'manual',
                'qty_to_order': quantity,
                'route_id': self.env.ref('purchase_stock.route_warehouse0_buy').id,
                'location_id': mps_id.warehouse_id.lot_stock_id.id,
            })
        return orderpoint_id


class MPSProductForecast(models.Model):
    _inherit = 'mrp.product.forecast'

    mo_count = fields.Integer(compute='_count_mo')
    rfq_count = fields.Integer(compute='_count_rfq')
    # orderpoint_count = fields.Integer(compute='_count_orderpoint')
    orderpoint_count = fields.Integer(related='production_schedule_id.orderpoint_count')
    orderpoint = fields.Boolean() # flagging udh dilempar ke replenishment apa belom

    @api.depends('production_schedule_id')
    def _count_mo(self):
        for rec in self:
            domain_moves = rec.production_schedule_id._get_moves_domain(date_start=rec.date, date_stop=rec.date, type='incoming')
            move_ids = rec.env['stock.move'].search(domain_moves)
            rec.mo_count = sum(move_ids.mapped('production_id.product_qty'))
    
    def action_view_mo(self):
        domain_moves = self.production_schedule_id._get_moves_domain(date_start=self.date, date_stop=self.date, type='incoming')
        move_ids = self.env['stock.move'].search(domain_moves)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
            'views': [(False, 'list'), (False, 'form')],
            'view_mode': 'list,form',
            'target': 'current',
            'name': 'Manufacturing Orders',
            # 'context': {'create': False, 'delete': False},
            'domain': [('id', 'in', move_ids.mapped('production_id').ids)],
        }

    @api.depends('production_schedule_id')
    def _count_rfq(self):
        for rec in self:
            rfq_domain = rec.production_schedule_id._get_rfq_domain(date_start=rec.date, date_stop=rec.date)
            purchase_order_line_ids = rec.env['purchase.order.line'].search(rfq_domain)
            rec.rfq_count = sum(purchase_order_line_ids.mapped('product_qty'))
    
    def action_view_rfq(self):
        rfq_domain = self.production_schedule_id._get_rfq_domain(date_start=self.date, date_stop=self.date)
        purchase_order_line_ids = self.env['purchase.order.line'].search(rfq_domain)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'views': [(False, 'list'), (False, 'form')],
            'view_mode': 'list,form',
            'target': 'current',
            'name': 'Request for Quotation',
            # 'context': {'create': False, 'delete': False},
            'domain': [('id', 'in', purchase_order_line_ids.mapped('order_id').ids)],
        }

    @api.onchange('date')
    def _onchange_date(self):
        if self.env.context.get('manual_mps',False):
            self.replenish_qty_updated = True

    @api.onchange('forecast_qty')
    def _onchange_forecast_qty(self):
        if self.env.context.get('manual_mps',False):
            self.replenish_qty = self.forecast_qty

    def action_view_orderpoint(self):
        return self.production_schedule_id.action_view_orderpoint()

    def action_replenish(self):
        return self.production_schedule_id.action_replenish(date_start=self.date, date_stop=self.date)
    
    @api.model
    def create(self, vals):
        res = super(MPSProductForecast, self).create(vals)
        if vals.get('forecast_qty',False):
            vals['replenish_qty'] = vals['forecast_qty']
            vals['replenish_qty_updated'] = True
        return res

    def unlink(self):
        domain_moves = self.production_schedule_id._get_moves_domain(date_start=self.date, date_stop=self.date, type='incoming')
        move_ids = self.env['stock.move'].search(domain_moves)
        if any(mo.state not in ('draft','cancel') for mo in move_ids.mapped('production_id')):
            raise ValidationError("You cannot delete daily production schedule, because manufacturing order (MO) is in-progress.")
        if any(mo.state == 'draft' for mo in move_ids.mapped('production_id')):
            for mo in move_ids.mapped('production_id').filtered(lambda x: x.state == 'draft'):
                mo.unlink()
        return super(MPSProductForecast, self).unlink()
