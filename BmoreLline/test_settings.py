"""Isolated database for protocol tests and local preview without production writes."""
import os
from .settings import *
DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':os.environ['LIFELINE_TEST_DB']}}
EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
