# This file is part galatea_cms module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
try:
    from trytond.modules.galatea_cms.tests.test_galatea_cms import suite
except ImportError:
    from .test_galatea_cms import suite

__all__ = ['suite']
