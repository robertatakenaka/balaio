# coding: utf-8
import sys
import xml.etree.ElementTree as etree

import plumber

import utils
import notifier
from models import Attempt

STATUS_OK = 'ok'
STATUS_WARNING = 'w'
STATUS_ERROR = 'e'


def has_element(etree, xpath):
    """
    Returns [STATUS_OK, ''] if ``xpath`` exists
    Returns [STATUS_ERROR, ``xpath`` not found] if ``xpath`` exists
    """
    status = STATUS_OK if etree.findall(xpath) != [] else STATUS_ERROR
    description = '' if status == STATUS_OK else xpath + ' not found'
    return [status, description]


def attrib_value(etree, xpath, attr_name):
    nodes = etree.findall(xpath)
    values = [node.attrib[attr_name] for node in nodes if attr_name in node.attrib.keys()]
    return None if values is [] else values[0] if len(values) == 1 else values


def key_value(dictionary, key):
    return dictionary[key] if key in dictionary.keys() else None


def format_description(xpath, found_value, matched, expected=''):
    if expected != '':
        expected = '. Expected value is ' + expected
    return xpath + ' not found' if found_value is None else found_value + ' is invalid value for ' + xpath + expected if not matched else ''


def join_results(results):
    status = any((result[0] for result in results if result[0] == STATUS_ERROR))
    status = STATUS_ERROR if status is True else STATUS_OK
    description = [result[1] for result in results if result[1] != '']
    return [status, '\n'.join(description)]


class ValidationPipe(plumber.Pipe):
    """
    Specialized Pipe which validates the data and notifies the result
    """
    def __init__(self, data, notifier_dep=notifier.Notifier):
        super(ValidationPipe, self).__init__(data)
        self._notifier = notifier_dep

    def transform(self, data):
        # data = (Attempt, PackageAnalyzer)
        # PackagerAnalyzer.xml
        attempt, package_analyzer = data

        result_status, result_description = self.validate(package_analyzer)

        message = {
            'stage': self._stage_,
            'status': result_status,
            'description': result_description,
        }

        self._notifier.validation_event(message)

        return data


class FundingCheckingPipe(ValidationPipe):
    """
    Check the absence/presence of funding-group and ack in the document

    funding-group is a mandatory element only if there is contract or project number
    in the document. Sometimes this information comes in Acknowledgments section.
    Return
    [STATUS_ERROR, ack]           if no founding-group, but Acknowledgments (ack) has number
    [STATUS_OK, founding-group]   if founding-group is present
    [STATUS_OK, ack]              if no founding-group, but Acknowledgments has no numbers
    [STATUS_WARNING, 'no funding-group and no ack'] if founding-group and Acknowledgments (ack) are absents
    """
    _stage_ = 'funding-group'

    def validate(self, package_analyzer):

        data = package_analyzer.xml

        funding_nodes = data.findall('.//funding-group')

        status, description = [STATUS_OK, etree.tostring(funding_nodes[0])] if funding_nodes != [] else [STATUS_WARNING, 'no funding-group']
        if not status == STATUS_OK:
            ack_node = data.findall('.//ack')
            description = etree.tostring(ack_node[0]) if ack_node != [] else 'no funding-group and no ack'
            status = STATUS_ERROR if self._contains_number(description) else STATUS_OK if description != 'no funding-group and no ack' else STATUS_WARNING
        return [status, description]

    def _contains_number(self, text):
        # if text contains any number
        return any((True for n in xrange(10) if str(n) in text))


