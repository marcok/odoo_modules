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

from datetime import datetime, date
from odoo import api, fields, models, _
import logging
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from dateutil import rrule, parser
from odoo.exceptions import UserError, ValidationError, AccessError
import pytz

_logger = logging.getLogger(__name__)


class EmployeeAttendanceAnalytic(models.Model):
    _name = "employee.attendance.analytic"
    _order = "name"
    _description = 'EmployeeAttendanceAnalytic'

    name = fields.Date(string='Date')
    attendance_date = fields.Date(string='Attendance Date')
    sheet_id = fields.Many2one('hr_timesheet_sheet.sheet',
                               string='Sheet',
                               index=True)
    attendance_ids = fields.One2many('hr.attendance',
                                      'line_analytic_id',
                                      string='Attendance IDS')
    contract_id = fields.Many2one('hr.contract',
                                  string='Contract')
    duty_hours = fields.Float(string='Duty Hours',
                              default=0.0)
    worked_hours = fields.Float(string='Worked Hours',
                                default=0.0)
    bonus_worked_hours = fields.Float(string='Bonus Worked Hours',
                                      default=0.0)
    night_shift_worked_hours = fields.Float(string='Night Shift',
                                            default=0.0)
    difference = fields.Float(compute='_get_difference',
                              string='Difference',
                              default=0.0)
    running = fields.Float(string='Running',
                           default=0.0)
    leave_description = fields.Char(string='Leave Description',
                                    default='-', )

    state = fields.Selection([('new', 'New'),
                              ('done', 'Approved')],
                             default='new',
                             string='Status',
                             required=True,
                             readonly=True,
                             )

    @api.multi
    def recalculate_line(self, line_date, employee_id=None):
        if employee_id:
            lines = self.search([('name', '=', line_date),
                                 ('sheet_id.employee_id', '=', employee_id.id)])
            date_line = line_date
        else:
            lines = self.search([('name', '=', line_date)])
            date_line = list(rrule.rrule(rrule.DAILY,
                                         dtstart=parser.parse(line_date),
                                         until=parser.parse(line_date)))[0]
        for line in lines:
            if line.sheet_id:
                duty_hours, contract, leave, public_holiday = \
                    self.calculate_duty_hours(sheet=line.sheet_id,
                                              date_from=date_line)
                values = {'duty_hours': duty_hours,
                          'contract_id': False,
                          'state':
                              'new' if line.sheet_id.state != 'done' else 'done',
                          'leave_description': '-'}
                if contract:
                    values.update(contract_id=contract.id)
                if public_holiday:
                    values.update(leave_description=public_holiday.name)
                if leave and leave[0]:
                    leaves = leave[0]
                    if len(leaves) > 1:
                        l = leaves[0]
                    else:
                        l = leave[0]
                    values.update(leave_description=l.name)
                line.write(values)

    @api.multi
    def _get_difference(self):
        for line in self:
            line.difference = line.worked_hours - line.duty_hours

    @api.multi
    def unlink_attendance(self, attend=False):
        worked_hours = 0
        bonus_worked_hours = 0
        night_shift_worked_hours = 0
        if attend:
            for attendance in self.attendance_ids:
                if attend != attendance:
                    bonus_worked_hours += attendance.bonus_worked_hours
                    night_shift_worked_hours \
                        += attendance.night_shift_worked_hours
                    worked_hours += attendance.worked_hours
        else:
            for attendance in self.attendance_ids:
                bonus_worked_hours += attendance.bonus_worked_hours
                night_shift_worked_hours \
                    += attendance.night_shift_worked_hours
                worked_hours += attendance.worked_hours
        self.write({
            'worked_hours': worked_hours,
            'bonus_worked_hours': bonus_worked_hours,
            'night_shift_worked_hours': night_shift_worked_hours,
        })

    @api.multi
    def recalculate_line_worktime(self, new_attendance, values):
        if values.get('check_in') or values.get('check_out'):
            line_new = False
            if values.get('check_in'):
                value_check_in = str(values.get('check_in')).split(' ')[0]

                user_tz = pytz.timezone(
                    new_attendance.employee_id.user_id.tz or 'UTC')
                local_date = fields.Datetime.from_string(
                    value_check_in).replace(
                    tzinfo=pytz.utc).astimezone(user_tz)
                local_value_check_in = local_date.replace(tzinfo=None)

                attendance_check_in = str(new_attendance.check_in).split(' ')[0]

                user_tz = pytz.timezone(
                    new_attendance.employee_id.user_id.tz or 'UTC')
                local_date = fields.Datetime.from_string(
                    attendance_check_in).replace(tzinfo=pytz.utc).astimezone(
                    user_tz)
                local_attendance_check_in = local_date.replace(tzinfo=None)
                if local_value_check_in != local_attendance_check_in:
                    line_new = self.search(
                        [('name', '=', local_value_check_in),
                         ('sheet_id', '=', new_attendance.sheet_id.id)])
                    new_attendance.line_analytic_id = line_new.id

                    line = self.search(
                        [('name', '=', local_attendance_check_in),
                         ('sheet_id', '=', new_attendance.sheet_id.id)])

                    line.unlink_attendance(new_attendance)

            check_in = values.get('check_in') or new_attendance.check_in
            check_out = values.get('check_out') or new_attendance.check_out

            user_tz = pytz.timezone(
                new_attendance.employee_id.user_id.tz or 'UTC')
            local_date = fields.Datetime.from_string(check_in).replace(
                tzinfo=pytz.utc).astimezone(user_tz)
            local_check_in = local_date.replace(tzinfo=None)

            name = str(local_check_in).split(' ')[0]
            if not line_new:
                line = self.search([('name', '=', name),
                                    ('sheet_id', '=',
                                     new_attendance.sheet_id.id)])
            else:
                line = line_new
            time1 = '{} 00:00:00'.format(name)
            duty_hours = new_attendance.sheet_id.calculate_duty_hours(
                time1,
                {'date_to': str(new_attendance.sheet_id.date_to),
                 'date_from': str(new_attendance.sheet_id.date_from), })
            if not line:
                line = self.create({'name': name,
                                    'sheet_id': new_attendance.sheet_id.id,
                                    'duty_hours': duty_hours})
                new_attendance.line_analytic_id = line.id
            else:
                if not new_attendance.line_analytic_id:
                    new_attendance.line_analytic_id = line.id
            if check_out:
                worked_hours = 0
                bonus_worked_hours = 0
                night_shift_worked_hours = 0
                if new_attendance not in line.attendance_ids:
                    worked_hours = new_attendance.worked_hours
                    bonus_worked_hours = new_attendance.bonus_worked_hours
                    night_shift_worked_hours = new_attendance.night_shift_worked_hours
                for attendance in line.attendance_ids:
                    bonus_worked_hours += attendance.bonus_worked_hours
                    night_shift_worked_hours \
                        += attendance.night_shift_worked_hours
                    if attendance.id != new_attendance.id:
                        worked_hours += attendance.worked_hours

                    else:
                        if check_out:
                            delta = datetime.strptime(
                                str(check_out),
                                DEFAULT_SERVER_DATETIME_FORMAT) - \
                                    datetime.strptime(
                                        str(check_in),
                                        DEFAULT_SERVER_DATETIME_FORMAT)
                            worked_hours += delta.total_seconds() / 3600.0
                line.write({
                    'duty_hours': duty_hours,
                    'worked_hours': worked_hours,
                    'bonus_worked_hours': bonus_worked_hours,
                    'night_shift_worked_hours': night_shift_worked_hours,
                })

    @api.multi
    def create_line(self, sheet, date_from, date_to):
        dates = list(rrule.rrule(rrule.DAILY,
                                 dtstart=parser.parse(str(date_from)),
                                 until=parser.parse(str(date_to))))
        for date_line in dates:
            name = str(date_line).split(' ')[0]
            line = self.search(
                [('name', '=', name),
                 ('sheet_id', '=', sheet.id)])
            if not line:
                duty_hours, contract, leave, public_holiday = \
                    self.calculate_duty_hours(sheet=sheet,
                                              date_from=date_line)
                leaves = leave[0]
                if len(leaves) > 1:
                    l = leaves[0]
                else:
                    l = leave[0]
                if l:
                    leave_type = l[0].holiday_status_id
                    if leave_type.take_into_attendance:
                        duty_hours -= duty_hours * leave[1]
                if contract and contract.rate_per_hour:
                    duty_hours = 0.0
                values = {'name': name,
                          'attendance_date': name,
                          'sheet_id': sheet.id,
                          'duty_hours': duty_hours,
                          'contract_id': contract.id}
                if public_holiday:
                    values.update(leave_description=public_holiday.name)
                if leave and leave[0]:
                    values.update(leave_description=l.name)
                self.create(values)

    @api.multi
    def calculate_duty_hours(self, sheet, date_from):
        contract_obj = self.env['hr.contract']
        duty_hours = 0.0
        contract = contract_obj.search(
            [('state', 'not in', ('draft', 'cancel')),
             ('employee_id', '=', sheet.employee_id.id),
             ('date_start', '<=', date_from), '|',
             ('date_end', '>=', date_from),
             ('date_end', '=', None)])

        if len(contract) > 1:
            raise UserError(_(
                'You have more than one active contract'))
        leave = sheet.count_leaves(str(date_from), sheet.employee_id.id)
        public_holiday = sheet.count_public_holiday(str(date_from))
        if contract and contract.rate_per_hour:
            return 0.00, contract, leave, public_holiday
        if contract:
            dh = contract.resource_calendar_id.get_working_hours_of_date(
                start_dt=fields.Datetime.from_string(str(date_from)),
                resource_id=sheet.employee_id.id)
        else:
            dh = sheet.employee_id.resource_calendar_id.get_working_hours_of_date(
                start_dt=fields.Datetime.from_string(str(date_from)),
                resource_id=sheet.employee_id.id)
        if contract.state not in ('draft', 'cancel'):
            if leave[1] == 0 and not public_holiday:
                if not dh:
                    dh = 0.00
                duty_hours += dh
            elif public_holiday:
                dh = 0.00
                duty_hours += dh
            else:
                if not public_holiday and leave[1] != 0:
                    leaves = leave[0]
                    if len(leaves) > 1:
                        l = leaves[0]
                    else:
                        l = leave[0]
                    leave_type = l.holiday_status_id
                    if not leave_type.take_into_attendance:
                        duty_hours += dh
                    else:
                        duty_hours += dh * (1 - leave[1])
        else:
            dh = 0.00
            duty_hours += dh
        return duty_hours, contract, leave, public_holiday
