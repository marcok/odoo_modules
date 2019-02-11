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

from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrHolidaysPublic(models.Model):
    _inherit = 'hr.holidays.public'


class HrHolidaysPublicLine(models.Model):
    _inherit = 'hr.holidays.public.line'

    @api.model
    def create(self, values):
        line = super(HrHolidaysPublicLine, self).create(values)
        line_date = str(line.date)
        self.env['employee.attendance.analytic'].recalculate_line(
            line_date=line_date)
        return line

    @api.multi
    def write(self, values):
        old_date = self.date
        new_date = values.get('date')
        res = super(HrHolidaysPublicLine, self).write(values)
        self.env.cr.commit()
        if values.get('date'):
            self.env['employee.attendance.analytic'].recalculate_line(
                line_date=old_date)
            self.env['employee.attendance.analytic'].recalculate_line(
                line_date=new_date)

        return res

    @api.multi
    def unlink(self):
        old_date = self.date
        res = super(HrHolidaysPublicLine, self).unlink()
        self.env['employee.attendance.analytic'].recalculate_line(
            line_date=old_date)
        return res
