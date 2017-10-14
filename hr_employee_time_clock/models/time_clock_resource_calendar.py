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

from datetime import datetime
import math
from odoo import fields, models, api


class TimeClockResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    @api.multi
    def get_working_intervals_of_day(self, start_dt=None, end_dt=None,
                                     leaves=None, compute_leaves=False,
                                     resource_id=None, default_interval=None):
        """ To resolve issue of 0.5h on duty hours,
        this method has to be overriden here."""

        """ Computes start_dt, end_dt (with default values if not set) +
        off-interval work limits """
        work_limits = []
        if start_dt is None and end_dt is not None:
            start_dt = end_dt.replace(hour=0, minute=0, second=0)
        elif start_dt is None:
            start_dt = datetime.datetime.now().replace(hour=0, minute=0,
                                                       second=0)
        else:
            work_limits.append(
                (start_dt.replace(hour=0, minute=0, second=0), start_dt))
        if end_dt is None:
            end_dt = start_dt.replace(hour=23, minute=59, second=59)
        else:
            work_limits.append(
                (end_dt, end_dt.replace(hour=23, minute=59, second=59)))
        assert start_dt.date() == end_dt.date(), \
            'get_working_intervals_of_day is restricted to one day'

        intervals = []
        work_dt = start_dt.replace(hour=0, minute=0, second=0)

        # no calendar: try to use the default_interval, then return directly
        if self.id is None:
            if default_interval:
                working_interval = (
                    start_dt.replace(
                        hour=default_interval[0], minute=0, second=0),
                    start_dt.replace(
                        hour=default_interval[1], minute=0, second=0))
                intervals = self.interval_remove_leaves(working_interval,
                                                        work_limits)
            if intervals:
                return intervals
            else:
                return []

        working_intervals = []
        for calendar_working_day in self.get_attendances_for_weekdays(
                [start_dt.weekday()])[0]:
            # FIXED by Addition IT Solutions: Counting
            # minutes to get result when 0.5h are added to calendar
            minutes_from = math.modf(calendar_working_day.hour_from)[0] * 60
            minutes_to = math.modf(calendar_working_day.hour_to)[0] * 60
            working_interval = (
                work_dt.replace(hour=int(calendar_working_day.hour_from),
                                minute=int(minutes_from)),
                work_dt.replace(hour=int(calendar_working_day.hour_to),
                                minute=int(minutes_to))
            )
            working_intervals += self.interval_remove_leaves(working_interval,
                                                             work_limits)
        # find leave intervals
        if leaves is None and compute_leaves:
            leaves = self.get_leave_intervals(resource_id=resource_id)

        # filter according to leaves
        for interval in working_intervals:
            work_intervals = self.interval_remove_leaves(interval, leaves)
            intervals += work_intervals

        return intervals
