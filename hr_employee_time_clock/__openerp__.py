# -*- coding: utf-8 -*-
{
    'name': "hr_employee_time_clock",
    'author': "Bytebrand GmbH",
    'website': "http://www.bytebrand.net",
    'category': 'Uncategorized',
    'version': '0.1',
    'depends': ['hr_timesheet_sheet'],
    'data': [
        'security/ir.model.access.csv',
        'templates.xml',
        'views.xml',
        'wizard/create_timesheet_with_tag_view.xml', # View file for the wizard
    ]
}