# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import tools
from odoo import api, fields, models


class HrAttendanceAnalysisReport(models.Model):
    _name = "hr.attendance.analysis.report"
    _description = "Attendance Analysis based on Timesheet"
    _auto = False

    name = fields.Many2one('hr.employee',
                           string='Employee')
    department_id = fields.Many2one('hr.department',
                                    string='Department')
    timesheet_id = fields.Many2one('hr_timesheet_sheet.sheet',
                                   string='Timesheet')
    total_duty_hours_running = fields.Float(string='Running Hours')
    total_duty_hours_done = fields.Float(string='Duty Hours')
    user_id = fields.Many2one('res.users',
                              string='User of Employee')
    parent_user_id = fields.Many2one('res.users',
                                     string='User of Manager')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'hr_attendance_analysis_report')
        self.env.cr.execute("""
            CREATE or REPLACE view hr_attendance_analysis_report as (
                 select
                     min(sheet.id) as id,
                     sheet.id as timesheet_id,
                     sheet.employee_id as name,
                     emp.department_id as department_id,
                     res.user_id as user_id,
                     (select r.user_id
                     from resource_resource r, hr_employee e
                     where r.id = e.resource_id and e.id=emp.parent_id) as parent_user_id,
                     sheet.total_diff_hours as total_duty_hours_running,
                     sheet.total_duty_hours_done as total_duty_hours_done
                from
                    hr_timesheet_sheet_sheet sheet,
                    hr_employee emp,
                    resource_resource res,
                    hr_department dp
                where
                    sheet.employee_id=emp.id AND
                    emp.resource_id=res.id AND
                    emp.department_id=dp.id
                group by
                    sheet.id, emp.department_id, res.user_id, emp.parent_id
            )
        """)


        # vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
