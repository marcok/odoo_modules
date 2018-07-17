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
import logging
_logger = logging.getLogger(__name__)


class HrTimesheetSheet(models.Model):
    _inherit = 'hr_timesheet_sheet.sheet'

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
