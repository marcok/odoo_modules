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
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools.translate import _
from odoo.tools.sql import drop_view_if_exists
from odoo.exceptions import UserError, ValidationError


class HrTimesheetSheetSheetAccount(models.Model):
    _name = "hr_timesheet_sheet.sheet.account"
    _description = "Timesheet Sheet Account"
    _auto = False
    _order = 'name'

    name = fields.Many2one('account.analytic.account',
                           string='Project / Analytic Account',
                           readonly=True)
    sheet_id = fields.Many2one('hr_timesheet_sheet.sheet',
                               string='Sheet',
                               readonly=True)
    total = fields.Float('Total Time',
                         digits=(16, 2),
                         readonly=True)

    # still seing _depends in BaseModel, ok to leave this as is?
    _depends = {
        'account.analytic.line': ['account_id', 'date', 'unit_amount', 'user_id'],
        'hr_timesheet_sheet.sheet': ['date_from', 'date_to', 'user_id'],
    }

    @api.model_cr
    def init(self):
        drop_view_if_exists(self._cr, 'hr_timesheet_sheet_sheet_account')
        self._cr.execute("""create view hr_timesheet_sheet_sheet_account as (
            select
                min(l.id) as id,
                l.account_id as name,
                s.id as sheet_id,
                sum(l.unit_amount) as total
            from
                account_analytic_line l
                    LEFT JOIN hr_timesheet_sheet_sheet s
                        ON (s.date_to >= l.date
                            AND s.date_from <= l.date
                            AND s.user_id = l.user_id)
            group by l.account_id, s.id
        )""")
