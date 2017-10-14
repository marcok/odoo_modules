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


import time
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class CreateTimesheetWithTag(models.TransientModel):
    _inherit = 'hr.timesheet.current.open'
    _description = 'Create Timesheet With Employee Tag'

    # Added below fields on the wizard
    category_id = fields.Many2one('hr.employee.category',
                                  string="Employee Tag",
                                  required=True,
                                  help='Category of Employee')
    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')

    @api.onchange('date_from', 'date_to')
    @api.multi
    def change_date(self, date_from, date_to):
        if date_to and date_from and date_from > date_to:
            raise ValidationError(
                _('You added wrong date period.'))

    @api.model
    def create(self, values):
        if values.get('date_to') and values.get('date_from') \
                and values.get('date_from') > values.get('date_to'):
            raise ValidationError(
                _('You added wrong date period.'))
        return super(CreateTimesheetWithTag, self).create(values)

    @api.multi
    def open_timesheet(self):
        employee_obj = self.env['hr.employee']
        ts = self.env['hr_timesheet_sheet.sheet']
        value = super(CreateTimesheetWithTag, self).open_timesheet()
        # First: Search all employees of selected Tag
        if not self.category_id:
            return value
        category_id = self.category_id.id
        employee_objects = employee_obj.search([
            ('category_ids', 'in', [category_id])])
        user_ids = []
        ts_ids = []
        date_from = self.date_from or time.strftime('%Y-%m-%d')
        date_to = self.date_to or time.strftime('%Y-%m-%d')
        # Second: Create/Open Timesheets for all fetched employees.
        for emp in employee_objects:

            if emp.user_id:
                user_ids.append(emp.user_id.id)
                ts_id = ts.search([
                    ('user_id', '=', emp.user_id.id),
                    ('state', 'in', ('draft', 'new')),
                    ('date_from', '<=', date_from),
                    ('date_to', '>=', date_to)
                ])
                if ts_id:
                    raise ValidationError(
                        _('Timesheet already exists for {name}.'.format(
                            name=emp.name)))
                if not ts_id:
                    values = {'employee_id': emp.id}
                    if self.date_from and self.date_to:
                        values.update({
                            'date_from': date_from,
                            'date_to': date_to})
                    ts_id = ts.create(values)

                ts_ids.append(ts_id.id)

        # Third: Add it to dictionary to be returned
        domain = "[('id','in',%s),('user_id', 'in', %s)]" % (ts_ids, user_ids)
        value.update(domain=domain)
        value.update(view_mode='tree,form')
        return value

# END
