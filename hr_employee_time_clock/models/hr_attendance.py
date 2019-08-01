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


# import datetime
import math
import pytz

from datetime import timedelta, datetime, time, date
from pytz import timezone
from odoo.tools import (
    DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_DATETIME_FORMAT,
    drop_view_if_exists,
)
from dateutil import rrule, parser
from odoo import api, fields, models, _
from odoo.tools import pycompat
from odoo.exceptions import AccessError
import calendar
import logging
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)

USER_PRIVATE_FIELDS = ['password']


def float_to_time(float_hour):
    return time(int(math.modf(float_hour)[1]),
                int(60 * math.modf(float_hour)[0]), 0)


def to_naive_user_tz(datetime, record):
    tz_name = record._context.get('tz') or record.env.user.tz
    tz = tz_name and pytz.timezone(tz_name) or pytz.UTC
    return pytz.UTC.localize(datetime.replace(tzinfo=None),
                             is_dst=False).astimezone(tz).replace(tzinfo=None)


def to_naive_utc(datetime, record):
    tz_name = record._context.get('tz') or record.env.user.tz
    tz = tz_name and pytz.timezone(tz_name) or pytz.UTC
    return tz.localize(datetime.replace(tzinfo=None), is_dst=False).astimezone(
        pytz.UTC).replace(tzinfo=None)


def to_tz(datetime, tz_name):
    tz = pytz.timezone(tz_name)
    return pytz.UTC.localize(datetime.replace(
        tzinfo=None), is_dst=False).astimezone(tz).replace(tzinfo=None)


