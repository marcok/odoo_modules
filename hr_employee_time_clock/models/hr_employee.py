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


from datetime import date
from openerp import api, fields, models, _
from openerp.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = "hr.employee"
    _description = "Employee"

    @api.multi
    def attendance_action_change(self):
        hr_timesheet_sheet_sheet_pool = self.env['hr_timesheet_sheet.sheet']
        hr_timesheet_ids = hr_timesheet_sheet_sheet_pool.search(
            [('employee_id', '=', self.id),
             ('date_from', '<=', date.today()),
             ('date_to', '>=', date.today())])
        if not hr_timesheet_ids:
            raise ValidationError(
                _('Please contact your manager to create timesheet for you.'))
        return super(HrEmployee, self).attendance_action_change()

    @api.model
    def check_in_out_action(self, values):
        employee = self.sudo().browse(values.get('employee_id')).exists()
        # employee.attendance_action_change()
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
            raise ValidationError(
                _('Cannot perform check in or '
                  'check out on multiple employees.'))
        action_date = fields.Datetime.now()
        if employee.state != 'absent':
            vals = {'name': action_date,
                    'action': 'sign_out',
                    'employee_id': employee.id, }
            log = 'checked_out'
        else:
            vals = {'name': action_date,
                    'action': 'sign_in',
                    'employee_id': employee.id, }
            log = 'checked_in'
        self.env['hr.attendance'].sudo().create(vals)
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
        re = {'log': log,
              'name': employee.name,
              'image': employee.image_medium,
              'running': running,
              'user_id': employee.user_id.id}
        return [{'log': log,
                 'name': employee.name,
                 'image': employee.image_medium,
                 'running': running,
                 'user_id': employee.user_id.id}]