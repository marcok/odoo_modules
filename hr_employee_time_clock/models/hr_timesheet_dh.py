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


import pytz
from datetime import datetime, timedelta, date
from odoo import api, fields, models, _
from dateutil import rrule, parser
from odoo.tools.translate import _
import calendar
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

                try:
                    model = self.env['ir.model'].search(
                        [('model', '=', 'hr.holidays.public.line')])
                except:
                    model = None
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
                                                            period=period)
                    sheet['total_duty_hours'] += duty_hours
                sheet['total_duty_hours'] = (sheet.total_duty_hours -
                                             sheet.total_attendance)

    @api.multi
    def take_holiday_status(self):
        return self.env['hr.holidays.status'].search(
            [('take_into_attendance', '=', True)])

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
             ('type', '=', 'remove'),
             ('holiday_status_id', 'in', self.take_holiday_status().ids)])
        leaves = []
        for leave in holiday_ids:
            leave_date_from = datetime.strptime(leave.date_from,
                                                '%Y-%m-%d %H:%M:%S')
            leave_date_to = datetime.strptime(leave.date_to,
                                              '%Y-%m-%d %H:%M:%S')
            leave_dates = list(rrule.rrule(rrule.DAILY,
                                           dtstart=parser.parse(
                                               leave.date_from),
                                           until=parser.parse(
                                               leave.date_to)))
            for date in leave_dates:
                if date.strftime('%Y-%m-%d') == date_from.strftime('%Y-%m-%d'):
                    leaves.append((leave_date_from, leave_date_to,
                                   leave.number_of_days))
                    break
        return leaves

    @api.model
    def count_public_holiday(self, date_from, period):
        public_holidays = []
        model = self.env['ir.model'].search(
            [('model', '=', 'hr.holidays.public.line')])
        if model:
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
                sheet.get_previous_month_diff(
                    sheet.employee_id.id,
                    old_timesheet_start_from.strftime('%Y-%m-%d')
                )
            sheet['calculate_diff_hours'] = (
                    self.get_overtime(datetime.today().strftime('%Y-%m-%d'), ) +
                    prev_timesheet_diff)
            sheet['prev_timesheet_diff'] = prev_timesheet_diff

    @api.multi
    def _overtime_diff(self):
        for sheet in self:
            old_timesheet_start_from = parser.parse(
                sheet.date_from) - timedelta(days=1)
            prev_timesheet_diff = \
                sheet.get_previous_month_diff(
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


    @api.multi
    def _get_analysis(self):
        for sheet in self:
            contract = self.check_contract(sheet.employee_id.id,
                                           sheet.date_from)
            if contract:
                resource_calendar_id = contract.resource_calendar_id
            else:
                resource_calendar_id = self.employee_id.resource_calendar_id

            use_overtime = resource_calendar_id.use_overtime

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
                '.attendanceTable {border: 1px solid #C0C0C0;}</style>'
                '<table class="attendanceTable">']
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
                    if use_overtime:
                        output.append('<td colspan="6">' + t + '</td>')
                    else:
                        output.append('<td colspan="4">' + t + '</td>')
                    output.append('</tr>')

            keys = (_('Date'), _('Duty Hours'), _('Worked Hours'),
                    _('Difference'), _('Running'))
            if use_overtime:
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
                    date_format, time_format = \
                        self._get_user_datetime_format()
                    for tr in values:
                        formatted_tr = tr[0]
                        formatted_tr = formatted_tr.replace('* ', '')
                        sheet_day = datetime.strptime(
                            formatted_tr, date_format).date()
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
                    if use_overtime:
                        analysis_fields = (
                            'duty_hours', 'worked_hours', 'bonus_hours',
                            'night_shift', 'work_current_month_diff',
                            'diff', 'leaves_descr')
                    else:
                        analysis_fields = (
                            'duty_hours', 'worked_hours',
                            'work_current_month_diff',
                            'diff')

                    for td in analysis_fields:
                        if type(v.get(td)) in [float, int]:
                            t = '{0:02.0f}:{1:02.0f}'.format(
                                *divmod(float(round(v.get(td), 4)) * 60, 60))
                            if float(v.get(td)) < 0.0:
                                t = '-{0:02.0f}:{1:02.0f}'.format(
                                    *divmod(float(round(v.get(td), 4)) * -60,
                                            60))
                        else:
                            t = v.get(td)

                        output.append(
                            '<td>' + '%s' % t + '</td>')
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
    calculate_diff_hours = fields.Float(compute='_overtime_diff',
                                       string="Diff (worked-duty)",
                                       multi="_diff")
    prev_timesheet_diff = fields.Float(compute='_overtime_diff',
                                       method=True,
                                       string="Diff from old",
                                       multi="_diff")
    analysis = fields.Text(compute='_get_analysis',
                           type="text",
                           string="Attendance Analysis")

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None,
                    order=None):
        if 'search_default_to_approve' in self.env.context.keys():
            if self.user_has_groups(
                    'hr_employee_time_clock.group_timesheet_supervisor'):
                pass
            elif self.user_has_groups('hr_timesheet.group_timesheet_manager'):
                domain.append(
                    ['employee_id.parent_id.user_id', '=', self.env.uid])
            elif self.user_has_groups(
                    'hr_timesheet.group_hr_timesheet_user'):
                domain.append(['employee_id.user_id', '=', self.env.uid])
        res = super(HrTimesheetDh, self.sudo()).search_read(
            domain=domain, fields=fields, offset=offset, limit=limit,
            order=order)
        _logger.info(res)
        return res

    @api.multi
    def calculate_duty_hours(self, date_from, period):
        contract_obj = self.env['hr.contract']
        calendar_obj = self.env['resource.calendar']
        duty_hours = 0.0
        contract_ids = contract_obj.search(
            [('employee_id', '=', self.employee_id.id),
             ('date_start', '<=', date_from), '|',
             ('date_end', '>=', date_from),
             ('date_end', '=', None)])
        for contract in contract_ids:
            ctx = dict(self.env.context).copy()
            ctx.update(period)
            dh = calendar_obj.get_working_hours_of_date(
                cr=self._cr,
                uid=self.env.user.id,
                ids=contract.resource_calendar_id.id,
                start_dt=date_from,
                resource_id=self.employee_id.id,
                context=ctx)
            leaves = self.count_leaves(date_from, self.employee_id.id, period)
            public_holiday = self.count_public_holiday(date_from, period)
            if contract.state != 'cancel':
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
            else:
                dh = 0.00
                duty_hours += dh

        return duty_hours

    @api.multi
    def get_previous_month_diff(self, employee_id, prev_timesheet_date_from):
        total_diff = self.env['hr.employee'].browse(
            employee_id).start_time_different
        prev_timesheet_ids = self.search(
            [('employee_id', '=', employee_id)
             ]).filtered(lambda sheet: sheet.date_to < self.date_from).sorted(
            key=lambda v: v.date_from)
        if prev_timesheet_ids:
            total_diff = prev_timesheet_ids[-1].calculate_diff_hours
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

                contract = self.check_contract(employee_id, start_date)
                if contract:
                    resource_calendar_id = contract.resource_calendar_id
                else:
                    resource_calendar_id = self.employee_id.resource_calendar_id

                use_overtime = resource_calendar_id.use_overtime

                previous_month_diff = sheet.get_previous_month_diff(
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
                         }
                if use_overtime:
                    total.update({'bonus_hours': 0.0,
                                  'night_shift': 0.0,
                                  'leaves_descr': ''})

                last_date = dates[-1]
                today_worked_hours = 0.0
                today_diff = 0
                today_current_month_diff = 0

                for date_line in dates:
                    dh = sheet.calculate_duty_hours(date_from=date_line,
                                                    period=period)

                    worked_hours = 0.0
                    bonus_hours = 0.0
                    night_shift_hours = 0.0
                    for att in sheet.attendances_ids:
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
                        today_worked_hours = worked_hours
                        today_diff = diff
                        today_current_month_diff = current_month_diff
                    if date_line == last_date:
                        if not self.env.context.get('online_analysis'):
                            worked_hours = today_worked_hours
                            diff = today_diff
                            current_month_diff = work_current_month_diff
                    if date_line == last_date:
                        if not self.env.context.get('online_analysis'):
                            worked_hours = today_worked_hours
                            diff = today_diff
                            current_month_diff = today_current_month_diff

                    date_mark = sheet.get_date_mark(date_line, period)
                    leave_descr = sheet.get_leave_descr(date_line, employee_id)
                    if function_call:
                        if use_overtime:
                            res['hours'].append({
                                _('Date'): date_mark + date_line.strftime(
                                    date_format),
                                _('Duty Hours'):
                                    attendance_obj.float_time_convert(dh),
                                _('Worked Hours'):
                                    attendance_obj.float_time_convert(
                                        worked_hours),
                                _('Bonus Hours'):
                                    attendance_obj.float_time_convert(
                                        bonus_hours),
                                _('Night Shift'):
                                    attendance_obj.float_time_convert(
                                        night_shift_hours),
                                _('Difference'): self.sign_float_time_convert(
                                    diff),
                                _('Running'): self.sign_float_time_convert(
                                    current_month_diff),
                                _('Leaves'): leave_descr})
                        else:
                            res['hours'].append({
                                _('Date'): date_mark + date_line.strftime(
                                    date_format),
                                _('Duty Hours'):
                                    attendance_obj.float_time_convert(dh),
                                _('Worked Hours'):
                                    attendance_obj.float_time_convert(
                                        worked_hours),
                                _('Difference'): self.sign_float_time_convert(
                                    diff),
                                _('Running'): self.sign_float_time_convert(
                                    current_month_diff)})
                    else:
                        if use_overtime:
                            res['hours'].append({
                                'name': date_line.strftime(date_format),
                                'dh': attendance_obj.float_time_convert(dh),
                                'worked_hours':
                                    attendance_obj.float_time_convert(
                                        worked_hours),
                                'bonus_hours':
                                    attendance_obj.float_time_convert(
                                        bonus_hours),
                                'night_shift':
                                    attendance_obj.float_time_convert(
                                        night_shift_hours),
                                'diff': self.sign_float_time_convert(diff),
                                'running':
                                    self.sign_float_time_convert(
                                        current_month_diff),
                                'leaves_descr': leave_descr
                            })
                        else:
                            res['hours'].append({
                                'name': date_line.strftime(date_format),
                                'dh': attendance_obj.float_time_convert(dh),
                                'worked_hours':
                                    attendance_obj.float_time_convert(
                                        worked_hours),
                                'diff': self.sign_float_time_convert(diff),
                                'running':
                                    self.sign_float_time_convert(
                                        current_month_diff),
                            })
                    total['duty_hours'] += dh
                    total['worked_hours'] += worked_hours

                    total['diff'] += diff
                    total['work_current_month_diff'] = work_current_month_diff
                    if use_overtime:
                        total['bonus_hours'] += bonus_hours
                        total['night_shift'] += night_shift_hours
                        total['leaves_descr'] = ''

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

    @api.multi
    def hr_attendance_employee_action(self):
        ctx = {'default_employee_id': self.employee_id.id}

        def ref(module, xml_id):
            proxy = self.env['ir.model.data']
            return proxy.get_object_reference(module, xml_id)

        model, search_view_id = ref('hr_attendance',
                                    'hr_attendance_view_filter')

        return {
            'name': 'Attendances',
            'view_type': 'form',
            'view_mode': 'tree,kanban,form',
            'target': 'current',
            'res_model': 'hr.attendance',
            'type': 'ir.actions.act_window',
            'domain': [('employee_id', '=', self.employee_id.id)],
            'context': ctx,
            'help': _('''<p>The attendance records of your employees will be displayed here.</p>
            <p>Please make sure you're using the correct filter if you expected to see any.</p>'''),
            'search_view_id': search_view_id,
        }
