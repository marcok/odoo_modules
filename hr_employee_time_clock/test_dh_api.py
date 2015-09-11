#!/usr/bin/env python

import xmlrpclib
import datetime


url = "http://localhost"
db = "db"
username = "admin"
password = 'admin'

common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(url))
print common.version()

uid = common.authenticate(db, username, password, {})
print uid

models = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(url), verbose=True)
print models.execute_kw(db, uid, password,
                  'hr_timesheet_sheet.sheet', 'attendance_analysis', [], dict(timesheet_id=1))