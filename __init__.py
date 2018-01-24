# This file is part galatea_cms module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from . import cms


def register():
    Pool.register(
        cms.Menu,
        cms.Block,
        cms.Article,
        cms.ArticleBlock,
        cms.ArticleWebsite,
        cms.Carousel,
        cms.CarouselItem,
        module='galatea_cms', type_='model')
