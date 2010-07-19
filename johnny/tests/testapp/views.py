#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Views for Johnny's testapp."""

from django.shortcuts import render_to_response
from models import *

def template_queries(request):
    """Render a simple template that will perform a query."""
    books = Book.objects.all()
    return render_to_response('template_queries.html', locals())
