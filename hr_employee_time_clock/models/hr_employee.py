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
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


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
        attendance = super(HrEmployee, self).attendance_action_change()
        if not self.env.context.get('attendance_manual'):
            return True
        return attendance

    @api.multi
    def attendance_manual(self, next_action, entered_pin=None):
        self.ensure_one()
        if not (entered_pin is None) or self.env['res.users'].browse(
                SUPERUSER_ID).has_group(
            'hr_attendance.group_hr_attendance_use_pin') and (
                        self.user_id and self.user_id.id != self._uid
                or not self.user_id):
            if entered_pin != self.pin:
                return {'warning': _('Wrong PIN')}
        ctx = self.env.context.copy()
        ctx['attendance_manual'] = True
        return self.with_context(ctx).attendance_action(next_action)

    @api.multi
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
