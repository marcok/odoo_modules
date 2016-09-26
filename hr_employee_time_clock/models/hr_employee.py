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


from datetime import date
from openerp.osv import fields, osv, orm
from openerp.tools.translate import _


class hr_employee(osv.osv):
    _inherit = "hr.employee"
    _description = "Employee"

    def attendance_action_change(self, cr, uid, ids, context=None):
        hr_timesheet_sheet_sheet_pool = self.pool.get(
            'hr_timesheet_sheet.sheet')
        hr_timesheet_ids = hr_timesheet_sheet_sheet_pool.search(
            cr, uid, [('employee_id', '=', ids[0]),
                      ('date_from', '<=', date.today()),
                      ('date_to', '>=', date.today())], context=context)
        if not hr_timesheet_ids:
            raise orm.except_orm(
                _("Error"),
                _("Please contact your manager to create timesheet for you."))
        return super(hr_employee, self).attendance_action_change(
            cr, uid, ids, context=context)
