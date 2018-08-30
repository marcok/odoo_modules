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
    current_hours_running = fields.Float(string='Today Running Hours',
                                         default=0.0)
    user_id = fields.Many2one('res.users',
                              string='User of Employee')
    parent_user_id = fields.Many2one('res.users',
                                     string='User of Manager')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'hr_attendance_analysis_report')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW hr_attendance_analysis_report AS (
                 SELECT 
                     MIN(sheet.id) AS id,
                     sheet.id AS timesheet_id,
                     sheet.employee_id AS name,
                     emp.department_id AS department_id,
                     res.user_id AS user_id,
                     (SELECT r.user_id
                     FROM resource_resource r, hr_employee e
                     WHERE r.id = e.resource_id AND e.id=emp.parent_id) AS parent_user_id,
                     sheet.total_diff_hours AS total_duty_hours_running,
                     sheet.total_duty_hours_done AS total_duty_hours_done,
                     (SELECT a.running 
                        FROM hr_attendance a
                        WHERE a.check_in=(SELECT MAX(check_in) 
                            FROM hr_attendance att 
                            WHERE att.employee_id=sheet.employee_id) 
                            AND a.check_out IS NOT NULL 
                            AND a.employee_id=sheet.employee_id) AS current_hours_running
                FROM
                    hr_timesheet_sheet_sheet sheet,
                    hr_employee emp,
                   resource_resource res,
                    hr_department dp
                WHERE
                    sheet.employee_id=emp.id AND
                    emp.resource_id=res.id AND
                    emp.department_id=dp.id AND
                    emp.active=TRUE
                GROUP BY
                    sheet.id, emp.department_id, res.user_id, emp.parent_id)
        """)

        # vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
