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

from datetime import datetime, timedelta
from openerp.osv import fields, osv, orm
from dateutil import rrule, parser
from openerp.tools.translate import _


class hr_timesheet_dh(osv.osv):
    """
        Addition plugin for HR timesheet for work with duty hours
    """
    _inherit = 'hr_timesheet_sheet.sheet'

    def _duty_hours(self, cr, uid, ids, name, args, context=None):
        res = {}
        if not context:
            context = {}
        for sheet in self.browse(cr, uid, ids, context=context or {}):
            res.setdefault(sheet.id, {
                'total_duty_hours': 0.0,
            })
            # Done BY Addition IT Solutions: BEGIN
            if sheet.state == 'done':
                res[sheet.id]['total_duty_hours'] = sheet.total_duty_hours_done
            else:
                dates = list(rrule.rrule(rrule.DAILY,
                                         dtstart=parser.parse(sheet.date_from),
                                         until=parser.parse(sheet.date_to)))
                ctx = dict(context)
                ctx.update(date_from=sheet.date_from,
                           date_to=sheet.date_to)
                for date_line in dates:
                    duty_hours = self.calculate_duty_hours(cr, uid,
                                                           sheet.employee_id.id,
                                                           date_line,
                                                           context=ctx)
                    res[sheet.id]['total_duty_hours'] += duty_hours
                res[sheet.id]['total_duty_hours'] = \
                    res[sheet.id]['total_duty_hours'] - sheet.total_attendance
                # Done BY Addition IT Solutions: END
        return res

    def count_leaves(self, cr, uid, date_from, employee_id, context=None):
        # Done BY Addition IT Solutions: BEGIN
        # First: Find all the leaves of current month
        holiday_obj = self.pool.get('hr.holidays')
        leaves = []
        start_leave_period = end_leave_period = False
        if context.get('date_from') and context.get('date_to'):
            start_leave_period = context.get('date_from')
            end_leave_period = context.get('date_to')
        holiday_ids = holiday_obj.search(
            cr, uid,
            ['|', '&',
             ('date_from', '>=', start_leave_period),
             ('date_from', '<=', end_leave_period),
             '&', ('date_to', '<=', end_leave_period),
             ('date_to', '>=', start_leave_period),
             ('employee_id', '=', employee_id),
             ('state', '=', 'validate'),
             ('type', '=', 'remove')])
        leaves = []
        # Second: If date_from and leave date matches add to list leaves
        for leave in holiday_obj.browse(cr, uid, holiday_ids, context=context):
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
                    leaves.append((leave_date_from, leave_date_to))
                    break
        # END
        return leaves

    def get_overtime(self, cr, uid, ids, start_date, context=None):
        for sheet in self.browse(cr, uid, ids, context):
            if sheet.state == 'done':
                return sheet.total_duty_hours_done * -1
            return self.calculate_diff(cr, uid, ids, start_date, context)

    def _overtime_diff(self, cr, uid, ids, name, args, context=None):
        res = {}
        for sheet in self.browse(cr, uid, ids, context):
            old_timesheet_start_from = parser.parse(
                sheet.date_from) - timedelta(days=1)
            prev_timesheet_diff = \
                self.get_previous_month_diff(
                    cr, uid,
                    sheet.employee_id.id,
                    old_timesheet_start_from.strftime('%Y-%m-%d'),
                    context=context)
            res.setdefault(sheet.id, {
                'calculate_diff_hours': self.get_overtime(
                    cr, uid, ids,
                    datetime.today().strftime('%Y-%m-%d'),
                    context) + prev_timesheet_diff,
                'prev_timesheet_diff': prev_timesheet_diff,
            })
        return res

    # Done BY Addition IT Solutions: BEGIN
    def _get_analysis(self, cr, uid, ids, name, args, context=None):
        res = {}
        for sheet in self.browse(cr, uid, ids, context=context):
            ctx = dict(context)
            ctx.update({'function_call': True})
            data = self.attendance_analysis(cr, uid, sheet.id, context=ctx)
            values = []
            output = [
                '<style>.attendanceTable td,.attendanceTable th {padding: 3px; border: 1px solid #C0C0C0; border-collapse: collapse;     text-align: right;} </style><table class="attendanceTable" >']
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
            res[sheet.id] = '\n'.join(output)
        return res

    # END

    _columns = {
        'total_duty_hours': fields.function(_duty_hours,
                                            method=True,
                                            string='Total Duty Hours',
                                            multi="_duty_hours"),
        'total_duty_hours_done': fields.float('Total Duty Hours',
                                              readonly=True,
                                              default=0.0),
        'total_diff_hours': fields.float('Total Diff Hours',
                                         readonly=True,
                                         default=0.0),
        'calculate_diff_hours': fields.function(_overtime_diff,
                                                method=True,
                                                string="Diff (worked-duty)",
                                                multi="_diff"),
        'prev_timesheet_diff': fields.function(_overtime_diff,
                                               method=True,
                                               string="Diff from old",
                                               multi="_diff"),
        'analysis': fields.function(_get_analysis,
                                    type="text",
                                    string="Attendance Analysis"),
        # To display o/p of attendance analysis method
    }

    def calculate_duty_hours(self, cr, uid, employee_id, date_from, context):
        contract_obj = self.pool.get('hr.contract')
        calendar_obj = self.pool.get('resource.calendar')
        duty_hours = 0.0
        contract_ids = contract_obj.search(cr, uid,
                                           [('employee_id', '=', employee_id),
                                            ('date_start', '<=', date_from),
                                            '|',
                                            ('date_end', '>=', date_from),
                                            ('date_end', '=', None)],
                                           context=context)

        for contract in contract_obj.browse(cr, uid, contract_ids,
                                            context=context):
            dh = calendar_obj.get_working_hours_of_date(
                cr=cr, uid=uid,
                id=contract.working_hours.id,
                start_dt=date_from,
                resource_id=employee_id,
                context=context)
            # Done BY Addition IT Solutions: BEGIN
            leaves = self.count_leaves(cr, uid, date_from, employee_id,
                                       context=context)
            if not leaves:
                duty_hours += dh
                # END
        return duty_hours

    def get_previous_month_diff(self, cr, uid, employee_id,
                                prev_timesheet_date_from, context=None):
        total_diff = 0.0
        timesheet_ids = self.search(cr, uid, [('employee_id', '=', employee_id),
                                              ('date_from', '<',
                                               prev_timesheet_date_from),
                                              # Get only previous timesheets
                                              ])
        for timesheet in self.browse(cr, uid, timesheet_ids):
            total_diff += self.get_overtime(cr, uid, [timesheet.id],
                                            start_date=prev_timesheet_date_from,
                                            context=context)
        return total_diff

    # Done BY Addition IT Solutions: BEGIN
    def _get_user_datetime_format(self, cr, uid, context=None):
        """ Get user's language & fetch date/time formats of
        that language """
        users_obj = self.pool.get('res.users')
        lang_obj = self.pool.get('res.lang')
        language = users_obj.browse(cr, uid, uid, context=context).lang
        lang_ids = lang_obj.search(cr, uid, [('code', '=', language)],
                                   context=context)
        date_format = _('%Y-%m-%d')
        time_format = _('%H:%M:%S')
        for lang in lang_obj.browse(cr, uid, lang_ids, context=context):
            date_format = lang.date_format
            time_format = lang.time_format
        return date_format, time_format

    # END

    def attendance_analysis(self, cr, uid, timesheet_id, context=None):
        attendance_obj = self.pool.get('hr.attendance')
        date_format, time_format = self._get_user_datetime_format(cr, uid,
                                                                  context)
        timesheet = self.browse(cr, uid, timesheet_id, context=context)
        employee_id = timesheet.employee_id.id
        start_date = timesheet.date_from
        end_date = timesheet.date_to
        previous_month_diff = self.get_previous_month_diff(cr, uid, employee_id,
                                                           start_date, context)
        current_month_diff = previous_month_diff
        if not context:
            context = {}
        res = {
            'previous_month_diff': previous_month_diff,
            'hours': []
        }

        # Done BY Addition IT Solutions: BEGIN
        # TS dates needed to find leaves during that period
        ctx = dict(context)
        ctx.update({'date_from': start_date,
                    'date_to': end_date
                    })
        dates = list(rrule.rrule(rrule.DAILY,
                                 dtstart=parser.parse(start_date),
                                 until=parser.parse(
                                     end_date)))
        # Removed datetime.utcnow to parse till end date
        # END
        work_current_month_diff = 0.0
        total = {'worked_hours': 0.0, 'duty_hours': 0.0,
                 'diff': current_month_diff, 'work_current_month_diff': ''}
        # total = collections.OrderedDict()
        # total['duty_hours'] = 0.0
        # total['worked_hours'] = 0.0
        # total['diff'] = current_month_diff
        for date_line in dates:

            dh = self.calculate_duty_hours(cr, uid, employee_id, date_line,
                                           context=ctx)
            worked_hours = 0.0
            # Done BY Addition IT Solutions: BEGIN
            for att in timesheet.period_ids:
                if att.name == date_line.strftime('%Y-%m-%d'):
                    worked_hours = att.total_attendance
            # END

            diff = worked_hours - dh
            current_month_diff += diff
            work_current_month_diff += diff
            if context.get('function_call', False):
                res['hours'].append({
                    _('Date'): date_line.strftime(date_format),
                    _('Duty Hours'): attendance_obj.float_time_convert(dh),
                    _('Worked Hours'): attendance_obj.float_time_convert(
                        worked_hours),
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
                    'running': self.sign_float_time_convert(current_month_diff)
                })
            total['duty_hours'] += dh
            total['worked_hours'] += worked_hours
            total['diff'] += diff
            total['work_current_month_diff'] = work_current_month_diff
            res['total'] = total
        return res

    def sign_float_time_convert(self, float_time):
        sign = '-' if float_time < 0 else ''
        attendance_obj = self.pool.get('hr.attendance')
        return sign + attendance_obj.float_time_convert(float_time)

    def write(self, cr, uid, ids, vals, context=None):
        if 'state' in vals and vals['state'] == 'done':
            vals['total_diff_hours'] = self.calculate_diff(cr, uid, ids, None,
                                                           context)
            for sheet in self.browse(cr, uid, ids, context=context):
                vals['total_duty_hours_done'] = sheet.total_duty_hours
        elif 'state' in vals and vals['state'] == 'draft':
            vals['total_diff_hours'] = 0.0
        res = super(hr_timesheet_dh, self).write(cr, uid, ids, vals,
                                                 context=context)
        return res

    def calculate_diff(self, cr, uid, ids, end_date=None, context=None):
        for sheet in self.browse(cr, uid, ids, context):
            return sheet.total_duty_hours * (-1)
