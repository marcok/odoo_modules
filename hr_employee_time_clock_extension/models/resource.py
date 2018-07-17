# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


import pytz
from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger(__name__)


def to_tz(datetime, tz_name):
    tz = pytz.timezone(tz_name)
    return pytz.UTC.localize(datetime.replace(tzinfo=None),
                             is_dst=False).astimezone(tz).replace(tzinfo=None)


class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    use_overtime = fields.Boolean(string="Use Overtime Setting")
    min_overtime_count = fields.Integer(string="Minimum overtime days",
                                        default=0,
                                        required=True)
    count = fields.Integer(string="Percent Count",
                           default=0,
                           required=True)
    overtime_attendance_ids = fields.One2many(
        'resource.calendar.attendance.overtime',
        'overtime_calendar_id',
        string='Overtime')
    two_days_shift = fields.Boolean(string='Shift between two days',
                                    default=True,
                                    help='Use for night shift between '
                                         'two days.')

    @api.constrains('min_overtime_count')
    def _check_min_overtime_count(self):
        """Ensure that field min_overtime_count is >= 0"""
        if self.min_overtime_count < 0:
            raise ValidationError("Minimum overtime days must be positive.")

    @api.constrains('two_days_shift')
    def _check_two_days_shift(self):
        if self.two_days_shift is False:
            for attendance_id in self.overtime_attendance_ids:
                if attendance_id.hour_to <= attendance_id.hour_from:
                   raise ValidationError("Overtime to must be greater than "
                                         "overtime from when two days "
                                         "shift is not using.")

    @api.multi
    def _get_leave_intervals(self, resource_id=None,
                             start_datetime=None, end_datetime=None):
        self.ensure_one()
        if resource_id:
            domain = ['|',
                      ('resource_id', '=', resource_id),
                      ('resource_id', '=', False)]
        else:
            domain = [('resource_id', '=', False)]
        if start_datetime:
            domain += [('date_to', '>', fields.Datetime.to_string(
                start_datetime + timedelta(days=-1)))]
        if end_datetime:
            domain += [('date_from', '<',
                        fields.Datetime.to_string(start_datetime +
                                                  timedelta(days=1)))]
        leaves = self.env['resource.calendar.leaves'].search(
            domain + [('calendar_id', '=', self.id)])

        filtered_leaves = self.env['resource.calendar.leaves']
        for leave in leaves:
            if not leave.tz:
                if self.env.context.get('tz'):
                    leave.tz = self.env.context.get('tz')
                else:
                    leave.tz = 'UTC'
            if start_datetime:
                leave_date_to = to_tz(
                    fields.Datetime.from_string(leave.date_to), leave.tz)
                if not leave_date_to >= start_datetime:
                    continue
            if end_datetime:
                leave_date_from = to_tz(
                    fields.Datetime.from_string(leave.date_from), leave.tz)
                if not leave_date_from <= end_datetime:
                    continue
            filtered_leaves += leave

        return [self._interval_new(
            to_tz(fields.Datetime.from_string(leave.date_from), leave.tz),
            to_tz(fields.Datetime.from_string(leave.date_to), leave.tz),
            {'leaves': leave}) for leave in filtered_leaves]

    @api.one
    def initial_overtime(self):
        users = self.env['res.users'].search([])
        for user in users:
            if not user.tz:
                raise ValidationError(_("Timezone for {user} "
                                        "is not set.".format(user=user.name)))

        attendances = self.env['hr.attendance'].search([])

        for attendance in attendances:
            attendance.write({'check_out': attendance.check_out})


class ResourceCalendarAttendanceOvertime(models.Model):
    _name = "resource.calendar.attendance.overtime"
    _order = 'dayofweek, hour_from'

    name = fields.Char(required=True)
    dayofweek = fields.Selection([('0', 'Monday'),
                                  ('1', 'Tuesday'),
                                  ('2', 'Wednesday'),
                                  ('3', 'Thursday'),
                                  ('4', 'Friday'),
                                  ('5', 'Saturday'),
                                  ('6', 'Sunday')
                                  ],
                                 string='Day of Week',
                                 required=True,
                                 index=True,
                                 default='0')
    date_from = fields.Date(string='Starting Date')
    date_to = fields.Date(string='End Date')
    hour_from = fields.Float(string='Overtime from',
                             required=True,
                             index=True,
                             help="Start and End time of Overtime.")
    hour_to = fields.Float(string='Overtime to',
                           required=True)

    overtime_calendar_id = fields.Many2one("resource.calendar",
                                           string="Resource's Calendar",
                                           required=True,
                                           ondelete='cascade')
