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

from odoo import api, fields, models, SUPERUSER_ID, _
from dateutil import rrule, parser
import pytz
from datetime import datetime, date, timedelta
import calendar
import math

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    This migration is made to calculate running time for each active employee and
    write it into last attendance, which has check out. It is important to
    companies that already use Employee Time Clock module.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    employee_ids = env['hr.employee'].search([('active', '=', True)])
    i = len(employee_ids)
    analytic = env['employee.attendance.analytic']
    analytic.search([]).unlink()
    for employee in employee_ids:
        _logger.info('\n')
        _logger.info(i)
        _logger.info(employee.name)
        sheets = env['hr_timesheet_sheet.sheet'].search(
            [('employee_id', '=', employee.id)])

        for sheet in sheets:
            analytic.create_line(
                sheet, sheet.date_from, sheet.date_to)
            attendances = env['hr.attendance'].search(
                [('sheet_id', '=', sheet.id)])
            for attendance in attendances:
                if attendance.check_out:
                    analytic.recalculate_line_worktime(
                        attendance, {'check_out': attendance.check_out})
        i -= 1
