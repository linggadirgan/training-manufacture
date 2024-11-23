from odoo import _, api, fields, models

class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    project_id = fields.Many2one('sk.project', 'Project')
    sale_line_id = fields.Many2one('sale.order.line', 'Sale Order Line')
    qty_to_order = fields.Float('To Order', compute=False, store=True, readonly=False)
    src_model = fields.Char('Resource Model')
    res_id = fields.Integer('Resource ID')

    def get_relation(self):
        # get relation of many various Forecast Customer models
        return self.env[self.src_model].browse(self.res_id)

    def _prepare_procurement_values(self, date=False, group=False):
        res = super(StockWarehouseOrderpoint, self)._prepare_procurement_values(date,group)
        res['project_id'] = self.project_id.id
        return res
    
    def action_replenish(self):
        res = super(StockWarehouseOrderpoint, self).action_replenish()
        for item in self:
            item.qty_to_order = 0 # Force 0
            if item.qty_to_order == 0:
                # item.unlink() #aneh ga update
                item.active = False
        return res