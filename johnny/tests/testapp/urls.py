#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""URLconf for Johnny's test app."""

from django.conf.urls import *

urlpatterns = patterns('johnny.tests.testapp.views',
   url(r'^test/template_queries', 'template_queries'),
)
