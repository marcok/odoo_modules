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

import datetime as dtime

from datetime import datetime, timedelta
from odoo import api, fields, models, _
from dateutil import rrule, parser
from odoo.tools.translate import _
import logging
_logger = logging.getLogger(__name__)


class HrTimesheetDh(models.Model):
    """
        Addition plugin for HR timesheet for work with duty hours
    """
    _inherit = 'hr_timesheet_sheet.sheet'

    @api.multi
    def _duty_hours(self):
        for sheet in self:
            sheet['total_duty_hours'] = 0.0
            if sheet.state == 'done':
                sheet['total_duty_hours'] = sheet.total_duty_hours_done
            else:
                dates = list(rrule.rrule(rrule.DAILY,
                                         dtstart=parser.parse(sheet.date_from),
                                         until=parser.parse(sheet.date_to)))
                period = {'date_from': sheet.date_from,
                          'date_to': sheet.date_to}

                model = self.env['ir.model'].search(
                    [('model', '=', 'hr.holidays.public.line')])
                if model:
                    holiday_obj = self.env['hr.holidays']
                    public_holidays = holiday_obj.search(
                        [('date_from', '>=', sheet.date_from),
                         ('date_from', '<=', sheet.date_to),
                         ('holiday_type', '=', 'public_holiday')])
                    for public_holiday in public_holidays:
                        public_holiday_date = datetime.strptime(
                            '%s' % public_holiday.date_from.split(' ')[0],
                            '%Y-%m-%d')
                        if public_holiday_date in dates:
                            dates.remove(public_holiday_date)

                for date_line in dates:
                    duty_hours = sheet.calculate_duty_hours(date_from=date_line,
                                                            period=period,
                                                            )
                    sheet['total_duty_hours'] += duty_hours
                sheet['total_duty_hours'] = (sheet.total_duty_hours -
                                             sheet.total_attendance)

    @api.multi
    def count_leaves(self, date_from, employee_id, period):
        holiday_obj = self.env['hr.holidays']
        start_leave_period = end_leave_period = False
        if period.get('date_from') and period.get('date_to'):
            start_leave_period = period.get('date_from')
            end_leave_period = period.get('date_to')
        holiday_ids = holiday_obj.search(
            ['|', '&',
             ('date_from', '>=', start_leave_period),
             ('date_from', '<=', end_leave_period),
             '&', ('date_to', '<=', end_leave_period),
             ('date_to', '>=', start_leave_period),
             ('employee_id', '=', employee_id),
             ('state', '=', 'validate'),
             ('type', '=', 'remove')])
        leaves = []
        for leave in holiday_ids:
            leave_date_from = datetime.strptime(leave.date_from,
                                                '%Y-%m-%d %H:%M:%S')
            leave_date_to = datetime.strptime(leave.date_to,
                                              '%Y-%m-%d %H:%M:%S')
            leave_dates = list(rrule.rrule(rrule.DAILY,
                                           dtstart=parser.parse(
                                               leave.date_from),
                                           until=parser.parse(leave.date_to)))
            for date in leave_dates:
                if date.strftime('%Y-%m-%d') == date_from.strftime('%Y-%m-%d'):
                    leaves.append(
                        (leave_date_from, leave_date_to, leave.number_of_days))
                    break
        return leaves

    @api.model
    def count_public_holiday(self, date_from, period):
        public_holidays = []
        models = self.env['ir.model'].search(
            [('model', '=', 'hr.holidays.public.line')])
        if models:
            holiday_obj = self.env['hr.holidays.public.line']
            public_holidays = holiday_obj.search(
                [('date', '=', date_from)])
        return public_holidays

    @api.multi
    def get_overtime(self, start_date):
        for sheet in self:
            if sheet.state == 'done':
                return sheet.total_duty_hours_done * -1
            return self.calculate_diff(start_date)

    @api.multi
    def _overtime_diff(self):
        for sheet in self:
            old_timesheet_start_from = parser.parse(
                sheet.date_from) - timedelta(days=1)
            prev_timesheet_diff = \
                self.get_previous_month_diff(
                    sheet.employee_id.id,
                    old_timesheet_start_from.strftime('%Y-%m-%d')
                )
            sheet['calculate_diff_hours'] = (
                self.get_overtime(datetime.today().strftime('%Y-%m-%d'), ) +
                prev_timesheet_diff)
            sheet['prev_timesheet_diff'] = prev_timesheet_diff

    @api.multi
    def _get_analysis(self):
        res = {}
        for sheet in self:
            function_call = True
            data = self.attendance_analysis(sheet.id, function_call)
            values = []
            output = [
                '<style>.attendanceTable td,.attendanceTable th '
                '{padding: 3px; border: 1px solid #C0C0C0; '
                'border-collapse: collapse;     '
                'text-align: right;} </style><table class="attendanceTable" >']
            for val in data.values():
                if isinstance(val, (int, float)):
                    output.append('<tr>')
                    prev_ts = _('Previous Timesheet:')
                    output.append('<th colspan="2">' + prev_ts + ' </th>')
                    output.append('<td colspan="3">' + str(val) + '</td>')
                    output.append('</tr>')
            for k, v in data.items():
                if isinstance(v, list):
                    output.append('<tr>')
                    for th in v[0].keys():
                        output.append('<th>' + th + '</th>')
                    output.append('</tr>')
                    for res in v:
                        values.append(res.values())
                    for tr in values:
                        output.append('<tr>')
                        for td in tr:
                            output.append('<td>' + td + '</td>')
                        output.append('</tr>')

                if isinstance(v, dict):
                    output.append('<tr>')
                    total_ts = _('Total:')
                    output.append('<th>' + total_ts + ' </th>')
                    for td in v.values():
                        output.append('<td>' + '%s' % round(td, 4) + '</td>')
                    output.append('</tr>')
            output.append('</table>')
            sheet['analysis'] = '\n'.join(output)

    total_duty_hours = fields.Float(compute='_duty_hours',
                                    string='Total Duty Hours',
                                    multi="_duty_hours")
    total_duty_hours_done = fields.Float(string='Total Duty Hours',
                                         readonly=True,
                                         default=0.0)
    total_diff_hours = fields.Float(string='Total Diff Hours',
                                    readonly=True,
                                    default=0.0)
    calculate_diff_hours = fields.Char(compute='_overtime_diff',
                                       string="Diff (worked-duty)",
                                       multi="_diff")
    prev_timesheet_diff = fields.Char(compute='_overtime_diff',
                                      method=True,
                                      string="Diff from old",
                                      multi="_diff")
    analysis = fields.Text(compute='_get_analysis',
                           type="text",
                           string="Attendance Analysis")

    @api.multi
    def calculate_duty_hours(self, date_from, period):
        contract_obj = self.env['hr.contract']
        calendar_obj = self.env['resource.calendar']
        duty_hours = 0.0
        contract_ids = contract_obj.search(
            [
                ('employee_id', '=', self.employee_id.id),
                ('date_start', '<=', date_from),
                '|',
                ('date_end', '>=', date_from),
                ('date_end', '=', None)
            ]
        )
        for contract in contract_ids:
            ctx = dict(self.env.context).copy()
            ctx.update(period)
            dh = calendar_obj.get_working_hours_of_date(
                cr=self._cr,
                uid=self.env.user.id,
                ids=contract.working_hours.id,
                start_dt=date_from,
                resource_id=self.employee_id.id,
                context=ctx)
            leaves = self.count_leaves(date_from, self.employee_id.id, period)
            public_holiday = self.count_public_holiday(date_from, period)
            if not leaves and not public_holiday:
                if not dh:
                    dh = 0.00
                duty_hours += dh
            elif not leaves and public_holiday:
                dh = 0.00
                duty_hours += dh
            else:
                if leaves[-1] and leaves[-1][-1]:
                    if float(leaves[-1][-1]) == (-0.5):
                        duty_hours += dh / 2

        return duty_hours

    @api.multi
    def get_previous_month_diff(self, employee_id, prev_timesheet_date_from):
        total_diff = 0.0
        timesheet_ids = self.search(
            [('employee_id', '=', employee_id),
             ('date_from', '<', prev_timesheet_date_from)
             ])
        for timesheet in timesheet_ids:
            total_diff += timesheet.get_overtime(
                start_date=prev_timesheet_date_from)
        return total_diff

    @api.multi
    def _get_user_datetime_format(self):
        """ Get user's language & fetch date/time formats of
        that language """
        lang_obj = self.env['res.lang']
        language = self.env.user.lang
        lang_ids = lang_obj.search([('code', '=', language)])
        date_format = _('%Y-%m-%d')
        time_format = _('%H:%M:%S')
        for lang in lang_ids:
            date_format = lang.date_format
            time_format = lang.time_format
        return date_format, time_format

    @api.multi
    def attendance_analysis(self, timesheet_id=None, function_call=False):
        attendance_obj = self.env['hr.attendance']
        date_format, time_format = self._get_user_datetime_format()
        for sheet in self:
            if not timesheet_id:
                timesheet_id = self[-1].id
            if sheet.id == timesheet_id:
                employee_id = sheet.employee_id.id
                start_date = sheet.date_from
                end_date = sheet.date_to
                previous_month_diff = self.get_previous_month_diff(
                    employee_id, start_date)
                current_month_diff = previous_month_diff
                res = {
                    'previous_month_diff': previous_month_diff,
                    'hours': []
                }

                period = {'date_from': start_date,
                          'date_to': end_date
                          }
                dates = list(rrule.rrule(rrule.DAILY,
                                         dtstart=parser.parse(start_date),
                                         until=parser.parse(
                                             end_date)))
                work_current_month_diff = 0.0
                total = {'worked_hours': 0.0, 'duty_hours': 0.0,
                         'diff':
                             current_month_diff, 'work_current_month_diff': ''}
                for date_line in dates:

                    dh = sheet.calculate_duty_hours(date_from=date_line,
                                                    period=period,
                                                    )
                    worked_hours = 0.0
                    for att in sheet.period_ids:
                        if att.name == date_line.strftime('%Y-%m-%d'):
                            worked_hours = att.total_attendance

                    diff = worked_hours - dh
                    current_month_diff += diff
                    work_current_month_diff += diff
                    if function_call:
                        res['hours'].append({
                            _('Date'): date_line.strftime(date_format),
                            _('Duty Hours'):
                                attendance_obj.float_time_convert(dh),
                            _('Worked Hours'):
                                attendance_obj.float_time_convert(worked_hours),
                            _('Difference'): self.sign_float_time_convert(diff),
                            _('Running'): self.sign_float_time_convert(
                                current_month_diff)})
                    else:
                        res['hours'].append({
                            'name': date_line.strftime(date_format),
                            'dh': attendance_obj.float_time_convert(dh),
                            'worked_hours': attendance_obj.float_time_convert(
                                worked_hours),
                            'diff': self.sign_float_time_convert(diff),
                            'running': self.sign_float_time_convert(
                                current_month_diff)
                        })
                    total['duty_hours'] += dh
                    total['worked_hours'] += worked_hours
                    total['diff'] += diff
                    total['work_current_month_diff'] = work_current_month_diff
                    res['total'] = total
                return res

    @api.multi
    def sign_float_time_convert(self, float_time):
        sign = '-' if float_time < 0 else ''
        attendance_obj = self.env['hr.attendance']
        # attendance_obj = self.pool.get('hr.attendance')
        return sign + attendance_obj.float_time_convert(float_time)

    @api.multi
    def write(self, vals):
        if 'state' in vals and vals['state'] == 'done':
            vals['total_diff_hours'] = self.calculate_diff(None)
            for sheet in self:
                vals['total_duty_hours_done'] = sheet.total_duty_hours
        elif 'state' in vals and vals['state'] == 'draft':
            vals['total_diff_hours'] = 0.0
        res = super(HrTimesheetDh, self).write(vals)
        return res

    @api.multi
    def calculate_diff(self, end_date=None):
        for sheet in self:
            return sheet.total_duty_hours * (-1)
