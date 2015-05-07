#!/usr/bin/env python

import xmlrpclib
import datetime
from dateutil import parser

#url = "http://localhost:8069"
url = "http://217.20.187.163:8069"
#db = "stclaus_1"
db = "Hosberg"
#username = "admin"
#password = 'admin'
username = "iphone@qarea.com"
password = "iphone"

common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(url))
print common.version()

uid = common.authenticate(db, username, password, {})
print uid

models = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(url), verbose=True)
print models.execute_kw(db, uid, password,
                  'hr_timesheet_sheet.sheet', 'attendance_analysis', [], dict(employee_id= 2, start_date='2015-04-28',
                                                                              end_date='2015-04-30'))