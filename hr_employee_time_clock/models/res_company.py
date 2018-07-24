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


from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    timesheet_range = fields.Selection(
        [('week', 'Week'),
         ('month', 'Month')],
        default='week', string='Timesheet range',
        help="Periodicity on which you validate your timesheets.")
    timesheet_max_difference = fields.Float(
        string='Timesheet allowed difference(Hours)',
        help="Allowed difference in hours between the sign in/out and the timesheet " \
             "computation for one sheet. Set this to 0 if you do not want any control.",
        default=0.0)
