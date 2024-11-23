{
    'name': 'Thinq - Manufacture Cost',
    'version': '1.0',
    'description': 'Compute Employee, Energy, and Overhead cost in manufacture process',
    'summary': 'Compute Employee, Energy, and Overhead cost in manufacture process',
    'author': 'Thinq Technology',
    'website': 'https://thinq-tech.id',
    'license': 'LGPL-3',
    'category': 'custom',
    'depends': [
        'mrp_account',
        'account_accountant',
        'mrp_workorder',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_category.xml',
        'views/mrp_production.xml',
        'views/mrp_workcenter.xml',
        'views/mrp_bom.xml',
    ],
    'demo': [
    ],
    'auto_install': False,
    'application': True,
}