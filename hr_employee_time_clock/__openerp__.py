{
    'name': "Employee time clock",
    'author': "Bytebrand GmbH",
	'summary': 'Track over- and under-time, generate timesheets, upload public holidays',
    'website': "http://www.bytebrand.net",
    'category': 'Human Resources',
    'version': '1.1',
    'depends': ['hr_timesheet_sheet', 'hr_attendance', 'hr_contract', 'hr_holidays'], #,'hr_attendance_analysis'
	'images': ['images/overundertime.png'],
	'installable': True,
    'data': [
		'security/ir_rule.xml',
        'security/ir.model.access.csv',
        'views.xml',
        # Report
        'report/report_attendance_analysis_view.xml',
        # View file for the wizard
        'wizard/create_timesheet_with_tag_view.xml', 
        'wizard/import_leave_requests_view.xml',
    ]
}
