# This file is part galatea_cms module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.cache import Cache
from trytond.pyson import Bool, Equal, Eval, Greater, In, Not

from .tools import slugify

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


class Article(ModelSQL, ModelView):
    "Article CMS"
    __name__ = 'galatea.cms.article'
    name = fields.Char('Title', translate=True, required=True)
    canonical_uri = fields.Many2One('galatea.uri', 'Canonical URI',
        required=True, select=True, domain=[
            ('website', 'in', Eval('websites')),
            ('type', '=', 'content'),
            ('template.allowed_models.model', 'in', ['galatea.cms.article']),
            ],
        states={
            'invisible': ~Greater(Eval('id', -1), 0),
            }, depends=['websites', 'id'])
    slug = fields.Function(fields.Char('Slug', translate=True, required=True),
        'on_change_with_slug', setter='set_canonical_uri_field',
        searcher='search_canonical_uri_field')
    slug_langs = fields.Function(fields.Dict(None, 'Slug Langs'),
        'get_slug_langs')
    _slug_langs_cache = Cache('galatea_cms_article.slug_langs')
    # TODO: ha d'incloure el canonical_uri o tenir alternative_uris + camp
    # funcional *uris*
    uris = fields.One2Many('galatea.uri', 'content', 'URIs', readonly=True,
        help='All article URIs')
    uri = fields.Function(fields.Many2One('galatea.uri', 'URI'),
        'get_uri', searcher='search_uri')
    # TODO: maybe websites should be a searchable functional field as sum of
    # canonical_uri/uris website field
    websites = fields.Many2Many('galatea.cms.article-galatea.website',
        'article', 'website', 'Websites', required=True,
        help='Tutorial will be available in those websites')
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
    # TODO: I think it should go to another module which implements private
    # area/portal features
    visibility = fields.Selection([
            ('public', 'Public'),
            ('register', 'Register'),
            ('manager', 'Manager'),
            ], 'Visibility', required=True, select=True)
    # TODO: extend getter/setter/searcher to all uris (is active is some uri is
    # active)
    active = fields.Function(fields.Boolean('Active',
            help='Dissable to not show content article.'),
        'get_active', setter='set_canonical_uri_field',
        searcher='search_canonical_uri_field')
    attachments = fields.One2Many('ir.attachment', 'resource', 'Attachments')

    @classmethod
    def __setup__(cls):
        super(Article, cls).__setup__()
        cls._error_messages.update({
            'delete_articles': ('You can not delete '
                'articles because you will get error 404 NOT Found. '
                'Dissable active field.'),
            })

    @fields.depends('name', 'slug')
    def on_change_name(self):
        res = {}
        if self.name and not self.slug:
            res['slug'] = slugify(self.name)
        return res

    @fields.depends('canonical_uri', 'slug')
    def on_change_with_slug(self, name=None):
        if self.canonical_uri:
            return self.canonical_uri.slug
        if self.slug:
            return slugify(self.slug)

    @classmethod
    def set_canonical_uri_field(cls, articles, name, value):
        pool = Pool()
        Uri = pool.get('galatea.uri')
        Uri.write([a.canonical_uri for a in articles if a.canonical_uri], {
                name: value,
                })

    @classmethod
    def search_canonical_uri_field(cls, name, clause):
        domain = [
            ('canonical_uri.%s' % name,) + tuple(clause[1:]),
            ]
        if clause == ['active', '=', False]:
            domain = [
                'OR',
                domain,
                [('canonical_uri', '=', None)],
                ]
        return domain

    def get_slug_langs(self, name):
        '''Return dict slugs by all languaes actives'''
        pool = Pool()
        Lang = pool.get('ir.lang')
        Article = pool.get('galatea.cms.article')

        article_id = self.id
        langs = Lang.search([
            ('active', '=', True),
            ('translatable', '=', True),
            ])

        slugs = {}
        for lang in langs:
            with Transaction().set_context(language=lang.code):
                article, = Article.read([article_id], ['slug'])
                slugs[lang.code] = article['slug']
        return slugs

    def get_uri(self, name):
        context = Transaction().context
        if context.get('website', False):
            for uri in self.uris:
                if uri.website.id == context['website']:
                    return uri.id
        return self.canonical_uri.id

    @classmethod
    def search_uri(cls, name, clause):
        context = Transaction().context
        if context.get('website', False):
            # TODO: is it better and If()?
            return [
                ['OR', [
                    ('canonical_uri',) + tuple(clause[1:]),
                    ('website', '=', context['website']),
                    ], [
                    ('uris',) + tuple(clause[1:]),
                    ('website', '=', context['website']),
                    ]],
                ]
        return [
            ['OR', [
                ('canonical_uri',) + tuple(clause[1:]),
                ], [
                ('uris',) + tuple(clause[1:]),
                ]],
            ]

    @classmethod
    def default_websites(cls):
        Website = Pool().get('galatea.website')
        websites = Website.search([('active', '=', True)])
        return [w.id for w in websites]

    @staticmethod
    def default_visibility():
        return 'public'

    @staticmethod
    def default_active():
        return True

    def get_active(self, name):
        return self.canonical_uri.active if self.canonical_uri else False

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        Uri = pool.get('galatea.uri')
        for vals in vlist:
            if not vals.get('canonical_uri'):
                assert vals.get('slug')
                assert vals.get('websites')
                uri, = Uri.create([{
                            'website': vals['websites'][0],
                            'name': vals['name'],
                            'slug': vals['slug'],
                            'type': 'content',
                            'active': vals.get('active', cls.default_active()),
                            }])
                vals['canonical_uri'] = uri.id
        new_articles = super(Article, cls).create(vlist)

        uri_args = []
        for article in new_articles:
            if not article.canonical_uri.content:
                uri_args.extend([article.canonical_uri], {
                        'content': str(article),
                        })
        if uri_args:
            Uri.write(*uri_args)
        return new_articles

    @classmethod
    def copy(cls, articles, default=None):
        pool = Pool()
        Uri = pool.get('galatea.uri')

        if default is None:
            default = {}
        else:
            default = default.copy()
        new_articles = []
        for article in articles:
            default['canonical_uri'] = Uri.copy([article.canonical_uri], {
                    'slug': '%s-copy' % article.slug,
                    })
            new_articles += super(Article, cls).copy([article],
                default=default)
        return new_articles

    @classmethod
    def write(cls, *args):
        pool = Pool()
        Uri = pool.get('galatea.uri')

        actions = iter(args)
        uri_args = []
        for articles, values in zip(actions, actions):
            if values.get('canonical_uri'):
                canonical_uri = Uri(values['canonical_uri'])
                canonical_uri.content = articles[0]
                canonical_uri.save()
            if 'name' in values:
                uri_todo = []
                for article in articles:
                    if article.canonical_uri.name == article.name:
                        uri_todo.append(article.canonical_uri)
                    for uri in article.uris:
                        if uri.name == article.name and uri not in uri_todo:
                            uri_todo.append(uri)
                if uri_todo:
                    # What happens if canonical_uri and name change?
                    uri_args.append(uri_todo)
                    uri_args.append({
                            'name': values['name'],
                            })

        super(Article, cls).write(*args)
        if uri_args:
            Uri.write(*uri_args)

    @classmethod
    def delete(cls, articles):
        cls.raise_user_error('delete_articles')


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