class HrAttendance(models.Model):
    _name = "hr.attendance"
    _inherit = ["hr.attendance", "mail.thread"]
    _description = 'HrAttendance'

    check_in = fields.Datetime(string="Check In", default=fields.Datetime.now,
                               required=True, track_visibility='always')
    check_out = fields.Datetime(string="Check Out", track_visibility='always')

    name = fields.Datetime(string='Date',
                           required=True,
                           default=datetime.now())

    sheet_id = fields.Many2one('hr_timesheet_sheet.sheet',
                               compute='_sheet',
                               string='Sheet',
                               store=True,
                               index=True)

    line_analytic_id = fields.Many2one(
        'employee.attendance.analytic',
        string='Attendance Line Analytic')

    have_overtime = fields.Boolean(string="Have Overtime",
                                   default=False)
    calculate_overtime = fields.Boolean(string="Calculate Overtime",
                                        default=False)
    overtime_change = fields.Boolean(string="Change Overtime",
                                     default=False)
    bonus_worked_hours = fields.Float(string='Bonus Worked Hours',
                                      readonly=True, default=0.0)
    night_shift_worked_hours = fields.Float(string='Night Shift',
                                            readonly=True, default=0.0)
    running = fields.Float(string="Running",
                           readonly=True,
                           default=0.0)

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
        attendance_dt = datetime.strptime(str(date), DEFAULT_SERVER_DATETIME_FORMAT)
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

    @api.multi
    def get_employee_sheets(self, employee, check_in):
        sheet_ids = []
        year = int(str(check_in).split('-')[0])
        sheets = self.env['hr_timesheet_sheet.sheet'].search(
            [('employee_id', '=', employee.id)])
        for sheet in sheets:
            if str(year) in str(sheet.date_from) or str(year) in str(sheet.date_to):
                sheet_ids.append(sheet.id)
        return sheet_ids

    @api.multi
    def _calculate_overtime(self, check_in, check_out, this_year_sheets):
        """
        Checks if employee has overtime in current attendance.
        """
        contract = self.get_contract(check_out)
        if contract:
            resource_calendar_id = contract.resource_calendar_id
        else:
            resource_calendar_id = self.employee_id.resource_calendar_id
        attendances = self.search([
            ('employee_id', '=', self.employee_id.id),
            ('sheet_id', 'in', this_year_sheets),
            ('id', '!=', self.id)], order='id asc')
        calculate_overtime = True
        cl_attendance = self
        for attendance in attendances:
            if not cl_attendance.check_out:
                cl_attendance = attendances[-1]

            elif attendance.check_out \
                    and str(cl_attendance.check_out) < str(attendance.check_out) < str(check_in):
                cl_attendance = attendance
        if cl_attendance != self:
            self_date = check_out.split(' ')[0].split('-')
            self_day_of_week = calendar.weekday(int(self_date[0]),
                                                int(self_date[1]),
                                                int(self_date[2]))

            self_overtime_calendar = \
                self.env['resource.calendar.attendance.overtime'].search(
                    [('overtime_calendar_id', '=',
                      resource_calendar_id.id),
                     ('dayofweek', '=', self_day_of_week)])

            attendance_date = str(cl_attendance.check_out).split(' ')[0].split('-')
            cl_attendance_day = calendar.weekday(int(attendance_date[0]),
                                                 int(attendance_date[1]),
                                                 int(attendance_date[2]))
            closest_overtime_calendar = \
                self.env['resource.calendar.attendance.overtime'].search(
                    [('overtime_calendar_id', '=',
                      resource_calendar_id.id),
                     ('dayofweek', '=', cl_attendance_day)])

            delta = relativedelta(
                fields.Datetime.from_string(cl_attendance.check_out),
                fields.Datetime.from_string(check_out))
            if self_overtime_calendar == closest_overtime_calendar and \
                            delta.days < 1:
                calculate_overtime = False
        return calculate_overtime

    @api.multi
    def get_contract(self, time_info=None):
        """
        Returns current employee's contract
        """
        if not time_info:
            time_info = self.check_out
        if not time_info:
            time_info = self.check_in
        user_tz = pytz.timezone(
            self.employee_id.user_id.tz or 'UTC')
        local_date = fields.Datetime.from_string(
            time_info).replace(tzinfo=pytz.utc).astimezone(user_tz)
        local_date = local_date.replace(tzinfo=None)
        contract = self.env['hr.contract'].search(
            [('employee_id', '=', self.sheet_id.employee_id.id),
             ('date_start', '<=', local_date),
             '|',
             ('date_end', '>=', local_date),
             ('date_end', '=', None)])
        if len(contract) > 1:
            contract = contract[-1]
        return contract

    @api.multi
    def check_overtime(self, values):
        """
        Calculates bonus hours, night worked shift hours for current attendance on
        write method.
        """
        overtime_context = self.env.context.copy()
        overtime_context['check_overtime'] = True
        check_out = values.get('check_out')

        if not check_out:
            check_out = self.check_out
        contract = self.get_contract(check_out)
        if contract:
            resource_calendar_id = contract.resource_calendar_id
        else:
            resource_calendar_id = self.employee_id.resource_calendar_id
        two_days_shift = resource_calendar_id.two_days_shift

        if check_out and resource_calendar_id \
                and resource_calendar_id.use_overtime \
                and not self.env.context.get('bonus_time'):

            user_tz = pytz.timezone(
                self.employee_id.user_id.tz or 'UTC')
            check_out_local_date = fields.Datetime.from_string(
                check_out).replace(tzinfo=pytz.utc).astimezone(user_tz)
            check_out_local_date = check_out_local_date.replace(tzinfo=None)
            check_in = self.check_in
            if values.get('check_in'):
                check_in = values.get('check_in')
            check_in_local_date = fields.Datetime.from_string(
                check_in).replace(tzinfo=pytz.utc).astimezone(user_tz)
            check_in_local_date = check_in_local_date.replace(tzinfo=None)

            need_overtime = None
            if two_days_shift:
                str_check_in_local_date = (
                    check_in_local_date -
                    timedelta(days=1)).strftime('%Y-%m-%d')

                str_check_out_local_date = (
                    check_out_local_date +
                    timedelta(days=1)).strftime('%Y-%m-%d')
            else:

                str_check_in_local_date = (
                    check_in_local_date).strftime('%Y-%m-%d')

                str_check_out_local_date = (
                    check_out_local_date).strftime('%Y-%m-%d')

            dates = list(rrule.rrule(
                rrule.DAILY,
                dtstart=parser.parse(str_check_in_local_date),
                until=parser.parse(str_check_out_local_date)))
            date_len = len(dates)
            i = 0
            overtime_minutes = 0.0
            delta_minutes = 0.0
            if two_days_shift:
                loop_count = date_len - 1
            else:
                loop_count = date_len
            while i < loop_count:
                day_of_week = calendar.weekday(dates[i].year,
                                               dates[i].month,
                                               dates[i].day)

                overtime_calendar_attendances = \
                    self.env[
                        'resource.calendar.attendance.overtime'].search(
                        [('overtime_calendar_id', '=',
                          resource_calendar_id.id),
                         ('dayofweek', '=', day_of_week)])
                for overtime_calendar_attendance in overtime_calendar_attendances:
                    start_overtime = datetime.combine(
                        date(dates[i].year,
                             dates[i].month,
                             dates[i].day),
                        float_to_time(overtime_calendar_attendance.hour_from))
                    if two_days_shift:
                        finish_overtime = datetime.combine(
                            date(dates[i + 1].year,
                                 dates[i + 1].month,
                                 dates[i + 1].day),
                            float_to_time(overtime_calendar_attendance.hour_to))
                    else:
                        finish_overtime = datetime.combine(
                            date(dates[i].year,
                                 dates[i].month,
                                 dates[i].day),
                            float_to_time(overtime_calendar_attendance.hour_to))
                    if finish_overtime.hour == 23 \
                            and finish_overtime.minute >= 55:
                        finish_overtime = finish_overtime.replace(
                            minute=59, second=59, microsecond=9999)
                    if (check_in_local_date < start_overtime
                        and (
                                    start_overtime < check_out_local_date < finish_overtime
                        or check_out_local_date > finish_overtime)) \
                            or (finish_overtime > check_in_local_date
                                    > start_overtime
                                and (start_overtime < check_out_local_date
                                         < finish_overtime
                                     or check_out_local_date > finish_overtime)):
                        need_overtime = overtime_calendar_attendance
                        if check_in_local_date > start_overtime:
                            if finish_overtime > check_out_local_date:
                                overtime_minutes += \
                                    (check_out_local_date -
                                     check_in_local_date).total_seconds() / 60
                            else:
                                overtime_minutes += \
                                    (finish_overtime -
                                     check_in_local_date).total_seconds() / 60
                        elif start_overtime > check_in_local_date:
                            if finish_overtime > check_out_local_date:
                                overtime_minutes += \
                                    (check_out_local_date -
                                     start_overtime).total_seconds() / 60
                            else:
                                overtime_minutes += \
                                    (finish_overtime -
                                     start_overtime).total_seconds() / 60
                i += 1

                delta_minutes = \
                    (overtime_minutes *
                     resource_calendar_id.count / 100)
            if need_overtime:
                this_year_sheets = self.get_employee_sheets(
                    self.employee_id, check_in)
                values.update(have_overtime=True,
                              bonus_worked_hours=delta_minutes / 60,
                              calculate_overtime=self._calculate_overtime(
                                  check_in, check_out, this_year_sheets),
                              night_shift_worked_hours=overtime_minutes / 60,
                              overtime_change=True)
                overtime_attendance = self.search([
                    ('calculate_overtime', '=', True),
                    ('employee_id', '=', self.employee_id.id),
                    ('sheet_id', 'in', this_year_sheets)
                ])
                min_overtime_count = \
                    resource_calendar_id.min_overtime_count
                real_overtime_count = (len(overtime_attendance) +
                                       self.employee_id.start_overtime_different)
                if real_overtime_count >= min_overtime_count:

                    change_overtime_attendance = \
                        overtime_attendance.filtered(
                            lambda
                                attendance: not attendance.overtime_change)
                    no_change_overtime_attendance = \
                        overtime_attendance.filtered(
                            lambda attendance: attendance.overtime_change)
                    val = {}
                    if change_overtime_attendance:
                        for over in change_overtime_attendance:
                            ctx = self.env.context.copy()
                            ctx['bonus_time'] = True
                            val.update(overtime_change=True)
                            over.sudo().with_context(ctx).write(val)
                    elif no_change_overtime_attendance:
                        for over in no_change_overtime_attendance:
                            ctx = self.env.context.copy()
                            ctx['bonus_time'] = True
                            val.update(overtime_change=True)
                            over.sudo().with_context(ctx).write(val)

                else:
                    for over in overtime_attendance:
                        over.with_context(overtime_context).write(
                            {'overtime_change': False})
            else:

                values.update(have_overtime=False,
                              bonus_worked_hours=0.0,
                              calculate_overtime=False,
                              night_shift_worked_hours=0.0)
                # res = super(HrAttendance, self).write(values)
        elif not self.env.context.get('bonus_time'):
            values.update(have_overtime=False,
                          bonus_worked_hours=0.0,
                          calculate_overtime=False,
                          night_shift_worked_hours=0.0)
            # res = super(HrAttendance, self).write(values)
        return values
        # return res

    @api.multi
    def write(self, values):
        if not self.env.context.get('check_overtime'):
            values = self.check_overtime(values)
        check_in = values.get('check_in') or self.check_in
        if check_in:
            values['name'] = check_in
            times = datetime.strptime(str(values.get('name')), "%Y-%m-%d %H:%M:%S")
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

        check_out = values.get('check_out') or self.check_out
        if check_out and check_in:
            self.env['employee.attendance.analytic'].recalculate_line_worktime(
                self, values)
        return super(HrAttendance, self).write(values)

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
            times = datetime.strptime(str(values.get('name')), "%Y-%m-%d %H:%M:%S")
            if datetime.now() < times:
                raise ValidationError(
                    _('You can not set time of Sing In (resp. Sing Out) which '
                      'is later than a current time'))
        attendance = super(HrAttendance, self).create(values)
        if values.get('check_out'):
            val = {'check_out': values.get('check_out')}
            values = attendance.check_overtime(val)
            attendance.write(values)
            self.env['employee.attendance.analytic'].recalculate_line_worktime(
                attendance, values)
        else:
            self.env['employee.attendance.analytic'].recalculate_line_worktime(
                attendance, values)
        return attendance

    @api.multi
    def unlink(self):
        for attendance in self:
            name = str(attendance.check_in).split(' ')[0]
            analytic = self.env['employee.attendance.analytic'].search(
                [('name', '=', name),
                 ('sheet_id', '=', attendance.sheet_id.id)])
            res = super(HrAttendance, attendance).unlink()

            analytic.unlink_attendance()
        return res