class ArticleTypeValidationPipe(ValidationPipe):
    """
    Check @article-type
    Expected values and dependences on other elements/attributes:

    No dependences:
        abstract, addendum, brief-report, case-report, data-paper, discussion, introduction, news, obituary, oration, other, research-article, review-article
    Depending on related-article:
        @article-type:
            article-commentary, correction, editorial, expression-of-concern, in-brief, letter, reply, retraction,
        @related-article-type:
            commentary-article, corrected-article, commentary-article, object-of-concern, article-reference, commentary-article, letter, retracted-article
    Depending on product:
        book-review, product-review,
    Especific validations:
        meeting reports or abstracts
        reply to letter
        reply_as_independent_article
        editorial
        letter
    """
    _stage_ = '@article-type'
    _no_dep_ = [
        'abstract',
        'addendum',
        'brief-report',
        'case-report',
        'data-paper',
        'discussion',
        'introduction',
        'news',
        'obituary',
        'oration',
        'other',
        'research-article',
        'review-article',
    ]
    _dep_related = {
        'retraction': 'retracted-article',
        'editorial': 'commentary-article',
        'article-commentary': 'commentary-article',
        'in-brief': 'article-reference',
        'expression-of-concern': 'object-of-concern',
        'letter': 'commentary-article',
        'reply': 'letter',
        'correction': 'corrected-article',
    }
    _other_validations = {
        'book-review': '_validate_book_review',
        'product-review': '_validate_product_review',
        'meeting-report': '_validate_meeting_reports_or_abstracts',
        'reply': '_validate_reply',
        'editorial': '_validate_editorial',
        'letter': '_validate_letter',
    }

    def validate(self, package_analyzer):
        data = package_analyzer.xml
        results = []

        # get value of @article-type and check if it is valid
        article_type = attrib_value(data, '.', 'article-type')
        is_valid = self.is_valid(article_type)
        description = format_description('@article-type', article_type, is_valid)
        status = STATUS_OK if is_valid else STATUS_ERROR       

        # validates according to the article type
        if article_type in self._other_validations.keys():
            self._other_validations = {
                'book-review': self._validate_book_review,
                'product-review': self._validate_product_review,
                'meeting-report': self._validate_meeting_reports_or_abstracts,
                'reply': self._validate_reply,
                'editorial': self._validate_editorial,
                'letter': self._validate_letter,
            }
            status, description = self._other_validations[article_type](data)
        else:
            status, description = self._validate_dependence(data, article_type)

        return [status, description]

    def is_valid(self, article_type):
        """
        Return True if @article-type is valid
        """
        return article_type in self._no_dep_ or article_type in self._dep_related.keys() or article_type in self._other_validations.keys()

    def _validate_dependence(self, data, article_type):
        related_article_dep = key_value(self._dep_related, article_type)
        if not related_article_dep is None:
            related_article_type = attrib_value(data, './/article-meta/related-article', 'related-article-type')
            is_valid = related_article_type == related_article_dep
            description = format_description('@related-article-type', related_article_type, is_valid, related_article_dep)
            status = STATUS_OK if is_valid else STATUS_ERROR
        return [status, description]

    def _validate_book_review(self, data, article_type):
        results = {}
        results.append(self._validate_dependence(data, article_type))
        results.append(has_element(data, './/article-meta/product'))
        return join_results(results)

    def _validate_product_review(self, data, article_type):
        results = {}
        results.append(self._validate_dependence(data, article_type))
        results.append(has_element(data, './/article-meta/product'))
        return join_results(results)

    def _validate_editorial(self, data, article_type):
        results = {}
        results.append(self._validate_dependence(data, article_type))
        results.append(has_element(data, './/body//sig'))
        return join_results(results)

    def _validate_letter(self, data, article_type):
        # @article-type='letter'
        # related-article/@related-article-type='commentary-article'
        # contrib-group
        # signature
        results = []
        results.append(self._validate_dependence(data, article_type))
        results.append(has_element(data, './/body//sig'))
        results.append(has_element(data, './/article-meta/contrib-group'))

        return join_results(results)

    def _validate_reply(self, data, article_type):
        # @article-type='reply'
        # related-article/@related-article-type='letter'
        # contrib-group
        # signatures
        results = []
        results.append(self._validate_dependence(data, article_type))
        results.append(has_element(data, './/body//sig'))
        results.append(has_element(data, './/article-meta/contrib-group'))

        return join_results(results)

    def _validate_meeting_reports_or_abstracts(self, data, article_type):
        # @article-type='meeting-report'
        # name of conference in article-title
        # The <article-meta> should contain article citation information, but should not include author information.
        # Tag each abstract in a separate <sub-article> with <title> of the presentation/paper abstract. The full citation of the abstract, including author/presenter should be captured in the <front-stub> of the <sub-article>.
        # The pagination tagged in the <front-stub>must reflect the actual pages on which the individual abstract appears. This will not always be the same as the parent <article> pagination.
        status = STATUS_OK
        description = ''
        return [status, description]


ppl = plumber.Pipeline(FundingCheckingPipe)

if __name__ == '__main__':
    messages = utils.recv_messages(sys.stdin, utils.make_digest)
    try:
        results = [msg for msg in ppl.run(messages)]
    except KeyboardInterrupt:
        sys.exit(0)
