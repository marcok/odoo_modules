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


import pytz
from datetime import datetime, timedelta, date
from odoo import api, fields, models, _
from dateutil import rrule, parser
from odoo.tools.translate import _
import calendar
import math
import logging

_logger = logging.getLogger(__name__)


class HrContract(models.Model):
    """
        Addition plugin for HR timesheet for work with duty hours
    """
    _inherit = 'hr.contract'

    rate_per_hour = fields.Boolean(string="Use hour rate")