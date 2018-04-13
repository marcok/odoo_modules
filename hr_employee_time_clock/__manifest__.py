# -*- coding: utf-8 -*-

##############################################################################
#
#    Clear Groups for Odoo
#    Copyright (C) 2016 Bytebrand GmbH (<http://www.bytebrand.net>).
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
    'version': '1.2',
    'depends': ['analytic',
                'hr_timesheet',
                'hr_attendance',
                'hr_contract',
                'hr_holidays'],
    'images': ['images/overundertime.png'],
    'installable': True,
    'data': [
        'data/hr_timesheet_sheet_data.xml',

        'views/hr_timesheet_sheet_views.xml',
        'views/hr_department_views.xml',
        # 'views/hr_timesheet_sheet_config_settings_views.xml',

        # Report
        'report/report_attendance_analysis_view.xml',

        # 'security/ir_rule.xml',
        # 'security/ir_rule_contract.xml',
        'security/hr_timesheet_sheet_security.xml',
        'security/ir.model.access.csv',

        # View file for the wizard
        'wizard/create_timesheet_with_tag_view.xml',
        'wizard/import_leave_requests_view.xml',
    ],
    'qweb': ['static/src/xml/timesheet.xml', ],
}
