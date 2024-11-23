{
    'name': 'Production Waste',
    'version': '1.0',
    'description': 'Production Waste Management',
    'summary': 'Production Waste Management',
    'author': 'Noval',
    'website': 'https://arkana.co.id/id',
    'license': 'LGPL-3',
    'category': 'mrp',
    'depends': [
        'mrp',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        'data/waste_mitigation.xml',
        'data/waste_type.xml',
        'data/sequence.xml',
        'data/cron.xml',

        'views/waste_record.xml',
        'views/waste_mitigation.xml',
        'views/waste_type.xml',

        'wizard/wizard_summary_waste_record.xml',

        'report/waste_record_pdf.xml',
        'report/report_data.xml',

        'views/menu.xml',
    ],
    'auto_install': False,
    'application': False,
    'assets': {
        
    }
}