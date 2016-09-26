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


from openerp import http

# class HrTimesheetOvertime(http.Controller):
#     @http.route('/hr_timesheet_overtime/hr_timesheet_overtime/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_timesheet_overtime/hr_timesheet_overtime/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_timesheet_overtime.listing', {
#             'root': '/hr_timesheet_overtime/hr_timesheet_overtime',
#             'objects': http.request.env['hr_timesheet_overtime.hr_timesheet_overtime'].search([]),
#         })

#     @http.route('/hr_timesheet_overtime/hr_timesheet_overtime/objects/<model("hr_timesheet_overtime.hr_timesheet_overtime"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_timesheet_overtime.object', {
#             'object': obj
#         })