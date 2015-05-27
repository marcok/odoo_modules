#Done BY Addition IT Solutions: BEGIN
from openerp.osv import fields, osv

class import_leave_requests(osv.osv_memory):
    _name = 'import.leave.requests'
    _description = 'Import Leave Requests With Employee Tag'
    _columns = {
        'leave_dates': fields.binary('Select *.csv', required=True, help="Select csv file having holiday dates."),
        'leave_type_id': fields.many2one('hr.holidays.status','Leave Type', required=True),
        'employee_tag_id': fields.many2one('hr.employee.category', "Employee Tag", required=True),
    }

    def import_leave_data(self, cr, uid, ids, context=None):
        holiday_obj = self.pool.get('hr.holidays')
        employee_obj = self.pool.get('hr.employee')
        for data in self.browse(cr, uid, ids, context):
            leaves = (data.leave_dates.decode('base64')).split('\n')
            category_id = data.employee_tag_id.id
            employee_ids = employee_obj.search(cr, uid, [('category_ids','in',[category_id])], context=context)
            for employee in employee_ids:
                for leave in leaves[:-1]:
                    holiday_id = holiday_obj.create(cr, uid, {
                                                 'date_from': leave+' 00:00:00',
                                                 'date_to': leave+' 00:01:00',
                                                 'holiday_status_id': data.leave_type_id.id,
                                                 'employee_id': employee,
                                                 'number_of_days_temp': 1.0,
                                                 'type': 'remove'
                                                 })
                    holiday_obj.holidays_validate(cr, uid, [holiday_id], context=context)
        return True

#END