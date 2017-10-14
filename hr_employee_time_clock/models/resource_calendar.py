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

import datetime as dtime

from datetime import datetime
from odoo import api, fields, models, _


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    @api.multi
    def get_working_hours_of_date(self, cr, uid, ids, start_dt=None,
                                  end_dt=None, leaves=None,
                                  compute_leaves=False, resource_id=None,
                                  default_interval=None, context=None):
        """ Get the working hours of the day based on calendar. This method uses
        get_working_intervals_of_day to have the work intervals of the day. It
        then calculates the number of hours contained in those intervals. """
        res = dtime.timedelta()
        intervals = self.get_working_intervals_of_day(
            cr, uid, ids,
            start_dt, end_dt, leaves,
            compute_leaves, resource_id,
            default_interval, context)
        for interval in intervals:
            res += interval[1] - interval[0]
        return seconds(res) / 3600.0

    @api.multi
    def get_working_intervals_of_day(self, cr, uid, ids, start_dt=None,
                                     end_dt=None, leaves=None,
                                     compute_leaves=False, resource_id=None,
                                     default_interval=None, context=None):

        if isinstance(ids, (list, tuple)):
            ids = ids[0]
        work_limits = []
        if start_dt is None and end_dt is not None:
            start_dt = end_dt.replace(hour=0, minute=0, second=0)
        elif start_dt is None:
            start_dt = datetime.now().replace(hour=0, minute=0, second=0)
        else:
            work_limits.append((start_dt.replace(
                hour=0, minute=0, second=0), start_dt))
        if end_dt is None:
            end_dt = start_dt.replace(hour=23, minute=59, second=59)
        else:
            work_limits.append((end_dt, end_dt.replace(
                hour=23, minute=59, second=59)))
        assert start_dt.date() == end_dt.date(), \
            'get_working_intervals_of_day is restricted to one day'
        intervals = []
        work_dt = start_dt.replace(hour=0, minute=0, second=0)

        # no calendar: try to use the default_interval, then return directly
        if ids is None:
            working_interval = []
            if default_interval:
                working_interval = (
                    start_dt.replace(hour=default_interval[0],
                                     minute=0, second=0),
                    start_dt.replace(hour=default_interval[1],
                                     minute=0, second=0))
            intervals = self.interval_remove_leaves(working_interval,
                                                    work_limits)
            return intervals

        working_intervals = []
        for calendar_working_day in self.get_attendances_for_weekdays(
                ids, [start_dt.weekday()]):
            working_interval = (
                work_dt.replace(hour=int(calendar_working_day.hour_from)),
                work_dt.replace(hour=int(calendar_working_day.hour_to))
            )
            working_intervals += self.interval_remove_leaves(working_interval,
                                                             work_limits)
        # find leave intervals
        if leaves is None and compute_leaves:
            leaves = self.get_leave_intervals(cr, uid, ids,
                                              resource_id=resource_id,
                                              context=context)

        # filter according to leaves
        for interval in working_intervals:
            work_intervals = self.interval_remove_leaves(interval, leaves)
            intervals += work_intervals
        return intervals

    @api.multi
    def get_attendances_for_weekdays(self, ids, weekdays):
        """ Given a list of weekdays, return matching
        resource.calendar.attendance"""
        calendar = self.browse(ids)
        return [att for att in calendar.attendance_ids
                if int(att.dayofweek) in weekdays]


def seconds(td):
    assert isinstance(td, dtime.timedelta)

    return (td.microseconds + (
        td.seconds + td.days * 24 * 3600) * 10 ** 6) / 10. ** 6
