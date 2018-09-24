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
from pytz import timezone
import pytz
from odoo.tools import (
    DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_DATETIME_FORMAT,
    drop_view_if_exists,
)

import math
from odoo import models, api, _, fields
from datetime import datetime, time, timedelta
from odoo.exceptions import ValidationError, AccessError
import logging

_logger = logging.getLogger(__name__)


def _employee_get(obj):
    employee = obj.env['hr.employee'].search([('user_id', '=', obj.env.uid)])
    if employee:
        return employee.id and employee[0].id
    else:
        return False


class HrAttendance(models.Model):
    _name = "hr.attendance"
    _inherit = ["hr.attendance", "mail.thread"]

    check_in = fields.Datetime(string="Check In", default=fields.Datetime.now,
                               required=True, track_visibility='always')
    check_out = fields.Datetime(string="Check Out", track_visibility='always')

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
        """
        Returns current timesheet (depends on date)
        :param employee_id: hr.employee object's id
        :param date: datetime object
        :return: hr_timesheet_sheet.sheet object or False
        """
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
                attendance.employee_id.id, attendance.check_in)
            if sheet:
                attendance.sheet_id = sheet.id

    name = fields.Datetime(string='Date',
                           required=True,
                           select=1,
                           default=datetime.now())

    sheet_id = fields.Many2one(
        'hr_timesheet_sheet.sheet',
        compute='_sheet',
        string='Sheet',
        store=True,
        index=True)

    def float_time_convert(self, float_val):
        """
        Converts float value of hours into time value
        :param float_val: hours/minutes in float type
        :return: string
        """
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
        check_in = fields.Datetime.from_string(values.get('check_in'))
        sheet_id = self.env['hr_timesheet_sheet.sheet'].search([
            ('employee_id', '=', values.get('employee_id')),
            ('date_from', '<=', check_in.date()),
            ('date_to', '>=', check_in.date())], limit=1)
        if sheet_id.state == 'done' and not \
                self.user_has_groups('hr.group_hr_user'):
            raise AccessError(
                _(
                    "Sorry, only manager is allowed to create attendance"
                    " of approved attendance sheet."))

        values['name'] = values.get('check_in')
        if values.get('name'):
            times = datetime.strptime(values.get('name'), "%Y-%m-%d %H:%M:%S")
            if datetime.now() < times:
                raise ValidationError(
                    _('You can not set time of Sing In (resp. Sing Out) which '
                      'is later than a current time'))
        return super(HrAttendance, self).create(values)

    @api.multi
    def write(self, values):
        if values.get('check_in'):
            values['name'] = values.get('check_in')
            times = datetime.strptime(values.get('name'), "%Y-%m-%d %H:%M:%S")
            if datetime.now() < times:
                raise ValidationError(
                    _('You can not set time of Sing In (resp. Sing Out) which '
                      'is later than a current time'))
        if self.sheet_id.state == 'done' and not \
                self.user_has_groups('hr.group_hr_user'):
            raise AccessError(
                _(
                    "Sorry, only manager is allowed to edit attendance"
                    " of approved attendance sheet."))
    ##################################################
    # Attendance separating
    ##################################################
    #
    #     if values.get('check_out'):
    #         local_tz = pytz.timezone(self.env.user.tz or 'UTC')
    #
    #         if values.get('check_in'):
    #             check_in = fields.Datetime.from_string(values.get('check_in'))
    #         else:
    #             check_in = fields.Datetime.from_string(self.check_in).replace(
    #                 tzinfo=pytz.utc).astimezone(local_tz)
    #         check_in = check_in.replace(tzinfo=None)
    #
    #         if values.get('check_out'):
    #             check_out = fields.Datetime.from_string(values.get('check_out'))
    #         else:
    #             check_out = fields.Datetime.from_string(
    #                 self.check_out).replace(tzinfo=pytz.utc).astimezone(
    #                 local_tz)
    #         check_out = check_out.replace(tzinfo=None)
    #
    #         midnight_without_tzinfo = datetime.combine(check_out.date(), time())
    #         midnight = local_tz.localize(midnight_without_tzinfo).astimezone(
    #             pytz.utc)
    #         midnight = midnight.replace(tzinfo=None)
    #
    #         if check_in < midnight < check_out:
    #             check_out_old = check_out
    #             check_out_new = midnight - timedelta(seconds=1)
    #             values.update(check_out=str(check_out_new))
    #             res = super(HrAttendance, self).write(values)
    #             att = self.env['hr.attendance'].create({
    #                 'employee_id': self.employee_id.id,
    #                 'check_in': str(midnight),
    #
    #                 'name': str(midnight)})
    #             att.write({'check_out': str(check_out_old)})
    #             return res
        return super(HrAttendance, self).write(values)

