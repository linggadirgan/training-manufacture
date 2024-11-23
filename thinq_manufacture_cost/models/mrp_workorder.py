from odoo import _, api, fields, models

class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    def button_finish(self):
        res = super(MrpWorkorder, self).button_finish()
        for wo in self:
            overhead = wo.production_id.overhead_cost_ids.filtered_domain([('operation_id','=',wo.operation_id.id)])
            for oh in overhead:
                oh.actual_hour = (wo.duration_expected / 60) if wo.duration == 0 else (wo.duration / 60)
        return res
    
    def _cal_cost(self):
        return super()._cal_cost() + sum(self.production_id.overhead_cost_ids.mapped('total_actual_cost'))