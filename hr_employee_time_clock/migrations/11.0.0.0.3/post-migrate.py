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

from odoo import api, fields, models, SUPERUSER_ID, _
from dateutil import rrule, parser
import pytz
from datetime import datetime, date, timedelta
import calendar
import math

def migrate(cr, version):
    """
    This migration is made to calculate running time for each active employee and
    write it into last attendance, which has check out. It is important to
    companies that already use Employee Time Clock module.
    """
    cr.execute(
        """UPDATE hr_attendance  SET running = 0.0""")
    env = api.Environment(cr, SUPERUSER_ID, {})

    employee_ids = env['hr.employee'].search([('active', '=', True)])
    for employee_id in employee_ids:
        current_timesheet_id = env['hr_timesheet_sheet.sheet'].search([
            ('employee_id', '=', employee_id.id)], limit=1).sorted(
            key=lambda v: v.date_from)

        if current_timesheet_id:
            start_date = current_timesheet_id.date_from
            end_date = current_timesheet_id.date_to

            contract = env['hr.contract'].search([
                ('employee_id', '=', employee_id.id),
                ('date_start', '<=', current_timesheet_id.date_from),
                '|',
                ('date_end', '>=', current_timesheet_id.date_from),
                ('date_end', '=', False),
                ('state', '!=', 'cancel')])

            if contract:
                resource_calendar_id = contract.resource_calendar_id
            else:
                resource_calendar_id = employee_id.resource_calendar_id

            use_overtime = resource_calendar_id.use_overtime

            previous_month_diff = get_previous_month_diff(cr, employee_id,
                                                          current_timesheet_id)

            current_month_diff = previous_month_diff
            period = {'date_from': start_date,
                      'date_to': end_date
                      }
            dates = list(rrule.rrule(rrule.DAILY,
                                     dtstart=parser.parse(start_date),
                                     until=parser.parse(end_date)))
            work_current_month_diff = 0.0

            for date_line in dates:
                dh = calculate_duty_hours(cr,date_line, period, employee_id)

                worked_hours = 0.0
                bonus_hours = 0.0
                night_shift_hours = 0.0
                for att in current_timesheet_id.attendances_ids:
                    user_tz = pytz.timezone(
                        att.employee_id.user_id.tz or 'UTC')
                    att_name = fields.Datetime.from_string(
                        att.name).replace(
                        tzinfo=pytz.utc).astimezone(user_tz)
                    name = att_name.replace(tzinfo=None)
                    if name.strftime('%Y-%m-%d') == \
                            date_line.strftime('%Y-%m-%d'):
                        worked_hours += att.worked_hours
                        if not att.check_out:
                            tz = pytz.timezone('UTC')
                            t = datetime.now(tz=tz)
                            d = t - att_name
                            worked_hours += (d.total_seconds() / 3600)
                        if att.overtime_change:
                            bonus_hours += att.bonus_worked_hours
                            night_shift_hours += \
                                att.night_shift_worked_hours
                if use_overtime:
                    diff = (worked_hours + bonus_hours) - dh
                else:
                    diff = worked_hours - dh
                current_month_diff += diff
                work_current_month_diff += diff

                if date_line.date() == date.today():
                    today_current_month_diff = current_month_diff
                    last_attendance = env['hr.attendance'].search([
                        ('employee_id', '=', employee_id.id),
                        ('check_out', '!=', False)], limit=1).sorted(
                        key=lambda v: v.check_out)

                    if last_attendance:
                        last_attendance.write({
                            'running': today_current_month_diff,
                        })
                        break


def get_previous_month_diff(cr, employee_id, current_timesheet_id):
    """
    Calculates total hours of previous timesheet.
    :param employee_id: hr.employee object
    :param current_timesheet_id: hr_timesheet_sheet.sheet object
    :return: float
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    total_diff = employee_id.start_time_different
    prev_timesheet_ids = env['hr_timesheet_sheet.sheet'].search(
        [('employee_id', '=', employee_id.id)
         ]).filtered(
        lambda sheet: sheet.date_to < current_timesheet_id.date_from).sorted(
        key=lambda v: v.date_from)
    if prev_timesheet_ids:
        total_diff = prev_timesheet_ids[-1].calculate_diff_hours
    return total_diff

def calculate_duty_hours(cr, date_from, period, employee_id):
    """
    Calculates duty hours for employee on current date.
    :param date_from: datetime string
    :param period: {'date_from': hr_timesheet_sheet.sheet date_from,
                  'date_to': hr_timesheet_sheet.sheet date_to
                  }
    :param employee_id: hr.employee object
    :return: float
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    contract_obj = env['hr.contract']
    calendar_obj = env['resource.calendar']
    duty_hours = 0.0
    contract_ids = contract_obj.search(
        [('employee_id', '=', employee_id.id),
         ('date_start', '<=', date_from), '|',
         ('date_end', '>=', date_from),
         ('date_end', '=', None)])
    for contract in contract_ids:
        ctx = dict(env.context).copy()
        ctx.update(period)
        dh = calendar_obj.get_working_hours_of_date(
            cr=cr,
            uid=env.user.id,
            ids=contract.resource_calendar_id.id,
            start_dt=date_from,
            resource_id=employee_id.id,
            context=ctx)
        leave = count_leaves(cr, date_from, employee_id.id)
        public_holiday = count_public_holiday(cr, date_from)
        if contract.state != 'cancel':
            if leave[1] == 0 and not public_holiday:
                if not dh:
                    dh = 0.00
                duty_hours += dh
            elif public_holiday:
                dh = 0.00
                duty_hours += dh
            else:
                if not public_holiday and leave[1] != 0:
                    duty_hours += dh * (1 - leave[1])
        else:
            dh = 0.00
            duty_hours += dh
    return duty_hours


