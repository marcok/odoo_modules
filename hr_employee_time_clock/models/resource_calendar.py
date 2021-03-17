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

import datetime as dtime

from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import pytz


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    def get_working_intervals_of_day(self, start_dt=None,
                                     end_dt=None, leaves=None,
                                     compute_leaves=False, resource_id=None,
                                     default_interval=None):
        work_limits = []
        if start_dt is None and end_dt is not None:
            start_dt = end_dt.replace(hour=0, minute=0, second=0)
        elif start_dt is None:
            start_dt = datetime.now().replace(hour=0, minute=0, second=0)
        else:
            work_limits.append((start_dt.replace(
                hour=0, minute=0, second=0), start_dt))
        if end_dt is None:
            end_dt = start_dt.replace(hour=23, minute=59, second=59)
        else:
            work_limits.append((end_dt, end_dt.replace(
                hour=23, minute=59, second=59)))
        assert start_dt.date() == end_dt.date(), \
            'get_working_intervals_of_day is restricted to one day'
        intervals = []
        work_dt = start_dt.replace(hour=0, minute=0, second=0)

        # no calendar: try to use the default_interval, then return directly
        if not self.ids:
            working_interval = []
            if default_interval:
                working_interval = (
                    start_dt.replace(hour=default_interval[0],
                                     minute=0, second=0),
                    start_dt.replace(hour=default_interval[1],
                                     minute=0, second=0))
            # intervals = self._interval_remove_leaves(working_interval, work_limits)
            date_from = start_dt.replace(hour=default_interval[0],
                                     minute=0, second=0).replace(tzinfo=pytz.UTC)
            date_to = start_dt.replace(hour=default_interval[1],
                                     minute=0, second=0).replace(tzinfo=pytz.UTC)
            intervals += self._leave_intervals(date_from, date_to)
            return intervals

        #working_intervals = []
        for calendar_working_day in self.get_attendances_for_weekdays(
                [start_dt.weekday()], start_dt,
                end_dt):

            str_time_from_dict = str(calendar_working_day.hour_from).split('.')
            hour_from = int(str_time_from_dict[0])
            if int(str_time_from_dict[1]) < 10:
                minutes_from = int(60 * int(str_time_from_dict[1]) / 10)
            elif int(str_time_from_dict[1]) > 100:
                m = str_time_from_dict[1][:2] + '.' + str_time_from_dict[1][2:]
                m = float(m)
                minutes_from = round(60 * m / 100)
            else:
                minutes_from = int(60 * int(str_time_from_dict[1]) / 100)
            str_time_to_dict = str(calendar_working_day.hour_to).split('.')
            hour_to = int(str_time_to_dict[0])
            if int(str_time_to_dict[1]) < 10:
                minutes_to = int(60 * int(str_time_to_dict[1]) / 10)
            elif int(str_time_to_dict[1]) > 100:
                m = str_time_to_dict[1][:2] + '.' + str_time_to_dict[1][2:]
                m = float(m)
                minutes_to = round(60 * m / 100)
            else:
                minutes_to = int(60 * int(str_time_to_dict[1]) / 100)

            working_interval = (
                work_dt.replace(hour=hour_from).replace(minute=minutes_from),
                work_dt.replace(hour=hour_to).replace(minute=minutes_to)
            )
            # working_intervals += self._interval_remove_leaves(working_interval, work_limits)
            intervals.append(working_interval)
            date_from = work_dt.replace(hour=hour_from).replace(minute=minutes_from).replace(tzinfo=pytz.UTC)
            date_to = work_dt.replace(hour=hour_to).replace(minute=minutes_to).replace(tzinfo=pytz.UTC)

            # working_intervals += self._leave_intervals(date_from, date_to)
        # find leave intervals
        if leaves is None and compute_leaves:
            leaves = self._get_leave_intervals(resource_id=resource_id)

        # filter according to leaves
        # for interval in working_intervals:
        #     if not leaves:
        #         leaves = []
        #     work_intervals = self._interval_remove_leaves(interval, leaves)
        #     intervals += work_intervals
        return intervals

    def get_working_hours_of_date(self, start_dt=None,
                                  end_dt=None, leaves=None,
                                  compute_leaves=None, resource_id=None,
                                  default_interval=None):
        """ Get the working hours of the day based on calendar. This method uses
        get_working_intervals_of_day to have the work intervals of the day. It
        then calculates the number of hours contained in those intervals. """
        res = dtime.timedelta()
        intervals = self.get_working_intervals_of_day(
            start_dt, end_dt, leaves,
            compute_leaves, resource_id,
            default_interval)
        for interval in intervals:
            res += interval[1] - interval[0]
        return seconds(res) / 3600.0

    def get_bonus_hours_of_date(self, start_dt=None,
                                end_dt=None, leaves=None,
                                compute_leaves=False, resource_id=None,
                                default_interval=None):
        """ Get the working hours of the day based on calendar. This method uses
        get_working_intervals_of_day to have the work intervals of the day. It
        then calculates the number of hours contained in those intervals. """
        res = dtime.timedelta()
        intervals = self.get_working_intervals_of_day(
            start_dt, end_dt, leaves,
            compute_leaves, resource_id,
            default_interval)
        for interval in intervals:
            res += interval[1] - interval[0]
        return seconds(res) / 3600.0

    def get_attendances_for_weekdays(self, weekdays, start_dt, end_dt):
        """ Given a list of weekdays, return matching
        resource.calendar.attendance"""

        res = []
        for att in self.attendance_ids:
            if int(att.dayofweek) in weekdays:
                if not att.date_from or not att.date_to:
                    res.append(att)
                else:
                    date_from = datetime.strptime(att.date_from, '%Y-%m-%d')
                    date_to = datetime.strptime(att.date_to, '%Y-%m-%d')

                    if date_from <= start_dt <= date_to:
                        res.append(att)
        return res

    use_overtime = fields.Boolean(string="Use Overtime Setting")
    min_overtime_count = fields.Integer(string="Minimum overtime days",
                                        default=0,
                                        required=True)
    count = fields.Integer(string="Percent Count",
                           default=0,
                           required=True)
    overtime_attendance_ids = fields.One2many(
        'resource.calendar.attendance.overtime',
        'overtime_calendar_id',
        string='Overtime')
    two_days_shift = fields.Boolean(string='Shift between two days',
                                    default=True,
                                    help='Use for night shift between '
                                         'two days.')

    @api.constrains('min_overtime_count')
    def _check_min_overtime_count(self):
        """Ensure that field min_overtime_count is >= 0"""
        if self.min_overtime_count < 0:
            raise ValidationError("Minimum overtime days must be positive.")

    @api.constrains('two_days_shift')
    def _check_two_days_shift(self):
        if self.two_days_shift is False:
            for attendance_id in self.overtime_attendance_ids:
                if attendance_id.hour_to <= attendance_id.hour_from:
                    raise ValidationError("Overtime to must be greater than "
                                          "overtime from when two days "
                                          "shift is not using.")

    def _get_leave_intervals(self, resource_id=None,
                             start_datetime=None, end_datetime=None):
        self.ensure_one()
        if resource_id:
            domain = ['|',
                      ('resource_id', '=', resource_id),
                      ('resource_id', '=', False)]
        else:
            domain = [('resource_id', '=', False)]
        if start_datetime:
            domain += [('date_to', '>', fields.Datetime.to_string(
                start_datetime + timedelta(days=-1)))]
        if end_datetime:
            domain += [('date_from', '<',
                        fields.Datetime.to_string(start_datetime +
                                                  timedelta(days=1)))]
        leaves = self.env['resource.calendar.leaves'].search(
            domain + [('calendar_id', '=', self.id)])

        filtered_leaves = self.env['resource.calendar.leaves']
        for leave in leaves:
            if not leave.tz:
                if self.env.context.get('tz'):
                    leave.tz = self.env.context.get('tz')
                else:
                    leave.tz = 'UTC'
            if start_datetime:
                leave_date_to = to_tz(
                    fields.Datetime.from_string(leave.date_to), leave.tz)
                if not leave_date_to >= start_datetime:
                    continue
            if end_datetime:
                leave_date_from = to_tz(
                    fields.Datetime.from_string(leave.date_from), leave.tz)
                if not leave_date_from <= end_datetime:
                    continue
            filtered_leaves += leave

        return [self._interval_new(
            to_tz(fields.Datetime.from_string(leave.date_from), leave.tz),
            to_tz(fields.Datetime.from_string(leave.date_to), leave.tz),
            {'leaves': leave}) for leave in filtered_leaves]

    def initial_overtime(self):
        contracts = self.env['hr.contract'].search(
            [('resource_calendar_id', '=', self.id)])
        employee_ids = [contract.employee_id.id for contract in contracts]
        for employee in self.env['hr.employee'].browse(set(employee_ids)):
            employee.initial_overtime()


