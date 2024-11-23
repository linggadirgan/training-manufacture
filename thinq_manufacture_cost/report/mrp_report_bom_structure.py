from odoo import api, models


class ReportBomStructure(models.AbstractModel):
    _inherit = 'report.mrp.report_bom_structure'

    def _get_operation_cost(self, duration, operation):
        overhead_cost = (duration / 60.0) * operation.workcenter_id.overhead_costs_hour
        return super()._get_operation_cost(duration, operation) + overhead_cost