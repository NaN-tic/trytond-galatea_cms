# This file is part galatea_cms module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.


def seo_lenght(string):
    '''Get first 155 characters from string'''
    if len(string) > 155:
        return '%s...' % (string[:152])
    return string
