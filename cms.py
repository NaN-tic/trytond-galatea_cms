# This file is part galatea_cms module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import ModelSQL, ModelView, fields, tree
from trytond.pool import Pool
from trytond.pyson import Bool, Equal, Eval, In, Not
from trytond import backend
from trytond.i18n import gettext
from trytond.modules.galatea.resource import GalateaVisiblePage
from trytond.modules.galatea.tools import slugify
from trytond.transaction import Transaction
from .exceptions import DeleteWarning

__all__ = ['Menu', 'Article', 'ArticleBlock', 'ArticleWebsite', 'Block',
    'Carousel', 'CarouselItem']

_TITLE_STYLE = [
    (None, ''),
    ('h1', 'H1'),
    ('h2', 'H2'),
    ('h3', 'H3'),
    ('h4', 'H4'),
    ('h5', 'H5'),
    ('h6', 'H6'),
    ]
_BLOCK_TYPES = [
    ('image', 'Image'),
    ('remote_image', 'Remote Image'),
    ('custom_code', 'Custom Code'),
    ('section_description', 'Section Description'),
    ]
_BLOCK_COVER_IMAGE_DOMAIN = [
    ('resource', '=', Eval('attachment_resource')),
    ]
_BLOCK_COVER_IMAGE_STATES = {
    'readonly': Eval('id', 0) <= 0,
    }
_BLOCK_COVER_IMAGE_CONTEXT = {
    'resource': Eval('attachment_resource'),
    }
_BLOCK_COVER_IMAGE_DEPENDS = ['attachment_resource']
_BLOCK_TITLE_REQUIRED = ['section_description']


class Menu(tree(), ModelSQL, ModelView):
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
    hidden_xs = fields.Boolean('Hidden XS',
        help='Hidden Extra small devices')
    hidden_sm = fields.Boolean('Hidden SM',
        help='Hidden Small devices')
    hidden_md = fields.Boolean('Hidden MD',
        help='Hidden Medium devices')
    hidden_lg = fields.Boolean('Hidden LG',
        help='Hidden Large devices')
    image = fields.Many2One('ir.attachment', 'Image',
        domain=[
            ('resource.id', '=', Eval('id'), 'galatea.cms.menu')
            ])

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


