#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""URLconf for Johnny's test app."""

from django.conf.urls.defaults import *

urlpatterns = patterns('johnny.tests.testapp.views',
   (r'^test/template_queries', 'template_queries'),
)

