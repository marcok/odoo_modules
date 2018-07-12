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

from odoo import api, models, fields
import logging

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.one
    def initial_overtime(self):
        users = self.env['res.users'].search([])
        for user in users:
            if not user.tz:
                raise ValueError("Timezone for {user} is not set.".format(
                    user=user.name))
        values = {}
        attendances = self.env['hr.attendance'].search([])
        values.update(have_overtime=False,
                      bonus_worked_hours=0.0,
                      calculate_overtime=False)
        for attendance in attendances:
            attendance.write(values)
        for attendance in attendances:
            attendance.write({'check_out': attendance.check_out})