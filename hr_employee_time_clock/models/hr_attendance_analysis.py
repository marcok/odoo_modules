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


import time
from pytz import timezone
import pytz
from odoo.tools import (
    DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_DATETIME_FORMAT,
    drop_view_if_exists,
)

import math
from odoo import models, api, _, fields
from datetime import datetime
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

def _employee_get(obj):
    employee = obj.env['hr.employee'].search([('user_id', '=', obj.env.uid)])
    if employee:
        return employee.id and employee[0].id
    else:
        return False

class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    @api.multi
    def _get_attendance_employee_tz(self, employee_id, date):
        """ Simulate timesheet in employee timezone

        Return the attendance date in string format in the employee
        tz converted from utc timezone as we consider date of employee
        timesheet is in employee timezone
        """
        employee_obj = self.env['hr.employee']
        tz = False
        if employee_id:
            employee = employee_obj.browse(employee_id)
            tz = employee.user_id.partner_id.tz
        if not date:
            date = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        att_tz = timezone(tz or 'utc')
        attendance_dt = datetime.strptime(date, DEFAULT_SERVER_DATETIME_FORMAT)
        att_tz_dt = pytz.utc.localize(attendance_dt)
        att_tz_dt = att_tz_dt.astimezone(att_tz)
        att_tz_date_str = datetime.strftime(att_tz_dt,
                                            DEFAULT_SERVER_DATE_FORMAT)
        return att_tz_date_str

    @api.multi
    def _get_current_sheet(self, employee_id, date=False):

        sheet_obj = self.env['hr_timesheet_sheet.sheet']
        if not date:
            date = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        att_tz_date_str = self._get_attendance_employee_tz(
            employee_id, date=date)
        sheet_ids = sheet_obj.search(
            [('date_from', '<=', att_tz_date_str),
             ('date_to', '>=', att_tz_date_str),
             ('employee_id', '=', employee_id)],
            limit=1)
        return sheet_ids and sheet_ids[0] or False

    @api.multi
    def _get_hr_timesheet_sheet(self):
        attendance_ids = []
        for ts in self:
            self.env.cr.execute("""
                        SELECT a.id
                          FROM hr_attendance a
                         INNER JOIN hr_employee e
                               INNER JOIN resource_resource r
                                       ON (e.resource_id = r.id)
                            ON (a.employee_id = e.id)
                         LEFT JOIN res_users u
                         ON r.user_id = u.id
                         LEFT JOIN res_partner p
                         ON u.partner_id = p.id
                         WHERE %(date_to)s >= date_trunc('day', a.name AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC'))
                              AND %(date_from)s <= date_trunc('day', a.name AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC'))
                              AND %(user_id)s = r.user_id
                         GROUP BY a.id""", {'date_from': ts.date_from,
                                            'date_to': ts.date_to,
                                            'user_id': ts.employee_id.user_id.id, })
            attendance_ids.extend([row[0] for row in self.env.cr.fetchall()])
        return attendance_ids

    @api.multi
    @api.depends('employee_id', 'check_in', 'check_out')
    def _sheet(self):
        res = {}.fromkeys(self, False)
        for attendance in self:
            sheet = self._get_current_sheet(
                attendance.employee_id.id, attendance.name)
            if sheet:
                attendance.sheet_id = sheet.id

    # store = {'hr_timesheet_sheet.sheet': (_get_hr_timesheet_sheet,
    #                                       ['employee_id', 'date_from',
    #                                        'date_to'], 10),
    #          'hr.attendance': (lambda self, cr, uid, ids, context=None: ids,
    #                            ['employee_id', 'name', 'day'], 10),
    #          },


    name = fields.Datetime(string='Date',
                           required=True,
                           select=1,
                           default = (lambda *a: time.strftime('%Y-%m-%d %H:%M:%S')))

    sheet_id = fields.Many2one(
        'hr_timesheet_sheet.sheet',
        compute='_sheet',
        string='Sheet',
        store=True)

    def float_time_convert(self, float_val):
        hours = math.floor(abs(float_val))
        mins = abs(float_val) - hours
        mins = round(mins * 60)
        if mins >= 60.0:
            hours += 1
            mins = 0.0
        float_time = '%02d:%02d' % (hours, mins)
        return float_time

    @api.model
    def create(self, values):
        if values.get('name'):
            times = datetime.strptime(values.get('name'), "%Y-%m-%d %H:%M:%S")
            if datetime.now() < times:
                raise ValidationError(
                    _('You can not set time of Sing In (resp. Sing Out) which '
                      'is later than a current time'))
        return super(HrAttendance, self).create(values)
