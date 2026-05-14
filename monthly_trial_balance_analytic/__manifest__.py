{
    'name': 'Monthly Trial Balance by Analytic',
    'version': '17.0.1.0.0',
    'summary': 'Monthly trial balance with analytic plan/account breakdown',
    'category': 'Accounting/Accounting',
    'author': 'OpenAI',
    'license': 'OPL-1',
    'depends': ['account_reports', 'analytic'],
    'data': [
        'security/ir.model.access.csv',
        'data/monthly_trial_balance_report.xml',
    ],
    'installable': True,
    'application': False,
}