class ResourceCalendarAttendanceOvertime(models.Model):
    _name = "resource.calendar.attendance.overtime"
    _order = 'dayofweek, hour_from'
    _description = 'ResourceCalendarAttendanceOvertime'

    name = fields.Char(required=True)
    dayofweek = fields.Selection([('0', 'Monday'),
                                  ('1', 'Tuesday'),
                                  ('2', 'Wednesday'),
                                  ('3', 'Thursday'),
                                  ('4', 'Friday'),
                                  ('5', 'Saturday'),
                                  ('6', 'Sunday')
                                  ],
                                 string='Day of Week',
                                 required=True,
                                 index=True,
                                 default='0')
    date_from = fields.Date(string='Starting Date')
    date_to = fields.Date(string='End Date')
    hour_from = fields.Float(string='Overtime from',
                             required=True,
                             index=True,
                             help="Start and End time of Overtime.")
    hour_to = fields.Float(string='Overtime to',
                           required=True)

    overtime_calendar_id = fields.Many2one("resource.calendar",
                                           string="Resource's Calendar",
                                           required=True,
                                           ondelete='cascade')


def seconds(td):
    assert isinstance(td, dtime.timedelta)

    return (td.microseconds + (
        td.seconds + td.days * 24 * 3600) * 10 ** 6) / 10. ** 6


