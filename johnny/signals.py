"""Defined signals for johnny-cache."""

from django.dispatch import Signal

# sent when the query cache finds a valid result in the cache
qc_hit = Signal(providing_args=['key', 'tables', 'query', 'size'])
# sent when the query cache cannot find a valid result in the cache
qc_miss = Signal(providing_args=['key', 'tables', 'query'])
# sent when johnny skips a statement because of blacklisting
qc_skip = Signal(providing_args=['key', 'tables', 'query'])
