# This file is part galatea_cms module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import Pool
from trytond.pyson import Bool, Equal, Eval, In, Not
from trytond.transaction import Transaction

from trytond.modules.galatea import GalateaVisiblePage
from trytond.modules.galatea.tools import slugify

__all__ = ['Menu', 'Article', 'ArticleWebsite', 'Block',
    'Carousel', 'CarouselItem']


class Menu(ModelSQL, ModelView):
    "Menu CMS"
    __name__ = 'galatea.cms.menu'
    _rec_name = 'name_used'

    name = fields.Char('Name', translate=True, states={
            'readonly': Eval('name_uri', False),
            }, depends=['name_uri'])
    name_uri = fields.Boolean('Use URI\'s name', states={
            'invisible': ((Eval('target_type', '') != 'internal_uri')
                | ~Bool(Eval('target_uri'))),
            }, depends=['target_type', 'target_uri'])
    name_used = fields.Function(fields.Char('Name', translate=True,
            required=True),
        'on_change_with_name', searcher='search_name_used')
    code = fields.Char('Code', required=True,
        help='Internal code.')
    target_type = fields.Selection([
            ('internal_uri', 'Internal URI'),
            ('external_url', 'External URL'),
            ], 'Type', required=True)
    target_uri = fields.Many2One('galatea.uri', 'Target URI', states={
            'invisible': Eval('target_type', '') != 'internal_uri',
            }, depends=['target_uri'])
    target_url = fields.Char('Target URL', states={
            'invisible': Eval('target_type', '') != 'external_url',
            }, depends=['target_type'])
    parent = fields.Many2One("galatea.cms.menu", "Parent", select=True)
    left = fields.Integer('Left', required=True, select=True)
    right = fields.Integer('Right', required=True, select=True)
    childs = fields.One2Many('galatea.cms.menu', 'parent', 'Children')
    sequence = fields.Integer('Sequence')
    nofollow = fields.Boolean('Nofollow',
        help='Add attribute in links to not search engines continue')
    active = fields.Boolean('Active', select=True)
    # TODO: add website field? add domain in target_uri parent
    # TODO: I think next fields should go to another module
    css = fields.Char('CSS',
        help='Class CSS in menu.')
    icon = fields.Char('Icon',
        help='Icon name show in menu.')
    login = fields.Boolean('Login', help='Allow login users')
    manager = fields.Boolean('Manager', help='Allow manager users')

    @fields.depends('name_uri', 'target_uri', 'name')
    def on_change_with_name(self, name=None):
        return (self.target_uri.name if self.name_uri and self.target_uri
            else self.name)

    @classmethod
    def search_name_used(cls, name, clause):
        return [
            ['OR', [
                ('name_uri', '=', True),
                ('target_uri.name',) + tuple(clause[1:]),
                ], [
                ('name_uri', '=', False),
                ('name',) + tuple(clause[1:]),
                ]],
            ]

    @staticmethod
    def default_left():
        return 0

    @staticmethod
    def default_right():
        return 0

    @staticmethod
    def default_sequence():
        return 1

    @staticmethod
    def default_active():
        return True

    @classmethod
    def __setup__(cls):
        super(Menu, cls).__setup__()
        cls._order.insert(0, ('sequence', 'ASC'))
        cls._order.insert(1, ('id', 'ASC'))

    @classmethod
    def validate(cls, menus):
        super(Menu, cls).validate(menus)
        cls.check_recursion(menus)

    @classmethod
    def copy(cls, menus, default=None):
        if default is None:
            default = {}

        default['left'] = 0
        default['right'] = 0

        # new_menus = []
        # for menu in menus:
        #     new_menu, = super(Menu, cls).copy([menu], default=default)
        #     new_menus.append(new_menu)
        # return new_menus
        return super(Menu, cls).copy(menus, default=default)


class Article(GalateaVisiblePage, ModelSQL, ModelView):
    "Article CMS"
    __name__ = 'galatea.cms.article'
    websites = fields.Many2Many('galatea.cms.article-galatea.website',
        'article', 'website', 'Websites', required=True)
    description = fields.Text('Description', required=True, translate=True,
        help='You could write wiki markup to create html content. Formats '
        'text following the MediaWiki '
        '(http://meta.wikimedia.org/wiki/Help:Editing) syntax.')
    markup = fields.Selection([
            (None, ''),
            ('wikimedia', 'WikiMedia'),
            ('rest', 'ReStructuredText'),
            ], 'Markup')
    metadescription = fields.Char('Meta Description', translate=True,
        help='Almost all search engines recommend it to be shorter '
        'than 155 characters of plain text')
    metakeywords = fields.Char('Meta Keywords', translate=True,
        help='Separated by comma')
    metatitle = fields.Char('Meta Title', translate=True)
    attachments = fields.One2Many('ir.attachment', 'resource', 'Attachments')

    @classmethod
    def __setup__(cls):
        super(Article, cls).__setup__()

        domain_clause = ('allowed_models.model', 'in', ['galatea.cms.article'])
        if domain_clause not in cls.template.domain:
            cls.template.domain.append(domain_clause)

        cls._error_messages.update({
            'delete_articles': ('You can not delete '
                'articles because you will get error 404 NOT Found. '
                'Dissable active field.'),
            })

    @classmethod
    def default_websites(cls):
        Website = Pool().get('galatea.website')
        websites = Website.search([('active', '=', True)])
        return [w.id for w in websites]

    @classmethod
    def calc_uri_vals(cls, record_vals):
        # TODO: calc parent and template?
        uri_vals = super(Article, cls).calc_uri_vals(record_vals)
        if 'template' in record_vals:
            uri_vals['template'] = record_vals['template']
        return uri_vals

    @classmethod
    def delete(cls, articles):
        if Transaction().user != 1:
            # TODO: change by a user warning
            cls.raise_user_error('delete_articles')
        super(Article, cls).delete(articles)


