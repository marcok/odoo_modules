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


import time
from pytz import timezone
import pytz
from odoo.tools import (
    DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_DATETIME_FORMAT,
    drop_view_if_exists,
)

import math
from odoo import models, api, _, fields
from datetime import datetime, time, timedelta
from odoo.exceptions import ValidationError, AccessError
import logging
from dateutil import rrule, parser

_logger = logging.getLogger(__name__)


def _employee_get(obj):
    employee = obj.env['hr.employee'].search([('user_id', '=', obj.env.uid)])
    if employee:
        return employee.id and employee[0].id
    else:
        return False


class HrAttendance(models.Model):
    _description = 'HrAttendance'

    @api.multi
    def write(self, values):
        if not self.env.context.get('check_overtime'):
            values = self.check_overtime(values)
        check_in = values.get('check_in') or self.check_in
        if check_in:
            values['name'] = check_in
            times = datetime.strptime(values.get('name'), "%Y-%m-%d %H:%M:%S")
            if datetime.now() < times:
                raise ValidationError(
                    _('You can not set time of Sing In (resp. Sing Out) which '
                      'is later than a current time'))
        if self.sheet_id.state == 'done' and not \
                self.user_has_groups('hr.group_hr_user'):
            raise AccessError(
                _(
                    "Sorry, only manager is allowed to edit attendance"
                    " of approved attendance sheet."))

        check_out = values.get('check_out') or self.check_out
        if check_out and check_in:
            self.env['employee.attendance.analytic'].recalculate_line_worktime(
                self, values)
        return super(HrAttendance, self).write(values)


