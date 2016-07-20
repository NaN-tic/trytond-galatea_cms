# This file is part galatea_cms module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import Pool
from trytond.pyson import Bool, Equal, Eval, In, Not
from trytond import backend

from trytond.modules.galatea import GalateaVisiblePage
from trytond.modules.galatea.tools import slugify

__all__ = ['Menu', 'Article', 'ArticleBlock', 'ArticleWebsite', 'Block',
    'Carousel', 'CarouselItem']


class Menu(ModelSQL, ModelView):
    "Menu CMS"
    __name__ = 'galatea.cms.menu'
    _rec_name = 'name_used'
    _order = [('parent', 'ASC'), ('sequence', 'ASC'), ('id', 'ASC')]

    website = fields.Many2One('galatea.website', 'Website',
        ondelete='RESTRICT', select=True, required=True)
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
            }, domain=[
            ('website', '=', Eval('website')),
            ], depends=['target_uri', 'website'])
    target_url = fields.Char('Target URL', states={
            'invisible': Eval('target_type', '') != 'external_url',
            }, depends=['target_type'])
    url = fields.Function(fields.Char('URL'),
        'get_url')
    parent = fields.Many2One('galatea.cms.menu', 'Parent', domain=[
            ('website', '=', Eval('website')),
            ], depends=['website'], select=True)
    left = fields.Integer('Left', required=True, select=True)
    right = fields.Integer('Right', required=True, select=True)
    childs = fields.One2Many('galatea.cms.menu', 'parent', 'Children')
    sequence = fields.Integer('Sequence')
    nofollow = fields.Boolean('Nofollow',
        help='Add attribute in links to not search engines continue')
    active = fields.Boolean('Active', select=True)
    # TODO: I think the following fields should go to another module
    css = fields.Char('CSS',
        help='Class CSS in menu.')
    icon = fields.Char('Icon',
        help='Icon name show in menu.')
    login = fields.Boolean('Login', help='Allow login users')
    manager = fields.Boolean('Manager', help='Allow manager users')

    @classmethod
    def __setup__(cls):
        super(Menu, cls).__setup__()
        cls._order.insert(0, ('sequence', 'ASC'))
        cls._order.insert(1, ('id', 'ASC'))

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

    def get_url(self, name):
        return (self.target_url if self.target_type == 'external_url'
            else (self.target_uri.uri if self.target_uri else '#'))

    @classmethod
    def default_website(cls):
        Website = Pool().get('galatea.website')
        websites = Website.search([])
        if len(websites) == 1:
            return websites[0].id

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
    description = fields.Text('Description', translate=True,
        help='You could write wiki or RST markups to create html content.')
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
    blocks = fields.One2Many('galatea.cms.article.block', 'article', 'Blocks')

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
    def __register__(cls, module_name):
        TableHandler = backend.get('TableHandler')
        table = TableHandler(cls, module_name)

        super(Article, cls).__register__(module_name)

        table.not_null_action('galatea_website', action='remove')
        table.not_null_action('template', action='remove')

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
        cls.raise_user_warning('delete_articles', 'delete_articles')
        super(Article, cls).delete(articles)


class ArticleBlock(ModelSQL, ModelView):
    "Article Block CMS"
    __name__ = 'galatea.cms.article.block'
    article = fields.Many2One('galatea.cms.article', 'Article',
        required=True)
    block = fields.Many2One('galatea.cms.block', 'Block',
        required=True)
    sequence = fields.Integer('Sequence')

    @staticmethod
    def default_sequence():
        return 1

    @classmethod
    def __setup__(cls):
        super(ArticleBlock, cls).__setup__()
        cls._order.insert(0, ('sequence', 'ASC'))


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
    name = fields.Char('Name', required=True)
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
        help='You could write wiki or RST markups to create html content.')
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
    css = fields.Char('CSS',
        help='Seperated styles by a space')
    title = fields.Char('Title', translate=True)
    paragraph1 = fields.Char('Paragraph 1', translate=True)
    paragraph2 = fields.Char('Paragraph 2', translate=True)
    paragraph3 = fields.Char('Paragraph 3', translate=True)
    paragraph4 = fields.Char('Paragraph 4', translate=True)
    paragraph5 = fields.Char('Paragraph 5', translate=True)

    @staticmethod
    def default_active():
        return True

    @staticmethod
    def default_type():
        return 'custom_code'

    @staticmethod
    def default_visibility():
        return 'public'

    @fields.depends('name', 'code')
    def on_change_name(self):
        if self.name and not self.code:
            self.code = slugify(self.name)


class Carousel(ModelSQL, ModelView):
    "Carousel CMS"
    __name__ = 'galatea.cms.carousel'
    name = fields.Char('Name', translate=True, required=True)
    code = fields.Char('Code', required=True,
        help='Internal code. Use characters az09')
    active = fields.Boolean('Active', select=True)
    items = fields.One2Many('galatea.cms.carousel.item', 'carousel', 'Items')

    @staticmethod
    def default_active():
        return True

    def on_change_name(self):
        if self.name and not self.code:
            self.code = slugify(self.name)


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