def take_holiday_status(cr):
    """
    Takes holiday types, which must change duty hours.
    :return: hr.holidays.status objects
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    holiday_status_ids = env['hr.holidays.status'].search(
        [('take_into_attendance', '=', True)])
    return holiday_status_ids


def count_leaves(cr, date_line, employee_id):
    """
    Checks if employee has any leave on current date.
    :param date_line: datetime
    :param employee_id: hr.employee object's id
    :return: list [hr.holidays objects, float]
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    holiday_obj = env['hr.holidays']
    holiday_ids = holiday_obj.search([
        ('employee_id', '=', employee_id),
        ('state', '=', 'validate'),
        ('type', '=', 'remove'),
        ('holiday_status_id', 'in', take_holiday_status(cr).ids),
        ('date_from', '<', str(date_line + timedelta(days=1))),
        ('date_to', '>', str(date_line))])
    number_of_days = 0
    if holiday_ids:
        for holiday_id in holiday_ids:
            date_from = fields.Datetime.from_string(holiday_id.date_from)
            date_to = fields.Datetime.from_string(holiday_id.date_to)

            contracts = env['hr.contract'].search([
                ('employee_id', '=', employee_id),
                ('date_start', '<=', holiday_id.date_from),
                ('state', '!=', 'cancel')])
            if contracts:
                contract = contracts[-1]
                day_of_week = calendar.weekday(date_line.year,
                                               date_line.month,
                                               date_line.day)
                calendar_attendance_ids = \
                    env['resource.calendar.attendance'].search([
                        ('calendar_id', '=',
                         contract.resource_calendar_id.id),
                        ('dayofweek', '=', day_of_week)])

                default_duty_hours = 0
                real_duty_hours = 0
                if calendar_attendance_ids:
                    for calendar_attendance_id in calendar_attendance_ids:
                        default_duty_hours += \
                            calendar_attendance_id.hour_to - \
                            calendar_attendance_id.hour_from
                        temp_duty_hours = calendar_attendance_id.hour_to - \
                                          calendar_attendance_id.hour_from

                        default_date_from = get_timezone_time(
                            cr, calendar_attendance_id.hour_from, date_line)

                        default_date_to = get_timezone_time(
                            cr, calendar_attendance_id.hour_to, date_line)
                        date_from_calc = default_date_from
                        date_to_calc = default_date_to

                        if date_line.date() == date_from.date():
                            if date_from.time() > default_date_from.time():
                                date_from_calc = default_date_from.replace(
                                    hour=date_from.hour,
                                    minute=date_from.minute,
                                    second=date_from.second)

                        if date_line.date() == date_to.date():
                            if date_to.time() < default_date_to.time():
                                date_to_calc = default_date_to.replace(
                                    hour=date_to.hour,
                                    minute=date_to.minute,
                                    second=date_to.second)
                        if date_to_calc < date_from_calc:
                            date_from_calc = date_to_calc
                        real_duty_hours += \
                            (date_to_calc - date_from_calc) \
                            / timedelta(days=temp_duty_hours / 24) \
                            * temp_duty_hours
                    number_of_days += real_duty_hours / default_duty_hours

    return [holiday_ids, number_of_days]


def count_public_holiday(cr, date_from):
    """
    Checks if there is any public holiday on current date.
    :param date_from: datetime string
    :return: hr.holidays.public.line objects
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    public_holidays = []
    model = env['ir.model'].search(
        [('model', '=', 'hr.holidays.public.line')])
    if model:
        holiday_obj = env['hr.holidays.public.line']
        public_holidays = holiday_obj.search(
            [('date', '=', date_from)])
    return public_holidays


def get_timezone_time(cr, time_without_tz, date_line):
    """
    Is used to transform hours/minutes, wrote in database in int/float type, into
    datetime object without timezone info. For example 8.5 -> 2018-08-28 05:30:00
    (including user timezone).
    :param time_without_tz: float
    :return: datetime
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    fl_part, int_part = math.modf(time_without_tz)
    local_tz = pytz.timezone(env.user.tz or 'UTC')
    default_date_without_tzinfo = datetime.combine(
        date_line.date(), datetime.strptime(
            str(int(int_part)) + ':' + str(int(fl_part * 60)) +
            ':00', '%H:%M:%S').time())
    default_date = local_tz.localize(
        default_date_without_tzinfo).astimezone(
        pytz.utc)
    default_date = default_date.replace(
        tzinfo=None)
    return default_date
