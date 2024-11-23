from odoo import _, api, fields, models

class WizardSummaryWasteRecord(models.TransientModel):
    _name = 'wizard.summary.waste.record'

    date_start = fields.Datetime('Date Start')
    date_end = fields.Datetime('Date End')
    state = fields.Selection(selection=lambda self: self.env['waste.record']._fields['state'].selection, string='Status')

    def generate(self):
        url = '/waste/report/download'
        qparams = []

        if self.date_start:
            qparams.append('date_start=%s' % self.date_start)
        if self.date_end:
            qparams.append('date_end=%s' % self.date_end)
        if self.state:
            qparams.append('state=%s' % self.state)
        
        url = f'{url}?{"&".join(qparams)}'

        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }