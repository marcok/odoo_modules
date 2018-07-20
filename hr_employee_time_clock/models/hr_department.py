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


from odoo import api, fields, models


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    timesheet_to_approve_count = fields.Integer(
        compute='_compute_timesheet_to_approve', string='Timesheet to Approve')

    @api.multi
    def _compute_timesheet_to_approve(self):
        timesheet_data = self.env['hr_timesheet_sheet.sheet'].read_group(
            [('department_id', 'in', self.ids),
             ('state', '=', 'confirm')],
            ['department_id'], ['department_id'])
        result = dict((data['department_id'][0], data['department_id_count'])
                      for data in timesheet_data)
        for department in self:
            department.timesheet_to_approve_count = result.get(department.id, 0)
