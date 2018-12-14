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


from odoo import api, fields, models, _
from dateutil import rrule, parser
import logging

_logger = logging.getLogger(__name__)


class HrContract(models.Model):
    """
        Addition plugin for HR timesheet for work with duty hours
    """
    _inherit = 'hr.contract'

    rate_per_hour = fields.Boolean(string="Use hour rate")

    @api.multi
    def write(self, values):
        old_date_start = self.date_start
        old_date_end = self.date_end
        analytic_pool = self.env['attendance.line.analytic']
        res = super(HrContract, self).write(values)
        if values.get('resource_calendar_id') \
                or 'rate_per_hour' in values.keys():
            lines = analytic_pool.search(
                [('contract_id', '=', self.id)])
            if lines:
                for line in lines:
                    date_from = line.name + ' 00:00:00'

                    dates = list(rrule.rrule(
                        rrule.DAILY,
                        dtstart=parser.parse(date_from),
                        until=parser.parse(date_from)))
                    for date_line in dates:
                        analytic_pool.recalculate_line(
                            line_date=str(date_line),
                            employee_id=self.employee_id)

        if values.get('date_end'):
            if old_date_end:
                dates = calculate_days(old_date_end, values.get('date_end'))

                for date_line in dates:
                    analytic_pool.recalculate_line(
                        line_date=str(date_line), employee_id=self.employee_id)
            else:
                lines = analytic_pool.search(
                    [('contract_id', '=', self.id),
                     ('attendance_date', '>', values.get('date_end'))])
                if lines:
                    dates = list(rrule.rrule(
                        rrule.DAILY,
                        dtstart=parser.parse(values.get('date_end')),
                        until=parser.parse(lines[-1].name)))
                    for date_line in dates:
                        analytic_pool.recalculate_line(
                            line_date=str(date_line),
                            employee_id=self.employee_id)
        elif 'date_end' in values.keys():
            line = analytic_pool.search(
                [('contract_id', '=', self.id),
                 ('attendance_date', '=', old_date_end)])
            lines = analytic_pool.search(
                [('sheet_id', '=', line.sheet_id.id),
                 ('attendance_date', '>', old_date_end)])
            if lines:
                dates = list(rrule.rrule(
                    rrule.DAILY,
                    dtstart=parser.parse(old_date_end),
                    until=parser.parse(lines[-1].name)))
                for date_line in dates:
                    analytic_pool.recalculate_line(
                        line_date=str(date_line), employee_id=self.employee_id)
        if values.get('date_start'):

            dates = calculate_days(old_date_start, values.get('date_start'))
            for date_line in dates:
                analytic_pool.recalculate_line(
                    line_date=str(date_line), employee_id=self.employee_id)
        return res

    @api.model
    def create(self, values):
        contract = super(HrContract, self).create(values)
        old_date_start = contract.date_start
        old_date_end = contract.date_end
        analytic_pool = self.env['attendance.line.analytic']
        sheets = self.env['hr_timesheet_sheet.sheet'].search(
            [('employee_id', '=', contract.employee_id.id)])
        if sheets:
            if not old_date_end:
                lines = analytic_pool.search(
                    [('contract_id', '=', False),
                     ('sheet_id', 'in', sheets.ids), ])
                for line in lines:
                    date_1 = fields.Datetime.from_string(old_date_start)
                    date_2 = fields.Datetime.from_string(line.name)
                    if date_1 <= date_2:
                        analytic_pool.recalculate_line(
                            line_date=line.name,
                            employee_id=self.employee_id)
            else:
                date_1 = fields.Datetime.from_string(old_date_start)
                date_2 = fields.Datetime.from_string(old_date_end)
                lines = analytic_pool.search(
                    [('contract_id', '=', False),
                     ('sheet_id', 'in', sheets.ids),
                     ('attendance_date', '>=', date_1),
                     ('attendance_date', '<=', date_2)])
                for line in lines:
                    analytic_pool.recalculate_line(
                        line_date=line.name,
                        employee_id=self.employee_id)

        return contract

    @api.multi
    def unlink(self):
        analytic_pool = self.env['attendance.line.analytic']
        lines = analytic_pool.search(
            [('contract_id', '=', self.id)])
        employee = self.employee_id
        res = super(HrContract, self).unlink()
        if lines:
            for line in lines:
                date_from = line.name + ' 00:00:00'

                dates = list(rrule.rrule(
                    rrule.DAILY,
                    dtstart=parser.parse(date_from),
                    until=parser.parse(date_from)))
                for date_line in dates:
                    analytic_pool.recalculate_line(
                        line_date=str(date_line), employee_id=employee)
        return res


def calculate_days(date_start, date_end):
    old_date_1 = fields.Datetime.from_string(date_start)
    old_date_2 = fields.Datetime.from_string(date_end)
    if old_date_1 > old_date_2:
        dates = list(rrule.rrule(
            rrule.DAILY,
            dtstart=parser.parse(date_end),
            until=parser.parse(date_start)))
    else:
        dates = list(rrule.rrule(
            rrule.DAILY,
            dtstart=parser.parse(date_start),
            until=parser.parse(date_end)))
    return dates
