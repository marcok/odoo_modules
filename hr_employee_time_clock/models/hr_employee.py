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

from random import choice
from string import digits
import logging
from odoo import exceptions, SUPERUSER_ID
from datetime import date
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    start_time_different = fields.Float(string='Start Time Different',
                                        default=0.00)
    start_overtime_different = fields.Integer(string='Start Overtime Count',
                                              default=0.00)


class HrEmployee(models.Model):
    _inherit = "hr.employee"
    _description = "Employee"

    def _compute_timesheet_count(self):
        for employee in self:
            employee.timesheet_count = employee.env[
                'hr_timesheet_sheet.sheet'].search_count(
                [('employee_id', '=', employee.id)])

    def _default_random_pin(self):
        return ("".join(choice(digits) for i in range(4)))

    def _default_random_barcode(self):
        barcode = None
        while not barcode or self.env['hr.employee'].search(
                [('barcode', '=', barcode)]):
            barcode = "".join(choice(digits) for i in range(8))
        return barcode

    timesheet_count = fields.Integer(compute='_compute_timesheet_count',
                                     string='Timesheets')

    barcode = fields.Char(string="Badge ID",
                          help="ID used for employee identification.",
                          default=_default_random_barcode,
                          copy=False)
    pin = fields.Char(string="PIN",
                      default=_default_random_pin,
                      help="PIN used to Check In/Out in Kiosk Mode "
                           "(if enabled in Configuration).",
                      copy=False)

    attendance_ids = fields.One2many('hr.attendance',
                                     'employee_id',
                                     string="Attendances",
                                     help='list of attendances for the employee')
    last_attendance_id = fields.Many2one('hr.attendance',
                                         compute='_compute_last_attendance_id')
    attendance_state = fields.Selection(
        string="Attendance",
        compute='_compute_attendance_state',
        selection=[('checked_out', "Checked out"),
                   ('checked_in', "Checked in")])
    manual_attendance = fields.Boolean(
        string='Manual Attendance',
        compute='_compute_manual_attendance',
        inverse='_inverse_manual_attendance',
        help='The employee will have access to the "My Attendances" '
             'menu to check in and out from his session')

    # start_time_different = fields.Float(string='Start Time Different',
    #                                    default=0.00)

    _sql_constraints = [('barcode_uniq', 'unique (barcode)',
                         "The Badge ID must be unique, this one is "
                         "already assigned to another employee.")]

    # start_overtime_different = fields.Integer(string='Start Overtime Count',
    #                                          default=0.00)

    def _compute_manual_attendance(self):
        for employee in self:
            employee.manual_attendance = employee.user_id.has_group(
                'hr_attendance.group_hr_attendance') \
                if employee.user_id else False

    def _inverse_manual_attendance(self):
        manual_attendance_group = self.env.ref(
            'hr_attendance.group_hr_attendance')
        for employee in self:
            if employee.user_id:
                if employee.manual_attendance:
                    manual_attendance_group.users = [
                        (4, employee.user_id.id, 0)]
                else:
                    manual_attendance_group.users = [
                        (3, employee.user_id.id, 0)]

    @api.depends('attendance_ids')
    def _compute_last_attendance_id(self):
        for employee in self:
            employee.last_attendance_id = employee.attendance_ids \
                                          and employee.attendance_ids[
                                              0] or False

    def initial_overtime(self):
        """
        Checks if timezone is set for each user.
        Checks if each employee has related user.
        Rewrites all attendances of current employee to initialise
        recalculation of bonus, night shift worked hours.
        """
        if not self.user_id:
            raise ValidationError(_("Employee must have related user."))
        if not self.user_id.tz:
            raise ValidationError(_("Timezone for {user} is not set.".format(
                user=self.user_id.name)))
        attendances = self.env['hr.attendance'].search(
            [('employee_id', '=', self.id)])

        for attendance in attendances:
            attendance.write({'check_out': attendance.check_out})

    @api.depends('last_attendance_id.check_in',
                 'last_attendance_id.check_out',
                 'last_attendance_id')
    def _compute_attendance_state(self):
        for employee in self:
            employee.attendance_state = (
                employee.last_attendance_id
                and not employee.last_attendance_id.check_out
                and 'checked_in' or 'checked_out')

    @api.constrains('pin')
    def _verify_pin(self):
        for employee in self:
            if employee.pin and not employee.pin.isdigit():
                raise exceptions.ValidationError(
                    _("The PIN must be a sequence of digits."))

    @api.model
    def attendance_scan(self, barcode):
        """ Receive a barcode scanned from the Kiosk Mode
        and change the attendances of corresponding employee.
            Returns either an action or a warning.
        """
        employee = self.search([('barcode', '=', barcode)], limit=1)
        return employee and employee.attendance_action(
            'hr_attendance.hr_attendance_action_kiosk_mode') or \
               {'warning': _('No employee corresponding to '
                             'barcode %(barcode)s') % {'barcode': barcode}}

    def attendance_manual(self, next_action, entered_pin=None):
        self.ensure_one()
        if not (entered_pin is None) or self.env['res.users'].browse(
                SUPERUSER_ID).has_group(
            'hr_attendance.group_hr_attendance_use_pin') \
                and (self.user_id and self.user_id.id != self._uid
                     or not self.user_id):
            if entered_pin != self.pin:
                return {'warning': _('Wrong PIN')}
        ctx = self.env.context.copy()
        ctx['attendance_manual'] = True
        return self.with_context(ctx).attendance_action(next_action)

    def attendance_action(self, next_action):
        """ Changes the attendance of the employee.
            Returns an action to the check in/out message,
            next_action defines which menu the check in/out
            message should return to. ("My Attendances" or "Kiosk Mode")
        """
        self.ensure_one()
        action_message = self.env.ref(
            'hr_attendance.hr_attendance_action_greeting_message').read()[0]
        action_message['previous_attendance_change_date'] = (
            self.last_attendance_id
            and (self.last_attendance_id.check_out
                 or self.last_attendance_id.check_in) or False)
        if action_message['previous_attendance_change_date']:
            action_message['previous_attendance_change_date'] = \
                fields.Datetime.to_string(fields.Datetime.context_timestamp(
                    self, fields.Datetime.from_string(
                        action_message['previous_attendance_change_date'])))
        action_message['employee_name'] = self.name
        action_message['next_action'] = next_action

        if self.user_id:
            modified_attendance = self.with_user(
                self.user_id.id).attendance_action_change()
        else:
            modified_attendance = self.sudo().attendance_action_change()
        action_message['attendance'] = modified_attendance.read()[0]
        return {'action': action_message}

    def attendance_action_change(self):
        hr_timesheet_sheet_sheet_pool = self.env['hr_timesheet_sheet.sheet']
        hr_timesheet_ids = hr_timesheet_sheet_sheet_pool.search(
            [('employee_id', '=', self.id),
             ('date_from', '<=', date.today()),
             ('date_to', '>=', date.today())])
        if not self.env.context.get('attendance_manual'):
            hr_timesheet_ids = hr_timesheet_sheet_sheet_pool.sudo().search(
                [('employee_id', '=', self.id),
                 ('date_from', '<=', date.today()),
                 ('date_to', '>=', date.today())])
        if not hr_timesheet_ids:
            raise ValidationError(
                _('Please contact your manager to create timesheet for you.'))
        """ Check In/Check Out action
            Check In: create a new attendance record
            Check Out: modify check_out field of appropriate attendance record
        """
        if len(self) > 1:
            raise exceptions.UserError(
                _('Cannot perform check in or '
                  'check out on multiple employees.'))
        action_date = fields.Datetime.now()
        if not self.env.context.get('attendance_manual'):
            if self.sudo().attendance_state != 'checked_in':
                vals = {
                    'employee_id': self.id,
                    'check_in': action_date,
                }
                attendance = self.env['hr.attendance'].sudo().create(vals)
            else:
                attendance = self.env['hr.attendance'].sudo().search(
                    [('employee_id', '=', self.id),
                     ('check_out', '=', False)], limit=1)
                if attendance:
                    attendance.sudo().check_out = action_date
                else:
                    raise exceptions.UserError(
                        _('Cannot perform check out on %(empl_name)s, '
                          'could not find corresponding check in. '
                          'Your attendances have probably been modified '
                          'manually by human resources.') % {
                            'empl_name': self.name, })
        else:
            if self.attendance_state != 'checked_in':
                vals = {
                    'employee_id': self.id,
                    'check_in': action_date,
                }
                attendance = self.env['hr.attendance'].create(vals)
            else:
                attendance = self.env['hr.attendance'].search(
                    [('employee_id', '=', self.id),
                     ('check_out', '=', False)], limit=1)
                if attendance:
                    attendance.check_out = action_date
                else:
                    raise exceptions.UserError(
                        _('Cannot perform check out on %(empl_name)s, '
                          'could not find corresponding check in. '
                          'Your attendances have probably been modified'
                          ' manually by human resources.') % {
                            'empl_name': self.name, })
        if not self.env.context.get('attendance_manual'):
            return True
        return attendance

    @api.model
    def _init_column(self, column_name):
        """ Initialize the value of the given column for existing rows.
            Overridden here because we need to have different default values
            for barcode and pin for every employee.
        """
        if column_name not in ["barcode", "pin"]:
            super(HrEmployee, self)._init_column(column_name)
        else:
            default_compute = self._fields[column_name].default

            query = 'SELECT id FROM "%s" WHERE "%s" is NULL' % (
                self._table, column_name)
            self.env.cr.execute(query)
            employee_ids = self.env.cr.fetchall()

            for employee_id in employee_ids:
                default_value = default_compute(self)

                query = 'UPDATE "%s" SET "%s"=%%s WHERE id = %s' % (
                    self._table, column_name, employee_id[0])
                self.env.cr.execute(query, (default_value,))

    def read(self, fields=None, load='_classic_read'):
        result = super(HrEmployee, self).read(fields=fields, load=load)
        new_result = []
        for r in result:
            if 'state' in fields and not r.get('state'):
                employee_id = r.get('id')
                employee = self.browse(employee_id)
                if employee.attendance_state == 'checked_out':
                    r['state'] = 'absent'
                else:
                    r['state'] = 'present'
            new_result.append(r)
        return new_result

    @api.model
    def check_in_out_action(self, values):
        employee = self.sudo().browse(values.get('employee_id')).exists()
        if not employee:
            return [
                {'error': _(
                    'Please contact your manager to create '
                    'employee for you and change QR-code.')}]

        hr_timesheet_sheet_sheet_pool = self.env['hr_timesheet_sheet.sheet']
        hr_timesheet_ids = hr_timesheet_sheet_sheet_pool.search(
            [('employee_id', '=', employee.id),
             ('date_from', '<=', date.today()),
             ('date_to', '>=', date.today())])
        if not hr_timesheet_ids:
            return [
                {'error': _(
                    'Please contact your manager to create '
                    'timesheet for you.')}]

        """ Check In/Check Out action
            Check In: create a new attendance record
            Check Out: modify check_out field of appropriate attendance record
        """
        if len(self) > 1:
            raise exceptions.UserError(
                _('Cannot perform check in or '
                  'check out on multiple employees.'))
        action_date = fields.Datetime.now()
        if employee.attendance_state != 'checked_in':
            vals = {
                'employee_id': employee.id,
                'check_in': action_date,
            }
            self.env['hr.attendance'].sudo().create(vals)
        else:
            attendance = self.env['hr.attendance'].sudo().search(
                [('employee_id', '=', employee.id),
                 ('check_out', '=', False)], limit=1).exists()
            if attendance:
                attendance.sudo().check_out = action_date
            else:
                return [
                    {'error': _('Cannot perform check out on %s, '
                                'could not find corresponding check in. '
                                'Your attendances have probably been modified '
                                'manually by human resources.') % self.name}]

        employee = self.sudo().browse(employee.id)
        ctx = self.env.context.copy()
        ctx.update(online_analysis=True)
        res = hr_timesheet_ids.with_context(
            ctx).attendance_analysis(hr_timesheet_ids.id)
        running = 0
        date_line = values.get('date').split(' ')[0]
        dddd = (fields.Datetime.from_string(date_line + ' 00:00:00'))
        date_format, time_format = \
            hr_timesheet_sheet_sheet_pool._get_user_datetime_format()
        date_line = dddd.strftime("{} {}".format(date_format,
                                                 time_format)).split(' ')[0]
        for d in res.get('hours'):
            if d.get('name') == date_line:
                running = d.get('running')

        return [{'log': employee.attendance_state,
                 'name': employee.name,
                 'image': employee.image_medium,
                 'running': running,
                 'user_id': employee.user_id.id}]
