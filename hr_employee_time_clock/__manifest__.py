# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2016 - now Bytebrand Outsourcing AG (<http://www.bytebrand.net>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': "Employee time clock",
    'author': "Bytebrand GmbH",
    'summary': 'Track over- and under-time, generate timesheets, upload public holidays',
    'website': "http://www.bytebrand.net",
    'category': 'Human Resources',
    'version': '11.0.0.0.11',
    'depends': ['mail',
                'analytic',
                'hr_timesheet',
                'hr_attendance',
                'hr_contract',
                'hr_holidays'],
    'images': ['images/overundertime.png'],
    'installable': True,
    'data': [
        'data/hr_timesheet_sheet_data.xml',

        'views/hr_timesheet_sheet_views.xml',

        'views/hr_attendance_subtypes.xml',
        'views/hr_holidays_views.xml',
        'views/hr_department_views.xml',

        # Report
        'report/report_attendance_analysis_view.xml',

        'security/hr_timesheet_security.xml',
        'security/ir.model.access.csv',

        # View file for the wizard
        'wizard/create_timesheet_with_tag_view.xml',
        'wizard/import_leave_requests_view.xml',

        # Extension
        'views/res_config_settings_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_contract_views.xml',
        'views/resource_calendar_view.xml',
    ],
    'qweb': ['static/src/xml/timesheet.xml', ],
}
