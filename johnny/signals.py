#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Defined signals for johnny-cache."""

from django.dispatch import Signal

qc_hit = Signal(providing_args=['key', 'tables', 'query', 'size'])
qc_miss = Signal(providing_args=['key', 'tables', 'query'])
qc_m2m_change = Signal(providing_args=['instance'])
