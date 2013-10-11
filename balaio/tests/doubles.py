# coding: utf-8
from StringIO import StringIO
import datetime
from xml.etree.ElementTree import ElementTree
import types


class Patch(object):
    """
    Helps patching instances to ease testing.
    """
    def __init__(self, target_object, target_attrname, patch, instance_method=False):
        self.target_object = target_object
        self.target_attrname = target_attrname
        if callable(patch) and instance_method:
            self.patch = types.MethodType(patch, target_object, target_object.__class__)
        else:
            self.patch = patch
        self._toggle()

    def _toggle(self):
        self._x = getattr(self.target_object, self.target_attrname)

        setattr(self.target_object, self.target_attrname, self.patch)
        self.patch = self._x

    def __enter__(self):
        return self.target_object

    def __exit__(self, *args, **kwargs):
        self._toggle()


#
# Stubs are test doubles to be used when the test does not aim
# to check inner aspects of a collaboration.
#
class ScieloAPIClientStub(object):
    def __init__(self, *args, **kwargs):
        self.journals = EndpointStub()
        self.issues = EndpointStub()

        def fetch_relations(dataset):
            return dataset
        self.fetch_relations = fetch_relations


class EndpointStub(object):

    def get(self, *args, **kwargs):
        return {}

    def filter(self, *args, **kwargs):
        return (_ for _ in range(5))

    def all(self, *args, **kwargs):
        return (_ for _ in range(5))


class NotifierStub(object):
    def __init__(self, *args, **kwargs):
        pass

    def start(self):
        pass

    def tell(self, *args, **kwargs):
        pass

    def end(self):
        pass


class PackageAnalyzerStub(object):
    def __init__(self, *args, **kwargs):
        """
        `_xml_string` needs to be patched.
        """
        self._xml_string = None
        self.checksum = '5a74db5db860f2f8e3c6a5c64acdbf04'
        self._filename = '/tmp/bla.zip'
        self.meta = {
            'journal_eissn': '1234-1234',
            'journal_pissn': '1234-4321',
            'article_title': 'foo',
        }

    @property
    def xml(self):
        etree = ElementTree()
        return etree.parse(StringIO(self._xml_string))

    def lock_package(self):
        return None

    def is_valid_package(self):
        return True


def get_ScieloAPIToolbeltStubModule():
    """
    Factory of scieloapitoolbelt modules. Using a factory
    is easier to keep the tests isolated.
    """
    sapi_tools = types.ModuleType('scieloapitoolbelt')

    def has_any(dataset):
        return True
    sapi_tools.has_any = has_any

    def get_one(dataset):
        return dataset[0]
    sapi_tools.get_one = get_one

    return sapi_tools


class ArticlePkgStub(object):
    journal_eissn = '0100-879X'
    journal_pissn = '0100-879X'

    def __init__(self, *args, **kwargs):
        self.id = 1
        self.issue_volume = '31'
        self.issue_number = '1'
        self.issue_suppl_volume = None
        self.issue_suppl_number = None
        self.journal_eissn = '0100-879X'
        self.journal_pissn = '0100-879X'

    def to_dict(self):
        return dict(id=self.id,
                    journal_pissn=self.journal_pissn,
                    journal_eissn=self.journal_eissn,
                    issue_volume=self.issue_volume,
                    issue_number=self.issue_number,
                    issue_suppl_volume=self.issue_suppl_volume,
                    issue_suppl_number=self.issue_suppl_number,
                    related_resources=[('attempts', 'Attempt', [1, 2]),
                                        ('tickets', 'Ticket', [11, 12]),
                        ]
                    )


class ValidationStub(object):
    def __init__(self, *args, **kwargs):
        self.id = 1
        self.status = 1
        self.started_at = '2013-09-18 14:11:04.129956'
        self.finished_at = None
        self.stage = 'Reference'
        self.message = 'Erro no param x...'

    def to_dict(self):
        return dict(id=self.id,
                    message=self.message,
                    stage=self.stage,
                    status=self.status,
                    started_at=str(self.started_at),
                    finished_at=self.finished_at,
                    articlepkg_id=ArticlePkgStub().id,
                    attempt_id=AttemptStub().id)


class AttemptStub(object):
    def __init__(self, *args, **kwargs):
        self.id = 1
        self.is_valid = True
        self.started_at = '2013-09-18 14:11:04.129956'
        self.finished_at = None
        self.filepath = '/tmp/foo/bar.zip'
        self.collection_uri = '/api/v1/collection/xxx/'
        self.package_checksum = 'ol9j27n3f52kne7hbn'
        self.articlepkg = ArticlePkgStub()

    def to_dict(self):
        return dict(id=self.id,
                    package_checksum=self.package_checksum,
                    articlepkg_id=ArticlePkgStub().id,
                    started_at=str(self.started_at),
                    finished_at=self.finished_at,
                    collection_uri=self.collection_uri,
                    filepath=self.filepath,
                    is_valid=self.is_valid,
                    comments=[{'author': 'Author', 'date': '2013-09-18 14:11:04.129956', 'message': 'Message'},
                    {'author': 'Author', 'date': '2013-09-18 14:11:04.129956', 'message': 'Message'},
                    {'author': 'Author', 'date': '2013-09-18 14:11:04.129956', 'message': 'Message'}]
                    )


class CommentStub(object):
    def __init__(self, *args, **kwargs):
        self.id = 1
        self.message = 'Erro no stage xxx'

    def to_dict(self):
        return dict(author='author',
                    message=self.message,
                    date='2013-09-18 14:11:04.129956'
                    )


class TicketStub(object):
    def __init__(self, *args, **kwargs):
        self.id = 1
        self.is_open = True
        self.started_at = '2013-09-18 14:11:04.129956'
        self.finished_at = None
        self.comments = [['Comment', CommentStub().id]]

    def to_dict(self):
        return dict(id=self.id,
                    is_open=self.is_open,
                    started_at=str(self.started_at),
                    finished_at=self.finished_at,
                    comments=self.comments,
                    articlepkg_id=ArticlePkgStub().id)


class ConfigStub(object):
    pass


class PipeStub(object):
    def __init__(self, data, **kwargs):
        self.data = data

    def __iter__(self):
        for i in self.data:
            yield i


class ObjectStub(object):
    pass


class QueryStub(object):
    def __init__(self, params):
        object.__init__(self)

    def scalar(self):
        return 200

    def limit(self, args):
        o = ObjectStub()
        o.offset = lambda params: []
        if self.found:
            o.offset = lambda params: [self.model(), self.model()]
        return o

    def filter_by(self, **kwargs):
        o = ObjectStub()
        o.limit = self.limit
        o.scalar = self.scalar
        return o

    def get(self, id):
        if not self.found:
            return None
        return self.model()


class DummyRoute:
    """
    Copied from pyramid.tests.test_url.DummyRoute
    """
    pregenerator = None
    name = 'route'
    def __init__(self, result='/1/2/3'):
        self.result = result

    def generate(self, kw):
        self.kw = kw
        return self.result


class DummyRoutesMapper:
    """
    Copied from pyramid.tests.test_url.DummyRoutesMapper
    """
    raise_exc = None
    def __init__(self, route=None, raise_exc=False):
        self.route = route

    def get_route(self, route_name):
        return self.route

