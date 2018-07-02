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
    'name': "Employee time clock extension",
    'author': "Bytebrand Outsourcing AG",
    'summary': 'Overtime configurations',
    'website': "http://www.bytebrand.net",
    'category': 'Human Resources',
    'version': '11.0.0.0.2',
    'depends': ['hr_employee_time_clock', ],
    'installable': True,
    'data': [
        'views/hr_employee_views.xml',
        'views/res_users_views.xml',
        'views/resource_calendar_view.xml',
    ],

    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': False,

    'js': [],
    'qweb': [],
}
