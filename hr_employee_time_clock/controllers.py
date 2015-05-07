# -*- coding: utf-8 -*-
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