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


import time
from openerp.osv import fields, osv, orm
from openerp.tools.translate import _


class create_timesheet_with_tag(osv.osv_memory):
    _inherit = 'hr.timesheet.current.open'
    _description = 'Create Timesheet With Employee Tag'
    _columns = {
        # Added below fields on the wizard
        'category_id': fields.many2one('hr.employee.category', "Employee Tag",
                                       required=True,
                                       help='Category of Employee'),
        'date_from': fields.date('Start Date'),
        'date_to': fields.date('End Date'),
    }

    def change_date(self, cr, uid, ids, date_from, date_to, context=None):
        if date_to and date_from and date_from > date_to:
            raise orm.except_orm(
                _("Error"),
                _("You added wrong date period."))

    def create(self, cr, uid, vals, context=None):
        if vals.get('date_to') and vals.get('date_from') and vals.get(
                'date_from') > vals.get('date_to'):
            raise orm.except_orm(
                _("Error"),
                _("You added wrong date period."))
        return super(create_timesheet_with_tag, self).create(cr, uid, vals,
                                                             context=context)

    def open_timesheet(self, cr, uid, ids, context=None):
        employee_obj = self.pool.get('hr.employee')
        ts = self.pool.get('hr_timesheet_sheet.sheet')
        value = super(create_timesheet_with_tag, self).open_timesheet(cr, uid,
                                                                      ids,
                                                                      context)
        if ids is None:
            return value

        # First: Search all employees of selected Tag
        record = self.browse(cr, uid, ids[0], context)
        category_id = record.category_id.id
        employee_ids = employee_obj.search(cr, uid, [
            ('category_ids', 'in', [category_id])], context=context)
        user_ids = []
        ts_ids = []
        date_from = record.date_from or time.strftime('%Y-%m-%d')
        date_to = record.date_to or time.strftime('%Y-%m-%d')
        # Second: Create/Open Timesheets for all fetched employees.
        for emp in employee_obj.browse(cr, uid, employee_ids, context=context):

            if emp.user_id:
                user_ids.append(emp.user_id.id)
                ts_id = ts.search(cr, uid, [('user_id', '=', emp.user_id.id),
                                            ('state', 'in', ('draft', 'new')),
                                            ('date_from', '<=', date_from),
                                            ('date_to', '>=', date_to)],
                                  context=context)
                if ts_id:
                    raise osv.except_osv(_('Data Error!'), _(
                        'Timesheet already exists for %s.') % (emp.name))
                if not ts_id:
                    vals = {'employee_id': emp.id}
                    if record.date_from and record.date_to:
                        vals.update({
                            'date_from': date_from,
                            'date_to': date_to})
                    ts_id = ts.create(cr, uid, vals, context=context)

                ts_ids.append(ts_id)

        # Third: Add it to dictionary to be returned
        domain = "[('id','in',%s),('user_id', 'in', %s)]" % (ts_ids, user_ids)
        value.update(domain=domain)
        value.update(view_mode='tree,form')
        return value

# END
