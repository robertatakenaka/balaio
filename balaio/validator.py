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
    _dep_related_article = {
        'retraction': 'retracted-article',
        'editorial': 'commentary-article',
        'article-commentary': 'commentary-article',
        'in-brief': 'article-reference',
        'expression-of-concern': 'object-of-concern',
        'letter': 'commentary-article',
        'reply': 'letter',
        'correction': 'corrected-article',
    }
    _other_dep = [
        'book-review',
        'product-review',
        'meeting-report',
        'reply',
        'editorial',
        'letter',
    ]

    def validate(self, package_analyzer):
        data = package_analyzer.xml

        status = STATUS_ERROR

        is_valid_value, article_type, has_dependences = self._value(data)

        description = '@article-type not found' if article_type is None else article_type + ' is invalid value for @article-type' if not is_valid_value else ''

        if is_valid_value:

        return []

    def _value(self, data):
        """
        Find @article-type in ``data``
        Return if value is valid
        Return if has dependences
        """
        article_type = data.attrib['article-type'] if 'article-type' in data.attrib.keys() else None
        valid = [True, False] if article_type in self._no_dep_ else [True, True] if article_type in self._dep_related_article.keys() or  article_type in self._other_dep else [False, False]

        return [valid, article_type, has_dependences]

    def _validate_meeting_reports_or_abstracts(self, data):
        # @article-type='meeting-report'
        # name of conference in article-title
        # The <article-meta> should contain article citation information, but should not include author information.
        # Tag each abstract in a separate <sub-article> with <title> of the presentation/paper abstract. The full citation of the abstract, including author/presenter should be captured in the <front-stub> of the <sub-article>.
        # The pagination tagged in the <front-stub>must reflect the actual pages on which the individual abstract appears. This will not always be the same as the parent <article> pagination.
        return []

    def _validate_product(self, data):
        # product
        return []

    def _validate_related_article(self, data):
        # @article-type='??'
        # related-article/@related-article-type='??'
        return []

    def _validate_editorial(self, data):
        # @article-type='editorial'
        # related-article/@related-article-type='commentary-article'
        # signature
        return []

    def _validate_letter(self, data):
        # @article-type='letter'
        # related-article/@related-article-type='commentary-article'
        # contrib-group
        # signature
        return []

    def _validate_reply_to_letter(self, data):
        # response
        return []

    def _validate_reply_as_independent_article(self, data):
        # @article-type='reply'
        # related-article/@related-article-type='letter'
        # contrib-group
        # signatures
        return []


ppl = plumber.Pipeline(FundingCheckingPipe)

if __name__ == '__main__':
    messages = utils.recv_messages(sys.stdin, utils.make_digest)
    try:
        results = [msg for msg in ppl.run(messages)]
    except KeyboardInterrupt:
        sys.exit(0)
