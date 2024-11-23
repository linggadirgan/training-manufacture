from odoo import models

class ReportMoOverview(models.AbstractModel):
    _inherit = 'report.mrp.report_mo_overview'

    def _get_finished_operation_data(self, production, level=0, current_index=False):
        res = super()._get_finished_operation_data(production, level, current_index)
        currency = res['summary']['currency']
        done_operation_uom = res['summary']['uom_name']
        operations = res['details']
        index = 0
        for workorder in production.workorder_ids:
            overhead_ids = production.overhead_cost_ids.filtered_domain([('operation_id','=',workorder.operation_id.id)])
            for overhead in overhead_ids:
                hourly_cost = overhead.cost
                duration = workorder.get_duration() / 60
                overhead_cost = duration * hourly_cost
                res['summary']['mo_cost'] += overhead_cost
                res['summary']['real_cost'] += overhead_cost
                operations.append({
                    'level': level,
                    'index': f"{current_index}WO{index}",
                    'name': f"Overhead {workorder.workcenter_id.display_name}: {workorder.display_name}",
                    'quantity': duration,
                    'uom_name': done_operation_uom,
                    'uom_precision': 4,
                    'unit_cost': hourly_cost,
                    'mo_cost': currency.round(overhead_cost),
                    'real_cost': currency.round(overhead_cost),
                    'currency_id': currency.id,
                    'currency': currency,
                })
                index += 1
        return res