class Article(GalateaVisiblePage):
    "Article CMS"
    __name__ = 'galatea.cms.article'
    _table = None  # Needed to reset GalateaVisiblePage._table
    websites = fields.Many2Many('galatea.cms.article-galatea.website',
        'article', 'website', 'Websites', required=True)
    description = fields.Text('Description', translate=True,
        help='You could write wiki or RST markups to create html content.')
    description_html = fields.Function(fields.Text('Description HTML'),
        'on_change_with_description_html')
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
    show_title = fields.Boolean('Show Title')

    @classmethod
    def __setup__(cls):
        super(Article, cls).__setup__()

        domain_clause = ('allowed_models.model', 'in', ['galatea.cms.article'])
        if domain_clause not in cls.template.domain:
            cls.template.domain.append(domain_clause)

    @classmethod
    def __register__(cls, module_name):
        TableHandler = backend.get('TableHandler')
        table = TableHandler(cls, module_name)

        super(Article, cls).__register__(module_name)

        table.not_null_action('galatea_website', action='remove')
        table.not_null_action('template', action='remove')

    @classmethod
    def view_attributes(cls):
        return super(Article, cls).view_attributes() + [
            ('//page[@id="descriptions"]/group[@id="description_html"]', 'states', {
                    'invisible': Eval('markup'),
                    }),
            ('//page[@id="descriptions"]/group[@id="description"]', 'states', {
                    'invisible': ~Eval('markup'),
                    }),
            ]

    @classmethod
    def default_websites(cls):
        Website = Pool().get('galatea.website')
        websites = Website.search([('active', '=', True)])
        return [w.id for w in websites]

    @staticmethod
    def default_show_title():
        return True

    @fields.depends('description')
    def on_change_with_description_html(self, name=None):
        if self.description:
            return self.description

    @classmethod
    def calc_uri_vals(cls, record_vals):
        # TODO: calc parent and template?
        uri_vals = super(Article, cls).calc_uri_vals(record_vals)
        if 'template' in record_vals:
            uri_vals['template'] = record_vals['template']
        return uri_vals

    @classmethod
    def delete(cls, articles):
        raise DeleteWarning('delete_articles',
            gettext('galatea_cms.msg_delete_articles'))
        super(Article, cls).delete(articles)

    @property
    def slug_langs(self):
        '''Return dict slugs by llanguage'''
        pool = Pool()
        Lang = pool.get('ir.lang')
        langs = Lang.search([
            ('active', '=', True),
            ('translatable', '=', True),
            ])
        slugs = {}
        for lang in langs:
            with Transaction().set_context(language=lang.code):
                slugs[lang.code] = self.__class__(self.id).slug
        return slugs


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
    type = fields.Selection(_BLOCK_TYPES, 'Type', required=True)
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
        states={
            'invisible': Not(In(Eval('type'), ['image', 'remote_image']))
            })
    width = fields.Integer('Width',
        states={
            'invisible': Not(In(Eval('type'), ['image', 'remote_image']))
            })
    alternative_text = fields.Char('Alternative Text',
        states={
            'invisible': Not(In(Eval('type'), ['image', 'remote_image']))
            })
    click_url = fields.Char('Click URL', translate=True,
        states={
            'invisible': Not(In(Eval('type'), ['image', 'remote_image']))
            })
    active = fields.Boolean('Active', select=True)
    attachments = fields.One2Many('ir.attachment', 'resource', 'Attachments')
    visibility = fields.Selection([
            ('public', 'Public'),
            ('register', 'Register'),
            ('manager', 'Manager'),
            ], 'Visibility', required=True)
    css = fields.Char('CSS',
        help='Seperated styles by a space')
    title = fields.Char('Title', translate=True,
        states={
            'required': Eval('type').in_(_BLOCK_TITLE_REQUIRED),
            }, depends=['type'])
    title_headings = fields.Selection(_TITLE_STYLE, 'Title Headings')
    show_title = fields.Boolean('Show Title')
    paragraph1 = fields.Text('Paragraph 1', translate=True)
    paragraph2 = fields.Text('Paragraph 2', translate=True)
    paragraph3 = fields.Text('Paragraph 3', translate=True)
    paragraph4 = fields.Text('Paragraph 4', translate=True)
    paragraph5 = fields.Text('Paragraph 5', translate=True)
    markup = fields.Selection([
            (None, ''),
            ('wikimedia', 'WikiMedia'),
            ('rest', 'ReStructuredText'),
            ], 'Markup')
    attachment_resource = fields.Function(fields.Char('Attachment Resource'),
        'get_attachment_resource')
    cover_image1 = fields.Many2One('ir.attachment', 'Cover Image 1',
        domain=_BLOCK_COVER_IMAGE_DOMAIN,
        states=_BLOCK_COVER_IMAGE_STATES,
        context=_BLOCK_COVER_IMAGE_CONTEXT,
        depends=_BLOCK_COVER_IMAGE_DEPENDS)
    cover_image2 = fields.Many2One('ir.attachment', 'Cover Image 2',
        domain=_BLOCK_COVER_IMAGE_DOMAIN,
        states=_BLOCK_COVER_IMAGE_STATES,
        context=_BLOCK_COVER_IMAGE_CONTEXT,
        depends=_BLOCK_COVER_IMAGE_DEPENDS)
    cover_image3 = fields.Many2One('ir.attachment', 'Cover Image 3',
        domain=_BLOCK_COVER_IMAGE_DOMAIN,
        states=_BLOCK_COVER_IMAGE_STATES,
        context=_BLOCK_COVER_IMAGE_CONTEXT,
        depends=_BLOCK_COVER_IMAGE_DEPENDS)
    cover_image4 = fields.Many2One('ir.attachment', 'Cover Image 4',
        domain=_BLOCK_COVER_IMAGE_DOMAIN,
        states=_BLOCK_COVER_IMAGE_STATES,
        context=_BLOCK_COVER_IMAGE_CONTEXT,
        depends=_BLOCK_COVER_IMAGE_DEPENDS)
    cover_image5 = fields.Many2One('ir.attachment', 'Cover Image 5',
        domain=_BLOCK_COVER_IMAGE_DOMAIN,
        states=_BLOCK_COVER_IMAGE_STATES,
        context=_BLOCK_COVER_IMAGE_CONTEXT,
        depends=_BLOCK_COVER_IMAGE_DEPENDS)
    cover_image_align = fields.Selection([
            (None, 'None'),
            ('top', 'Top'),
            ('bottom', 'Bottom'),
            ('right', 'Right'),
            ('left', 'Left'),
            ], 'Cover Image Align')
    total_cover_images = fields.Function(fields.Integer('Total Cover Images'),
        'on_change_with_total_cover_images')

    @staticmethod
    def default_active():
        return True

    @staticmethod
    def default_type():
        return 'custom_code'

    @staticmethod
    def default_visibility():
        return 'public'

    @staticmethod
    def default_show_title():
        return True

    @fields.depends('name', 'code')
    def on_change_name(self):
        if self.name and not self.code:
            self.code = slugify(self.name)

    @fields.depends('cover_image1', 'cover_image2', 'cover_image3',
        'cover_image4', 'cover_image5')
    def on_change_with_total_cover_images(self, name=None):
        total = 0
        if self.cover_image1:
            total += 1
        if self.cover_image2:
            total += 1
        if self.cover_image3:
            total += 1
        if self.cover_image4:
            total += 1
        if self.cover_image5:
            total += 1
        return total

    def get_attachment_resource(self, name):
        if self.id:
            return 'galatea.cms.block,%s' % self.id
        return 'galatea.cms.block,-1'


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

    @fields.depends('name', 'code')
    def on_change_name(self):
        if self.name and not self.code:
            self.code = slugify(self.name)


class CarouselItem(ModelSQL, ModelView):
    "Carousel Item CMS"
    __name__ = 'galatea.cms.carousel.item'
    carousel = fields.Many2One(
        'galatea.cms.carousel', "Carousel", required=True)
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
