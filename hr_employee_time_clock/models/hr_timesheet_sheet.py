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


from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrTimesheetSheet(models.Model):
    _inherit = "hr_timesheet_sheet.sheet"

    def _total(self, cr, uid, ids, name, args, context=None):
        """ Compute the attendances, analytic lines timesheets
        and differences between them
            for all the days of a timesheet and the current day
        """
        res = dict.fromkeys(ids, {
            'total_attendance': 0.0,
            'total_timesheet': 0.0,
            'total_difference': 0.0,
        })

        cr.execute("""
            SELECT sheet_id as id,
                   sum(total_attendance) as total_attendance,
                   sum(total_timesheet) as total_timesheet,
                   sum(total_difference) as  total_difference
            FROM hr_timesheet_sheet_sheet_day
            WHERE sheet_id IN %s
            GROUP BY sheet_id
        """, (tuple(ids),))

        res.update(dict((x.pop('id'), x) for x in cr.dictfetchall()))

        return res

    @api.onchange('date_from', 'date_to')
    @api.multi
    def change_date(self):
        if self.date_to and self.date_from and self.date_from > self.date_to:
            raise ValidationError(
                _('You added wrong date period.'))

    @api.model
    def create(self, values):
        if values.get('date_to') and values.get('date_from') \
                and values.get('date_from') > values.get('date_to'):
            raise ValidationError(
                _('You added wrong date period.'))
        return super(HrTimesheetSheet, self).create(values)

    total_attendance = fields.Float(compute="_total",
                                    string='Total Attendance')
    total_timesheet = fields.Float(compute="_total",
                                   string='Total Timesheet')
    total_difference = fields.Float(compute="_total",
                                    string='Difference')
