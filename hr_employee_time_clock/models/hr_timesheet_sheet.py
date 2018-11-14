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

import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError
import logging
_logger = logging.getLogger(__name__)


class HrTimesheetSheet(models.Model):
    _name = "hr_timesheet_sheet.sheet"
    _inherit = ['mail.thread']
    _table = 'hr_timesheet_sheet_sheet'
    _order = "id desc"
    _description = "Timesheet"

    def _default_date_from(self):
        user = self.env['res.users'].browse(self.env.uid)
        r = user.company_id and user.company_id.timesheet_range or 'month'
        if r == 'month':
            return time.strftime('%Y-%m-01')
        elif r == 'week':
            return (datetime.today() + relativedelta(
                weekday=0, days=-6)).strftime('%Y-%m-%d')
        elif r == 'year':
            return time.strftime('%Y-01-01')
        return fields.Date.context_today(self)

    def _default_date_to(self):
        user = self.env['res.users'].browse(self.env.uid)
        r = user.company_id and user.company_id.timesheet_range or 'month'
        if r == 'month':
            return (datetime.today() + relativedelta(
                months=+1, day=1, days=-1)).strftime('%Y-%m-%d')
        elif r == 'week':
            return (datetime.today() + relativedelta(
                weekday=6)).strftime('%Y-%m-%d')
        elif r == 'year':
            return time.strftime('%Y-12-31')
        return fields.Date.context_today(self)

    def _default_employee(self):
        emp_ids = self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)])
        return emp_ids and emp_ids[0] or False

    @api.multi
    def _total(self):
        """ Compute the attendances, analytic lines timesheets
        and differences between them
            for all the days of a timesheet and the current day
        """
        ids = [i.id for i in self]

        self.env.cr.execute("""
                SELECT sheet_id as id,
                       sum(total_attendance) as total_attendance,
                       sum(total_timesheet) as total_timesheet,
                       sum(total_difference) as  total_difference
                FROM hr_timesheet_sheet_sheet_day
                WHERE sheet_id IN %s
                GROUP BY sheet_id
            """, (tuple(ids),))

        res = self.env.cr.dictfetchall()
        if res:
            ctx = self.env.context.copy()
            ctx['online_analysis'] = True
            for sheet in self:
                if sheet.id == res[0].get('id'):
                    if self.with_context(ctx).attendance_analysis()[
                        'total'].get('bonus_hours'):
                        sheet.total_attendance = \
                            self.with_context(ctx).attendance_analysis()[
                                'total'].get('worked_hours') + \
                            self.with_context(ctx).attendance_analysis()[
                                'total'].get('bonus_hours')
                    else:
                        sheet.total_attendance = \
                            self.with_context(ctx).attendance_analysis()[
                                'total'].get('worked_hours')
                    sheet.total_timesheet = res[0].get(
                        'total_timesheet')
                    sheet.total_difference = res[0].get(
                        'total_difference')

    @api.depends('attendances_ids')
    def _compute_attendances(self):
        for sheet in self:
            sheet.attendance_count = len(sheet.attendances_ids)

    @api.onchange('date_from', 'date_to')
    @api.multi
    def change_date_from(self):
        date_from = self.date_from
        date_to = self.date_to
        if date_from and not date_to:
            date_to_with_delta = \
                fields.Date.from_string(date_from) + timedelta(hours=164)
            self.date_to = date_to_with_delta
        elif date_from and date_to and date_from > date_to:
            date_to_with_delta = \
                fields.Date.from_string(date_from) + timedelta(hours=164)
            self.date_to = str(date_to_with_delta)

    name = fields.Char(string="Note",
                       states={'confirm': [('readonly', True)],
                               'done': [('readonly', True)]})
    employee_id = fields.Many2one('hr.employee',
                                  string='Employee',
                                  default=_default_employee,
                                  required=True,
                                  readonly=True,
                                  states={'new': [('readonly', False)]})
    user_id = fields.Many2one('res.users',
                              related='employee_id.user_id',
                              string='User',
                              store=True,
                              readonly=True,
                              states={'new': [('readonly', False)]})
    date_from = fields.Date(string='Date From',
                            default=_default_date_from,
                            required=True,
                            index=True,
                            readonly=True,
                            states={'new': [('readonly', False)]})
    date_to = fields.Date(string='Date To',
                          default=_default_date_to,
                          required=True,
                          index=True,
                          readonly=True,
                          states={'new': [('readonly', False)]})
    timesheet_ids = fields.One2many('account.analytic.line',
                                    'sheet_id',
                                    string='Timesheet lines',
                                    readonly=True,
                                    states={
                                        'draft': [('readonly', False)],
                                        'new': [('readonly', False)]})


    state = fields.Selection([('new', 'New'),
                              ('draft', 'Open'),
                              ('confirm', 'Waiting Approval'),
                              ('done', 'Approved')],
                             default='new',
                             track_visibility='onchange',
                             string='Status',
                             required=True,
                             readonly=True,
                             index=True,
                             help=' * The \'Open\' status is used when a user '
                                  'is encoding a new and unconfirmed timesheet.'
                                  '\n* The \'Waiting Approval\' status is used '
                                  'to confirm the timesheet by user. '
                                  '\n* The \'Approved\' status is used when the'
                                  ' users timesheet is accepted by '
                                  'his/her senior.')
    account_ids = fields.One2many('hr_timesheet_sheet.sheet.account',
                                  'sheet_id',
                                  string='Analytic accounts',
                                  readonly=True)
    company_id = fields.Many2one('res.company',
                                 string='Company')
    department_id = fields.Many2one('hr.department',
                                    string='Department',
                                    default=lambda self: self.env[
                                        'res.company']._company_default_get())

    total_attendance = fields.Float(compute="_total",
                                    string='Total Attendance')
    total_timesheet = fields.Float(compute="_total",
                                   string='Total Timesheet')
    total_difference = fields.Float(compute="_total",
                                    string='Difference')
    attendances_ids = fields.One2many('hr.attendance', 'sheet_id',
                                      'Attendances')
    period_ids = fields.One2many('hr_timesheet_sheet.sheet.day', 'sheet_id',
                                 string='Period', readonly=True)
    attendance_count = fields.Integer(compute='_compute_attendances',
                                      string="Attendances")

    total_duty_hours = fields.Float(compute='_duty_hours',
                                    string='Total Duty Hours',
                                    multi="_duty_hours")
    total_duty_hours_done = fields.Float(string='Total Duty Hours',
                                         readonly=True,
                                         default=0.0)
    total_diff_hours = fields.Float(string='Total Diff Hours',
                                    readonly=True,
                                    default=0.0)
    calculate_diff_hours = fields.Float(compute='_overtime_diff',
                                        string="Diff (worked-duty)",
                                        multi="_diff")
    prev_timesheet_diff = fields.Float(compute='_overtime_diff',
                                       method=True,
                                       string="Diff from old",
                                       multi="_diff")
    analysis = fields.Text(compute='_get_analysis',
                           type="text",
                           string="Attendance Analysis")

    @api.model
    def create(self, values):
        if 'employee_id' in values:
            if not self.env['hr.employee'].browse(
                    values['employee_id']).user_id:
                raise UserError(_(
                    'In order to create a timesheet for this employee,'
                    ' you must link him/her to a user.'))
            if not self.env['hr.employee'].browse(
                    values['employee_id']).department_id:
                raise UserError(_(
                    'In order to create a timesheet for this employee,'
                    ' you must link him/her to a department.'))
            else:
                values['department_id']= self.env['hr.employee'].browse(
                    values['employee_id']).department_id.id
        if values.get('date_to') and values.get('date_from') \
                and values.get('date_from') > values.get('date_to'):
            raise ValidationError(
                _('You added wrong date period.'))
        res = super(HrTimesheetSheet, self).create(values)
        res.write({'state': 'draft'})
        return res

    @api.constrains('date_to', 'date_from', 'employee_id')
    def _check_sheet_date(self, forced_user_id=False):
        for sheet in self:
            new_user_id = forced_user_id or sheet.user_id and sheet.user_id.id
            if new_user_id:
                self.env.cr.execute('''
                    SELECT id
                    FROM hr_timesheet_sheet_sheet
                    WHERE (date_from <= %s and %s <= date_to)
                        AND user_id=%s
                        AND id <> %s''',
                                    (sheet.date_to,
                                     sheet.date_from,
                                     new_user_id,
                                     sheet.id))
                if any(self.env.cr.fetchall()):
                    raise ValidationError(_(
                        'You cannot have 2 timesheets that overlap!\n'
                        'Please use the menu \'My Current Timesheet\' '
                        'to avoid this problem.'))

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id:
            self.department_id = self.employee_id.department_id.id
            self.user_id = self.employee_id.user_id

    def copy(self, *args, **argv):
        raise UserError(_('You cannot duplicate a timesheet.'))

    @api.multi
    def write(self, vals):
        if vals.get('state'):
            if vals.get('state') == 'done':
                employee = self.env['hr.employee'].search([
                    ('user_id', '=', self.env.uid)])
                if employee == self.employee_id:
                    raise AccessError(
                        _("You are not allowed to approve your "
                          "attendance sheet."))

        if 'employee_id' in vals:
            new_user_id = self.env['hr.employee'].browse(
                vals['employee_id']).user_id.id
            if not new_user_id:
                raise UserError(_(
                    'In order to create a timesheet for this employee,'
                    ' you must link him/her to a user.'))
            self._check_sheet_date(forced_user_id=new_user_id)
        return super(HrTimesheetSheet, self).write(vals)

    @api.multi
    def action_timesheet_draft(self):
        if not self.env.user.has_group('hr_timesheet.group_hr_timesheet_user'):
            raise UserError(_('Only an HR Officer or Manager can refuse '
                              'timesheets or reset them to draft.'))
        self.write({'state': 'draft'})
        return True

    @api.multi
    def action_timesheet_confirm(self):
        for sheet in self:
            sheet.check_employee_attendance_state()
            di = sheet.user_id.company_id.timesheet_max_difference
            if (abs(sheet.total_difference) <= di) or not di:
                if sheet.employee_id \
                        and sheet.employee_id.parent_id \
                        and sheet.employee_id.parent_id.user_id:
                    self.message_subscribe_users(
                        user_ids=[sheet.employee_id.parent_id.user_id.id])
            else:
                raise UserError(_(
                    'Please verify that the total difference '
                    'of the sheet is lower than %.2f.') % (di,))
        self.write({'state': 'confirm'})
        return True

    @api.multi
    def action_timesheet_done(self):
        if not self.env.user.has_group('hr_timesheet.group_hr_timesheet_user'):
            raise UserError(_(
                'Only an HR Officer or Manager can approve timesheets.'))
        if self.filtered(lambda sheet: sheet.state != 'confirm'):
            raise UserError(_("Cannot approve a non-submitted timesheet."))
        self.write({'state': 'done'})

    @api.multi
    def name_get(self):
        # week number according to ISO 8601 Calendar
        return [(r['id'], _('Week ') + str(
            datetime.strptime(r['date_from'], '%Y-%m-%d').isocalendar()[1]))
                for r in self.read(['date_from'], load='_classic_write')]

    @api.multi
    def unlink(self):
        sheets = self.read(['state', 'total_attendance'])
        for sheet in sheets:
            if sheet['state'] in ('confirm', 'done'):
                raise UserError(_('You cannot delete a timesheet which '
                                  'is already confirmed.'))
            if sheet['total_attendance'] > 0.00:
                raise UserError(_('You cannot delete a timesheet that '
                                  'has attendance entries.'))

        analytic_timesheet_toremove = self.env['account.analytic.line']
        for sheet in self:
            analytic_timesheet_toremove += sheet.timesheet_ids.filtered(
                lambda t: not t.task_id)
        analytic_timesheet_toremove.unlink()

        return super(HrTimesheetSheet, self).unlink()

    # ------------------------------------------------
    # OpenChatter methods and notifications
    # ------------------------------------------------

    @api.multi
    def _track_subtype(self, init_values):
        if self:
            record = self[0]
            if 'state' in init_values and record.state == 'confirm':
                return 'hr_employee_time_clock.mt_timesheet_confirmed'
            elif 'state' in init_values and record.state == 'done':
                return 'hr_employee_time_clock.mt_timesheet_approved'
        return super(HrTimesheetSheet, self)._track_subtype(init_values)

    @api.model
    def _needaction_domain_get(self):
        empids = self.env['hr.employee'].search(
            [('parent_id.user_id', '=', self.env.uid)])
        if not empids:
            return False
        return ['&', ('state', '=', 'confirm'),
                ('employee_id', 'in', empids.ids)]

    @api.depends('period_ids.total_attendance', 'period_ids.total_timesheet',
                 'period_ids.total_difference')
    def _compute_total(self):
        """ Compute the attendances, analytic lines timesheets and differences
            between them for all the days of a timesheet and the current day
        """
        if len(self.ids) == 0:
            return

        self.env.cr.execute("""
                SELECT sheet_id as id,
                       sum(total_attendance) as total_attendance,
                       sum(total_timesheet) as total_timesheet,
                       sum(total_difference) as  total_difference
                FROM hr_timesheet_sheet_sheet_day
                WHERE sheet_id IN %s
                GROUP BY sheet_id
            """, (tuple(self.ids),))

        for x in self.env.cr.dictfetchall():
            sheet = self.browse(x.pop('id'))
            sheet.total_attendance = x.pop('total_attendance')
            sheet.total_timesheet = x.pop('total_timesheet')
            sheet.total_difference = x.pop('total_difference')

    @api.multi
    def action_sheet_report(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'HR Timesheet/Attendance Report',
            'res_model': 'hr.timesheet.attendance.report',
            'domain': [('date', '>=', self.date_from),
                       ('date', '<=', self.date_to)],
            'view_mode': 'pivot',
            'context': {'search_default_user_id': self.user_id.id, }
        }


    @api.multi
    def check_employee_attendance_state(self):
        """ Checks the attendance records of the timesheet,
            make sure they are all closed
            (by making sure they have a check_out time)
        """
        self.ensure_one()
        if any(self.attendances_ids.filtered(lambda r: not r.check_out)):
            raise UserError(_("The timesheet cannot be validated as it "
                              "contains an attendance record with no "
                              "Check Out."))
        return True


