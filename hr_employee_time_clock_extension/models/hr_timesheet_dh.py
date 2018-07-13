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

from odoo import models, api, _, fields
from datetime import datetime, timedelta
from dateutil import rrule, parser
import pytz
import calendar
import logging

_logger = logging.getLogger(__name__)


class HrTimesheetDh(models.Model):
    _inherit = 'hr_timesheet_sheet.sheet'

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
                    sheet.get_overtime(
                        datetime.today().strftime('%Y-%m-%d'), ) +
                    prev_timesheet_diff)
            sheet['prev_timesheet_diff'] = prev_timesheet_diff

    def check_contract(self, employee, date_line):
        contract = self.env['hr.contract'].search([
                ('employee_id', '=', employee),
                ('date_start', '<=', date_line),
                '|',
                ('date_end', '>=', date_line),
                ('date_end', '=', False),
                ('state', '!=', 'cancel')])
        return contract

    def get_date_mark(self, date_line, period):
        date_mark = ''
        public_holidays = self.count_public_holiday(date_line, period)
        date_line_day_of_week = calendar.weekday(date_line.year,
                                                 date_line.month,
                                                 date_line.day)
        if public_holidays or date_line_day_of_week == 6:
            date_mark = '* '

        return date_mark

    def get_leave_descr(self, date_line, employee_id):
        leave_descr = ' '
        holiday_obj = self.env['hr.holidays']
        holiday_ids = holiday_obj.search([
            ('employee_id', '=', employee_id),
            ('state', '=', 'validate'),
            ('type', '=', 'remove'),
            ('date_from', '<', str(date_line + timedelta(days=1))),
            ('date_to', '>', str(date_line))])
        descr = None
        if holiday_ids:
            descr = holiday_ids.filtered(lambda holiday: holiday.name != False)
        if descr:
            leave_descr = descr[0].name
        return leave_descr

    def get_date_format(self, values):
        if values[0][0].find('* ') != -1:
            values[0][0] = values[0][0].replace('* ', '')
        splitter = '.'
        for symbol in ['-', '/', '.']:
            find_splitter = values[0][0].find(symbol)
            if find_splitter != -1:
                splitter = symbol
                break
        year = str(datetime.today().year)
        year_index_find = values[0][0].find(year)
        if year_index_find == 6:
            year_index = 2
            find_month_index = [0, 1]
        else:
            year_index = 0
            find_month_index = [1, 2]
        month_index = 0
        for i in range(len(values) - 1):
            if values[i][0].find('* ') != -1:
                values[i][0] = values[i][0].replace('* ', '')
            if values[i + 1][0].find('* ') != -1:
                values[i + 1][0] = values[i + 1][0].replace('* ', '')
            value_lst_1 = values[i][0].split(splitter)
            value_lst_2 = values[i + 1][0].split(splitter)
            if value_lst_1[find_month_index[0]] == value_lst_2[
                                                        find_month_index[0]]:
                month_index = find_month_index[0]
                break
            if value_lst_1[find_month_index[1]] == value_lst_2[
                                                        find_month_index[1]]:
                month_index = find_month_index[1]
                break

        indexes = [0, 1, 2]
        for number in [month_index, year_index]:
            indexes.remove(number)
        day_index = indexes[0]
        format_unsorted = {day_index: 'd', month_index: 'm', year_index: 'Y'}
        date_format = '%' + format_unsorted.get(0) + splitter + '%'\
                      + format_unsorted.get(1) + splitter + '%' \
                      + format_unsorted.get(2)

        return date_format

    @api.multi
    def attendance_analysis(self, timesheet_id=None, function_call=False):
        attendance_obj = self.env['hr.attendance']
        date_format, time_format = self._get_user_datetime_format()
        if not self.env.context.get('online_analysis') \
                and date_format != '%m/%d/%Y':
            date_format = '%m/%d/%Y'
        for sheet in self.sudo():
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
                                         until=parser.parse(end_date)))
                work_current_month_diff = 0.0
                total = {'worked_hours': 0.0, 'duty_hours': 0.0,
                         'diff': current_month_diff,
                         'work_current_month_diff': '',
                         'bonus_hours': 0.0,
                         'night_shift': 0.0,
                         'leaves_descr': ''}
                for date_line in dates:
                    dh = sheet.calculate_duty_hours(date_from=date_line,
                                                    period=period)

                    worked_hours = 0.0
                    bonus_hours = 0.0
                    night_shift_hours = 0.0
                    for att in sheet.attendances_ids:
                        user_tz = pytz.timezone(
                            att.employee_id.user_id.tz or 'UTC')
                        att_name = fields.Datetime.from_string(att.name).replace(
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

                    diff = (worked_hours + bonus_hours) - dh
                    current_month_diff += diff
                    work_current_month_diff += diff
                    date_mark = sheet.get_date_mark(date_line, period)
                    leave_descr = sheet.get_leave_descr(date_line, employee_id)
                    if function_call:
                        res['hours'].append({
                            _('Date'): date_mark + date_line.strftime(date_format),
                            _('Duty Hours'):
                                attendance_obj.float_time_convert(dh),
                            _('Worked Hours'):
                                attendance_obj.float_time_convert(worked_hours),
                            _('Bonus Hours'):
                                attendance_obj.float_time_convert(bonus_hours),
                            _('Night Shift'):
                                attendance_obj.float_time_convert(
                                    night_shift_hours),
                            _('Difference'): self.sign_float_time_convert(diff),
                            _('Running'): self.sign_float_time_convert(
                                current_month_diff),
                            _('Leaves'): leave_descr})
                    else:
                        res['hours'].append({
                            'name': date_line.strftime(date_format),
                            'dh': attendance_obj.float_time_convert(dh),
                            'worked_hours':
                                attendance_obj.float_time_convert(worked_hours),
                            'bonus_hours':
                                attendance_obj.float_time_convert(bonus_hours),
                            'night_shift':
                                attendance_obj.float_time_convert(
                                    night_shift_hours),
                            'diff': self.sign_float_time_convert(diff),
                            'running':
                                self.sign_float_time_convert(current_month_diff),
                            'leaves_descr': leave_descr
                        })
                    total['duty_hours'] += dh
                    total['worked_hours'] += worked_hours
                    total['bonus_hours'] += bonus_hours
                    total['night_shift'] += night_shift_hours
                    total['leaves_descr'] = ''
                    total['diff'] += diff
                    total['work_current_month_diff'] = work_current_month_diff

                    res['total'] = total
                return res

    @api.multi
    def _get_analysis(self):
        for sheet in self:
            function_call = True
            ctx = self.env.context.copy()
            ctx['online_analysis'] = True
            data = self.with_context(ctx).attendance_analysis(
                timesheet_id=sheet.id, function_call=function_call)
            values = []
            output = [
                '<style>.attendanceTable td,.attendanceTable th '
                '{padding: 3px; border: 1px solid #C0C0C0; '
                'border-collapse: collapse;     '
                'text-align: right;} '
                '.attendanceTable {border: 1px solid #C0C0C0;}</style><table class="attendanceTable">']
            for val in data.values():
                if isinstance(val, (int, float)):
                    t = '{0:02.0f}:{1:02.0f}'.format(
                        *divmod(float(val) * 60, 60))
                    if val < 0:
                        t = '-{0:02.0f}:{1:02.0f}'.format(
                            *divmod(float(val) * -60, 60))

                    output.append('<tr>')
                    prev_ts = _('Previous Attendance Sheet:')
                    output.append('<th colspan="2">' + prev_ts + ' </th>')
                    output.append('<td colspan="6">' + t + '</td>')
                    output.append('</tr>')
            keys = (_('Date'), _('Duty Hours'), _('Worked Hours'),
                    _('Bonus Hours'), _('Night Shift'),
                    _('Difference'), _('Running'), _('Leaves'))
            a = ('previous_month_diff', 'hours', 'total')
            for k in a:
                v = data.get(k)
                if isinstance(v, list):
                    output.append('<tr>')

                    for th in keys:
                        output.append('<th style="text-align: center;">' + th +
                                      '</th>')
                    output.append('</tr>')
                    for res in v:
                        values.append([res.get(key) for key in keys])
                    date_format = self.get_date_format(values)
                    for tr in values:
                        formatted_tr = tr[0]
                        if formatted_tr.find('* ') != -1:
                            formatted_tr = formatted_tr.replace('* ', '')
                        sheet_day = datetime.strptime(formatted_tr, date_format).date()
                        if datetime.today().date() == sheet_day:
                            output.append(
                                '<tr style="background-color:#bdde9f96;">')
                        else:
                            output.append('<tr>')
                        for td in tr:
                            if not td:
                                td = '-'
                            if td == tr[-1]:
                                output.append(
                                    '<td style="text-align: center;">' + td +
                                    '</td>')
                            else:
                                output.append(
                                    '<td>' + td + '</td>')
                        output.append('</tr>')

                if isinstance(v, dict):
                    output.append('<tr>')
                    total_ts = _('Total:')
                    output.append('<th>' + total_ts + ' </th>')
                    for td in ('duty_hours', 'worked_hours', 'bonus_hours',
                               'night_shift',
                               'work_current_month_diff',
                               'diff',
                               'leaves_descr'):
                        if type(v.get(td)) in [float, int]:
                            t = '{0:02.0f}:{1:02.0f}'.format(
                                *divmod(float(round(v.get(td), 4)) * 60, 60))
                            if float(v.get(td)) < 0.0:
                                t = '-{0:02.0f}:{1:02.0f}'.format(
                                    *divmod(float(round(v.get(td), 4)) * -60, 60))
                        else:
                            t = v.get(td)

                        output.append(
                            '<td>' + '%s' % t + '</td>')
                    output.append('</tr>')
            output.append('</table>')
            sheet['analysis'] = '\n'.join(output)
