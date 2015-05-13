#Done BY Addition IT Solutions: BEGIN
import time

from openerp.osv import fields, osv
from openerp.tools.translate import _

class create_timesheet_with_tag(osv.osv_memory):

    _inherit = 'hr.timesheet.current.open'
    _description = 'Create Timesheet With Employee Tag'
    _columns = {
            # Added below fields on the wizard
            'category_id': fields.many2one('hr.employee.category', "Employee Tag", required=True, help='Category of Employee'),
            'date_from': fields.date('Start Date'),
            'date_to': fields.date('End Date'),
    }

    def open_timesheet(self, cr, uid, ids, context=None):
        employee_obj = self.pool.get('hr.employee')
        ts = self.pool.get('hr_timesheet_sheet.sheet')
        value = super(create_timesheet_with_tag, self).open_timesheet(cr, uid, ids, context)
        if ids is None:
            return value

        #First: Search all employees of selected Tag
        record = self.browse(cr, uid, ids[0], context)
        category_id = record.category_id.id
        employee_ids = employee_obj.search(cr, uid, [('category_ids','in',[category_id])], context=context)
        user_ids = []
        ts_ids = []
        date_from = record.date_from or time.strftime('%Y-%m-%d')
        date_to = record.date_to or time.strftime('%Y-%m-%d')

        #Second: Create/Open Timesheets for all fetched employees.
        for emp in employee_obj.browse(cr, uid, employee_ids, context=context):
            if emp.user_id:
                user_ids.append(emp.user_id.id)
                ts_id = ts.search(cr, uid, [('user_id','=',emp.user_id.id),
                                            ('state','in',('draft','new')),
                                            ('date_from','<=',date_from), 
                                            ('date_to','>=',date_to)], 
                                  context=context)
                if ts_id:
                    raise osv.except_osv(_('Data Error!'),_('Timesheet already exists for %s.') %(emp.name))
                if not ts_id:
                    vals = {'employee_id': emp.id}
                    if record.date_from and record.date_to:
                        vals.update({
                                    'date_from': date_from,
                                    'date_to': date_to})
                    ts_id = ts.create(cr, uid, vals)
                ts_ids.append(ts_id)
        
        #Third: Add it to dictionary to be returned
        domain = "[('id','in',%s),('user_id', 'in', %s)]" %(ts_ids,user_ids)
        value.update(domain=domain)
        value.update(view_mode='tree,form')
        return value

#END

