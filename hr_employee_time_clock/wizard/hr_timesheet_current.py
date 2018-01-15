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


class HrTimesheetCurrentOpen(models.TransientModel):
    _name = 'hr.timesheet.current.open'
    _description = 'hr.timesheet.current.open'

    @api.model
    def open_timesheet(self):
        view_type = 'form,tree'

        sheets = self.env['hr_timesheet_sheet.sheet'].search(
            [('user_id', '=', self._uid),
             ('state', 'in', ('draft', 'new')),
             ('date_from', '<=', fields.Date.today()),
             ('date_to', '>=', fields.Date.today())])
        if len(sheets) > 1:
            view_type = 'tree,form'
            domain = "[('id', 'in', " + str(sheets.ids) \
                     + "),('user_id', '=', uid)]"
        else:
            domain = "[('user_id', '=', uid)]"
        value = {
            'domain': domain,
            'name': _('Open Timesheet'),
            'view_type': 'form',
            'view_mode': view_type,
            'res_model': 'hr_timesheet_sheet.sheet',
            'view_id': False,
            'type': 'ir.actions.act_window'
        }
        if len(sheets) == 1:
            value['res_id'] = sheets.ids[0]
        return value
