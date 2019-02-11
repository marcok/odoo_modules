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

import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError
import logging

_logger = logging.getLogger(__name__)


class TimesheetsByPeriod(models.Model):
    _name = "hr_timesheet_sheet.sheet.day"
    _description = "Timesheets by Period"
    _auto = False
    _order = 'name'

    name = fields.Date('Date', readonly=True)
    sheet_id = fields.Many2one('hr_timesheet_sheet.sheet', 'Sheet',
                               readonly=True, index=True)
    total_timesheet = fields.Float('Total Timesheet', readonly=True)
    total_attendance = fields.Float('Attendance', readonly=True)
    total_difference = fields.Float('Difference', readonly=True)

    _depends = {
        'account.analytic.line': ['date', 'unit_amount'],
        'hr.attendance': ['check_in', 'check_out', 'sheet_id'],
        'hr_timesheet_sheet.sheet': ['attendances_ids', 'timesheet_ids'],
    }

    @api.model_cr
    def init(self):
        self._cr.execute("""create or replace view %s as
            SELECT
                id,
                name,
                sheet_id,
                total_timesheet,
                total_attendance,
                cast(round(cast(total_attendance - total_timesheet as Numeric),2) as Double Precision) AS total_difference
            FROM
                ((
                    SELECT
                        MAX(id) as id,
                        name,
                        sheet_id,
                        timezone,
                        SUM(total_timesheet) as total_timesheet,
                        SUM(total_attendance) /60 as total_attendance
                    FROM
                        ((
                            select
                                min(l.id) as id,
                                p.tz as timezone,
                                l.date::date as name,
                                s.id as sheet_id,
                                sum(l.unit_amount) as total_timesheet,
                                0.0 as total_attendance
                            from
                                account_analytic_line l
                                LEFT JOIN hr_timesheet_sheet_sheet s ON s.id = l.sheet_id
                                JOIN hr_employee e ON s.employee_id = e.id
                                JOIN resource_resource r ON e.resource_id = r.id
                                LEFT JOIN res_users u ON r.user_id = u.id
                                LEFT JOIN res_partner p ON u.partner_id = p.id
                            group by l.date::date, s.id, timezone
                        ) union (
                            select
                                -min(a.id) as id,
                                p.tz as timezone,
                                (a.check_in AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC'))::date as name,
                                s.id as sheet_id,
                                0.0 as total_timesheet,
                                SUM(DATE_PART('day', (a.check_out AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC'))
                                                      - (a.check_in AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC')) ) * 60 * 24
                                    + DATE_PART('hour', (a.check_out AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC'))
                                                         - (a.check_in AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC')) ) * 60
                                    + DATE_PART('minute', (a.check_out AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC'))
                                                           - (a.check_in AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC')) )) as total_attendance
                            FROM
                                hr_attendance AS a
                                LEFT JOIN hr_timesheet_sheet_sheet s
                                ON s.id = a.sheet_id
                                JOIN hr_employee e
                                ON a.employee_id = e.id
                                JOIN resource_resource r
                                ON e.resource_id = r.id
                                LEFT JOIN res_users u
                                ON r.user_id = u.id
                                LEFT JOIN res_partner p
                                ON u.partner_id = p.id
                            WHERE check_out IS NOT NULL
                            group by (a.check_in AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC'))::date, s.id, timezone
                        )) AS foo
                        GROUP BY name, sheet_id, timezone
                )) AS bar""" % self._table)
