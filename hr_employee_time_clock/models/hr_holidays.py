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

import logging

from odoo import api, fields, models
from dateutil import rrule, parser

_logger = logging.getLogger(__name__)


class HolidaysType(models.Model):
    _inherit = "hr.leave.type"

    take_into_attendance = fields.Boolean(default=True,
                                          string='Take Into Attendance')


class HrHolidays(models.Model):
    _inherit = "hr.leave"

    @api.multi
    def write(self, values):
        state = self.state
        res = super(HrHolidays, self).write(values)
        if (values.get('state') == 'validate' and state == 'confirm') \
                or (values.get('state') == 'refuse' and state == 'validate') \
                or (values.get('state') == 'validate' and state == 'validate1'):
            date_from = str(self.date_from).split(' ')[0] + ' 00:00:00'
            date_to = str(self.date_to).split(' ')[0] + ' 00:00:00'
            dates = list(rrule.rrule(rrule.DAILY,
                                     dtstart=parser.parse(date_from),
                                     until=parser.parse(date_to)))
            for date_line in dates:
                self.env['employee.attendance.analytic'].recalculate_line(
                    line_date=str(date_line), employee_id=self.employee_id)
        return res
