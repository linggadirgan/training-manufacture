from odoo import http
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime
import io
import xlsxwriter
import pytz

class WasteReportController(http.Controller):
    @http.route('/waste/report/download', type='http', auth='user')
    def download_excel_report(self, **kwargs):
        date_start = kwargs.get('date_start', False)
        date_end = kwargs.get('date_end', False)
        state = kwargs.get('state', False)

        output = io.BytesIO()

        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,
        })
        worksheet = workbook.add_worksheet('Waste Records')

        header_format = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#F5F5F5'})

        headers = ['Reference', 'Date', 'Waste Type', 'Quantity (kg)', 'Status']
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, header_format)

        domain = []

        user_tz = request.env.user.tz or 'UTC'
        tz = pytz.timezone(user_tz)

        if date_start:
            date_start = datetime.strptime(date_start, DEFAULT_SERVER_DATETIME_FORMAT)
            date_start = pytz.utc.localize(date_start).astimezone(tz)
            domain += [('date_planned', '>=', date_start)]

        if date_end:
            date_end = datetime.strptime(date_end, DEFAULT_SERVER_DATETIME_FORMAT)
            date_end = pytz.utc.localize(date_end).astimezone(tz)
            domain += [('date_planned', '<=', date_end)]

        if state:
            domain += [('state','=',kwargs['state'])]
        
        records = request.env['waste.record'].search(domain)
        row = 1
        for record in records:
            worksheet.write(row, 0, record.name)
            worksheet.write(row, 1, record.date_planned.strftime('%d %B %Y %H:%M:%S'))
            worksheet.write(row, 2, record.waste_type_id.name or '')
            worksheet.write(row, 3, record.total_quantity)
            worksheet.write(row, 4, record.state.capitalize())
            row += 1

        workbook.close()
        output.seek(0)
        file_data = output.read()
        output.close()

        return request.make_response(
            file_data,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', 'attachment; filename="Waste_Report.xlsx"'),
            ]
        )