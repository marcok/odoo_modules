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


from openerp import api, fields, models, _
from openerp.exceptions import ValidationError


class HrTimesheetSheet(models.Model):
    _inherit = "hr_timesheet_sheet.sheet"

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