def to_tz(datetime, tz_name):
    tz = pytz.timezone(tz_name)
    return pytz.UTC.localize(datetime.replace(tzinfo=None),
                             is_dst=False).astimezone(tz).replace(tzinfo=None)


class ResourceCalendarAttendance(models.Model):
    _inherit = "resource.calendar.attendance"

    def write(self, values):
        if 'date_from' in values.keys() or 'date_to' in values.keys():
            old_date_from = self.date_from
            old_date_to = self.date_to

            new_date_from = values.get('date_from') or self.date_from
            new_date_to = values.get('date_to') or self.date_to
            start_calc = None
            if not old_date_from or not new_date_from:
                start_calc = (datetime.now().date().replace(
                    month=1, day=1)).strftime("%Y-%m-%d")
            end_calc = None
            if not old_date_to or not new_date_to:
                end_calc = (datetime.now().date().replace(
                    month=12, day=31)).strftime("%Y-%m-%d")

            res = super(ResourceCalendarAttendance, self).write(values)
            list_of_dates = filter(None, [new_date_from, new_date_to,
                                          old_date_from, old_date_to,
                                          end_calc, start_calc])
            list_of_dates = [datetime.strptime(date, "%Y-%m-%d") for date in
                             list_of_dates]
            date_end = max(list_of_dates)
            date_start = min(list_of_dates)

            self.change_working_time(date_start, date_end)
            return res
        else:
            return super(ResourceCalendarAttendance, self).write(values)

    @api.model
    def create(self, values):
        date_start = values.get('date_from') or (
            datetime.now().date().replace(month=1, day=1)).strftime("%Y-%m-%d")
        date_end = values.get('date_to') or (
            datetime.now().date().replace(month=12, day=31)).strftime(
            "%Y-%m-%d")
        res = super(ResourceCalendarAttendance, self).create(values)
        res.change_working_time(date_start, date_end)
        return res

    def unlink(self):
        date_start = self.date_from or (
            datetime.now().date().replace(month=1, day=1)).strftime("%Y-%m-%d")
        date_end = self.date_to or (
            datetime.now().date().replace(month=12, day=31)).strftime(
            "%Y-%m-%d")
        resource_calendar_id = self.calendar_id.id
        res = super(ResourceCalendarAttendance, self).unlink()
        self.change_working_time(date_start, date_end, resource_calendar_id)
        return res

    def change_working_time(self, date_start, date_end,
                            resource_calendar_id=False):
        _logger.info(date_start)
        _logger.info(date_end)
        analytic_pool = self.env['employee.attendance.analytic']
        if not resource_calendar_id:
            resource_calendar_id = self.calendar_id.id
        contract_ids = self.env['hr.contract'].search(
            [('state', '=', 'open'),
             ('resource_calendar_id', '=', resource_calendar_id)]).ids
        lines = analytic_pool.search(
            [('contract_id', 'in', contract_ids),
             ('attendance_date', '<=', date_end),
             ('attendance_date', '>=', date_start)])
        _logger.info(len(lines))
        for line in lines:
            analytic_pool.recalculate_line(line.name)
