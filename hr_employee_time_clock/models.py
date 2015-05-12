# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from openerp.osv import fields, osv
from dateutil import rrule, parser
import pytz


class hr_timesheet_dh(osv.osv):
    """
        Addition plugin for HR timesheet for work with duty hours
    """
    _inherit = 'hr_timesheet_sheet.sheet'

    def _duty_hours(self, cr, uid, ids, name, args, context=None):
        res = {}
        for sheet in self.browse(cr, uid, ids, context=context or {}):
            res.setdefault(sheet.id, {
                'total_duty_hours': 0.0,
            })
            for duty_hours in sheet.duty_hour_ids:
                res[sheet.id]['total_duty_hours'] += duty_hours.duty_hours
        return res

    def get_overtime(self, cr, uid, ids, start_date, context=None):
        for sheet in self.browse(cr, uid, ids, context):
            if sheet.state == 'done':
                return sheet.total_duty_hours
            return self.calculate_diff(cr, uid, ids, start_date, context)

    def _overtime_diff(self, cr, uid, ids, name, args, context=None):
        res = {}
        for sheet in self.browse(cr, uid, ids, context):
            old_timesheet_start_from = parser.parse(sheet.date_from)-timedelta(days=1)
            prev_timesheet_diff = self.get_previous_month_diff(cr, uid, sheet.employee_id.id,
                                                               old_timesheet_start_from.strftime('%Y-%m-%d'),
                                                               context=context)
            res.setdefault(sheet.id, {
                'calculate_diff_hours': self.get_overtime(cr, uid, ids,
                                                          datetime.today().strftime('%Y-%m-%d'),
                                                          context) + prev_timesheet_diff,
                'prev_timesheet_diff': prev_timesheet_diff,
            })
        return res

    _columns = {
        'total_duty_hours': fields.function(_duty_hours, method=True, string='Total Duty Hours', multi="_duty_hours"),
        'duty_hour_ids': fields.one2many('hr_timesheet.day.dh', 'sheet_id', 'Daily Duty Hours', readonly=True),
        'total_diff_hours': fields.float('Total Diff Hours', readonly=True, default=0.0),
        'calculate_diff_hours': fields.function(_overtime_diff, method=True, string="Diff (worked-duty)", multi="_diff"),
        'prev_timesheet_diff': fields.function(_overtime_diff, method=True, string="Diff from old", multi="_diff"),
    }


    def create(self, cr, uid, vals, context=None):
        res = super(hr_timesheet_dh, self).create(cr, uid, vals, context=context)
        self.create_days_dh(cr, uid, [res], context)
        return res

    def create_days_dh(self, cr, uid, ids, context=None):
        for sheet in self.browse(cr, uid, ids, context=context or {}):

            dates = list(rrule.rrule(rrule.DAILY,
                                     dtstart=parser.parse(sheet.date_from),
                                     until=parser.parse(sheet.date_to)))
            for date_line in dates:
                duty_hours = self.calculate_duty_hours(cr, uid, sheet.employee_id.id, date_line, context)
                self.pool.get('hr_timesheet.day.dh').create(cr,
                                                            uid,
                                                            {'name': date_line, 'duty_hours': duty_hours, 'sheet_id': sheet.id},
                                                            context)

    def calculate_duty_hours(self, cr, uid, employee_id, date_from, context):
        contract_obj = self.pool.get('hr.contract')
        holiday_obj = self.pool.get('hr.holidays')
        calendar_obj = self.pool.get('resource.calendar')
        duty_hours = 0.0
        contract_ids = contract_obj.search(cr, uid, [('employee_id','=',employee_id),
                                                     ('date_start','<=', date_from), '|',
                                                     ('date_end', '>=', date_from), ('date_end', '=', None) ], context=context)
        # Done BY Addition IT Solutions: BEGIN 
        # First: Find all the leaves of current month
        start_leave_period = datetime.strftime((date_from + relativedelta(day=1)),'%Y-%m-%d')
        end_leave_period = datetime.strftime((date_from + relativedelta(day=31)),'%Y-%m-%d')
        holiday_ids = holiday_obj.search(cr, uid, [('date_from','>=',start_leave_period),
                                                   ('date_to','<=',end_leave_period),
                                                   ('employee_id','=',employee_id),
                                                   ('state','=','validate'),
                                                   ('type','=','remove')])
        leaves = []
        
        #Second: If date_from and leave date matches add to list leaves
        for leave in holiday_obj.browse(cr, uid, holiday_ids, context=context):
            leave_date_from = datetime.strptime(leave.date_from, '%Y-%m-%d %H:%M:%S')
            leave_date_to = datetime.strptime(leave.date_to, '%Y-%m-%d %H:%M:%S')
            for days in range(0,int(leave.number_of_days_temp)):
                if leave_date_from.strftime('%Y-%m-%d') == date_from.strftime('%Y-%m-%d'):
                    leaves.append((leave_date_from, leave_date_to))
                    break
                next_leave_date = leave_date_from + relativedelta(days=1)
                leave_date_from = next_leave_date
                
        # END

        for contract in contract_obj.browse(cr, uid, contract_ids, context=context):
            dh = calendar_obj.get_working_hours_of_date(cr=cr, uid=uid,
                                                         id=contract.working_hours.id,
                                                         start_dt=date_from,
                                                         leaves=leaves, # Added leaves here
                                                         compute_leaves=True, # Added this argument to calculate leaves
                                                         resource_id=employee_id, # Find leaves of this employee
                                                         context=context)
            duty_hours += dh
        return duty_hours

    def get_previous_month_diff(self, cr, uid, employee_id, prev_timesheet_date_from, context=None):
        total_diff = 0.0
        timesheet_ids = self.search(cr, uid, [('employee_id','=',employee_id),
                                              ('date_from', '<=', prev_timesheet_date_from),
                                             ])
        for timesheet in self.browse(cr, uid, timesheet_ids):
            total_diff += self.get_overtime(cr, uid, [timesheet.id], start_date=prev_timesheet_date_from, context=context)
        return total_diff

    def attendance_analysis(self, cr, uid, employee_id, start_date, end_date, context=None):
        previous_month_diff = self.get_previous_month_diff(cr, uid, employee_id, start_date, context)
        current_month_diff = previous_month_diff
        res = {
            'previous_month_diff': previous_month_diff,
            'hours': []
        }
        attendance_obj = self.pool.get('hr.attendance')

        dates = list(rrule.rrule(rrule.DAILY,
                                 dtstart=parser.parse(start_date),
                                 until=min(parser.parse(end_date), datetime.utcnow())))
        total = {'worked_hours': 0.0, 'diff': current_month_diff}
        for date_line in dates:

            dh = self.calculate_duty_hours(cr, uid, employee_id, date_line, context)
            worked_hours = 0.0
            for attendance in attendance_obj.search_read(cr, uid, [('employee_id','=', employee_id),
                                                         ('action', '=', 'sign_out'),
                                                         ('name', '>=', date_line.strftime('%Y-%m-%d 00:00:00')),
                                                         ('name', '<=', date_line.strftime('%Y-%m-%d 23:59:59')),
                                                         ], ['name', 'worked_hours']):
                worked_hours += attendance['worked_hours']

            diff = worked_hours-dh
            current_month_diff += diff
            res['hours'].append({'name': date_line.strftime('%Y-%m-%d'),
                                 'worked_hours': attendance_obj.float_time_convert(worked_hours),
                                 'dh': attendance_obj.float_time_convert(dh),
                                 'diff': self.sign_float_time_convert(diff),
                                 'running': self.sign_float_time_convert(current_month_diff)})
            total['worked_hours'] += worked_hours
            total['diff'] += diff
        res['total'] = total
        return res

    def sign_float_time_convert(self, float_time):
        sign = '-' if float_time < 0 else ''
        attendance_obj = self.pool.get('hr.attendance')
        return sign+attendance_obj.float_time_convert(float_time)

    def write(self, cr, uid, ids, vals, context=None):
        if 'state' in vals and vals['state'] == 'done':
            vals['total_diff_hours'] = self.calculate_diff(cr, uid, ids, None, context)
        elif 'state' in vals and vals['state'] == 'draft':
            vals['total_diff_hours'] = 0.0
        res = super(hr_timesheet_dh, self).write(cr, uid, ids, vals, context=context)
        return res

    def calculate_diff(self, cr, uid, ids, end_date=None, context=None):
        attendance_obj = self.pool.get('hr.attendance')
        q = [('action', '=', 'sign_out')]
        if end_date:
            q.append(('name', '<=', end_date))
        for sheet in self.browse(cr, uid, ids, context):
            q.append(('sheet_id', '=', sheet.id))
            worked_hours = 0.0
            for attendance in attendance_obj.search_read(cr, uid, q, ['name', 'worked_hours']):
                worked_hours += attendance['worked_hours']
            return worked_hours-sheet.total_duty_hours

class hr_timesheet_day_dh(osv.osv):
    """
        Daily duty hours
    """
    _name = 'hr_timesheet.day.dh'

    def _init_duty_hours(self):
        self.duty_hours = 5.0

    _columns = {
        'sheet_id': fields.many2one('hr_timesheet_sheet.sheet', 'Sheet'),
        'name': fields.date('Date'),
        'duty_hours': fields.float('Duty Hours'),
    }