class TimesheetsByPeriod(models.Model):
    _name = "hr_timesheet_sheet.sheet.day"
    _description = "Timesheets by Period"
    _auto = False
    _order = 'name'

    name = fields.Date('Date', readonly=True)
    sheet_id = fields.Many2one('hr_timesheet_sheet.sheet', 'Sheet',
                               readonly=True, index=True)
    total_timesheet = fields.Float('Total Timesheet', readonly=True)
    total_attendance = fields.Float('Attendance', readonly=True)
    total_difference = fields.Float('Difference', readonly=True)

    _depends = {
        'account.analytic.line': ['date', 'unit_amount'],
        'hr.attendance': ['check_in', 'check_out', 'sheet_id'],
        'hr_timesheet_sheet.sheet': ['attendances_ids', 'timesheet_ids'],
    }

    @api.model_cr
    def init(self):
        self._cr.execute("""create or replace view %s as
            SELECT
                id,
                name,
                sheet_id,
                total_timesheet,
                total_attendance,
                cast(round(cast(total_attendance - total_timesheet as Numeric),2) as Double Precision) AS total_difference
            FROM
                ((
                    SELECT
                        MAX(id) as id,
                        name,
                        sheet_id,
                        timezone,
                        SUM(total_timesheet) as total_timesheet,
                        SUM(total_attendance) /60 as total_attendance
                    FROM
                        ((
                            select
                                min(l.id) as id,
                                p.tz as timezone,
                                l.date::date as name,
                                s.id as sheet_id,
                                sum(l.unit_amount) as total_timesheet,
                                0.0 as total_attendance
                            from
                                account_analytic_line l
                                LEFT JOIN hr_timesheet_sheet_sheet s ON s.id = l.sheet_id
                                JOIN hr_employee e ON s.employee_id = e.id
                                JOIN resource_resource r ON e.resource_id = r.id
                                LEFT JOIN res_users u ON r.user_id = u.id
                                LEFT JOIN res_partner p ON u.partner_id = p.id
                            group by l.date::date, s.id, timezone
                        ) union (
                            select
                                -min(a.id) as id,
                                p.tz as timezone,
                                (a.check_in AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC'))::date as name,
                                s.id as sheet_id,
                                0.0 as total_timesheet,
                                SUM(DATE_PART('day', (a.check_out AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC'))
                                                      - (a.check_in AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC')) ) * 60 * 24
                                    + DATE_PART('hour', (a.check_out AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC'))
                                                         - (a.check_in AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC')) ) * 60
                                    + DATE_PART('minute', (a.check_out AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC'))
                                                           - (a.check_in AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC')) )) as total_attendance
                            FROM
                                hr_attendance AS a
                                LEFT JOIN hr_timesheet_sheet_sheet s
                                ON s.id = a.sheet_id
                                JOIN hr_employee e
                                ON a.employee_id = e.id
                                JOIN resource_resource r
                                ON e.resource_id = r.id
                                LEFT JOIN res_users u
                                ON r.user_id = u.id
                                LEFT JOIN res_partner p
                                ON u.partner_id = p.id
                            WHERE check_out IS NOT NULL
                            group by (a.check_in AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC'))::date, s.id, timezone
                        )) AS foo
                        GROUP BY name, sheet_id, timezone
                )) AS bar""" % self._table)