class ArticleWebsite(ModelSQL):
    'Galatea CMS Article - Website'
    __name__ = 'galatea.cms.article-galatea.website'
    article = fields.Many2One('galatea.cms.article', 'Article',
        ondelete='CASCADE', select=True, required=True)
    website = fields.Many2One('galatea.website', 'Website',
        ondelete='RESTRICT', select=True, required=True)


class Block(ModelSQL, ModelView):
    "Block CMS"
    __name__ = 'galatea.cms.block'
    name = fields.Char('Name', required=True,
        on_change=['name', 'code', 'slug'])
    code = fields.Char('Code', required=True, help='Internal code.')
    type = fields.Selection([
        ('image', 'Image'),
        ('remote_image', 'Remote Image'),
        ('custom_code', 'Custom Code'),
        ], 'Type', required=True)
    file = fields.Many2One('galatea.static.file', 'File', states={
            'required': Equal(Eval('type'), 'image'),
            'invisible': Not(Equal(Eval('type'), 'image'))
            })
    remote_image_url = fields.Char('Remote Image URL', states={
            'required': Equal(Eval('type'), 'remote_image'),
            'invisible': Not(Equal(Eval('type'), 'remote_image'))
            })
    custom_code = fields.Text('Custom Code', translate=True,
        states={
            'required': Equal(Eval('type'), 'custom_code'),
            'invisible': Not(Equal(Eval('type'), 'custom_code'))
            },
        help='You could write wiki markup to create html content. Formats text following '
        'the MediaWiki (http://meta.wikimedia.org/wiki/Help:Editing) syntax.')
    height = fields.Integer('Height',
        states = {
            'invisible': Not(In(Eval('type'), ['image', 'remote_image']))
            })
    width = fields.Integer('Width',
        states = {
            'invisible': Not(In(Eval('type'), ['image', 'remote_image']))
            })
    alternative_text = fields.Char('Alternative Text',
        states = {
            'invisible': Not(In(Eval('type'), ['image', 'remote_image']))
            })
    click_url = fields.Char('Click URL', translate=True,
        states = {
            'invisible': Not(In(Eval('type'), ['image', 'remote_image']))
            })
    active = fields.Boolean('Active', select=True)
    attachments = fields.One2Many('ir.attachment', 'resource', 'Attachments')
    visibility = fields.Selection([
            ('public','Public'),
            ('register','Register'),
            ('manager','Manager'),
            ], 'Visibility', required=True)

    @staticmethod
    def default_active():
        'Return True'
        return True

    @staticmethod
    def default_type():
        'Return Image'
        return 'image'

    @staticmethod
    def default_visibility():
        return 'public'

    def on_change_name(self):
        res = {}
        if self.name and not self.code:
            res['code'] = slugify(self.name)
        return res


class Carousel(ModelSQL, ModelView):
    "Carousel CMS"
    __name__ = 'galatea.cms.carousel'
    name = fields.Char('Name', translate=True,
        required=True, on_change=['name', 'code'])
    code = fields.Char('Code', required=True,
        help='Internal code. Use characters az09')
    active = fields.Boolean('Active', select=True)
    items = fields.One2Many('galatea.cms.carousel.item', 'carousel', 'Items')

    @staticmethod
    def default_active():
        return True

    def on_change_name(self):
        res = {}
        if self.name and not self.code:
            res['code'] = slugify(self.name)
        return res


class CarouselItem(ModelSQL, ModelView):
    "Carousel Item CMS"
    __name__ = 'galatea.cms.carousel.item'
    carousel = fields.Many2One("galatea.cms.carousel", "Carousel", required=True)
    name = fields.Char('Label', translate=True, required=True)
    link = fields.Char('Link', translate=True,
        help='URL absolute')
    image = fields.Char('Image', translate=True,
        help='Image with URL absolute')
    sublabel = fields.Char('Sublabel', translate=True,
        help='In case text carousel, second text')
    description = fields.Char('Description', translate=True,
        help='In cas text carousel, description text')
    html = fields.Text('HTML', translate=True,
        help='HTML formated item - Content carousel-inner')
    active = fields.Boolean('Active', select=True)
    sequence = fields.Integer('Sequence')

    @staticmethod
    def default_active():
        return True

    @staticmethod
    def default_sequence():
        return 1

    @classmethod
    def __setup__(cls):
        super(CarouselItem, cls).__setup__()
        cls._order.insert(0, ('sequence', 'ASC'))
        cls._order.insert(1, ('id', 'ASC'))
