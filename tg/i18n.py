import logging, os
from gettext import NullTranslations, translation
import tg
from tg.util import lazify
from tg._compat import PY3, string_type

log = logging.getLogger(__name__)

class LanguageError(Exception):
    """Exception raised when a problem occurs with changing languages"""
    pass

def _parse_locale(identifier, sep='_'):
    """
    Took from Babel,
    Parse a locale identifier into a tuple of the form::

      ``(language, territory, script, variant)``

    >>> parse_locale('zh_CN')
    ('zh', 'CN', None, None)
    >>> parse_locale('zh_Hans_CN')
    ('zh', 'CN', 'Hans', None)

    The default component separator is "_", but a different separator can be
    specified using the `sep` parameter:

    :see: `IETF RFC 4646 <http://www.ietf.org/rfc/rfc4646.txt>`_
    """
    if '.' in identifier:
        # this is probably the charset/encoding, which we don't care about
        identifier = identifier.split('.', 1)[0]
    if '@' in identifier:
        # this is a locale modifier such as @euro, which we don't care about
        # either
        identifier = identifier.split('@', 1)[0]

    parts = identifier.split(sep)
    lang = parts.pop(0).lower()
    if not lang.isalpha():
        raise ValueError('expected only letters, got %r' % lang)

    script = territory = variant = None
    if parts:
        if len(parts[0]) == 4 and parts[0].isalpha():
            script = parts.pop(0).title()

    if parts:
        if len(parts[0]) == 2 and parts[0].isalpha():
            territory = parts.pop(0).upper()
        elif len(parts[0]) == 3 and parts[0].isdigit():
            territory = parts.pop(0)

    if parts:
        if len(parts[0]) == 4 and parts[0][0].isdigit() or\
           len(parts[0]) >= 5 and parts[0][0].isalpha():
            variant = parts.pop()

    if parts:
        raise ValueError('%r is not a valid locale identifier' % identifier)

    return lang, territory, script, variant


def gettext_noop(value):
    """Mark a string for translation without translating it. Returns
    value.
    """
    
    return value

def ugettext(value):
    """Mark a string for translation. Returns the localized unicode
    string of value.

    Mark a string to be localized as follows::

        _('This should be in lots of languages')

    """
    if PY3: #pragma: no cover
        return tg.translator.gettext(value)
    else:
        return tg.translator.ugettext(value)
lazy_ugettext = lazify(ugettext)

def ungettext(singular, plural, n):
    """Mark a string for translation. Returns the localized unicode
    string of the pluralized value.

    This does a plural-forms lookup of a message id. ``singular`` is
    used as the message id for purposes of lookup in the catalog, while
    ``n`` is used to determine which plural form to use. The returned
    message is a Unicode string.

    Mark a string to be localized as follows::

        ungettext('There is %(num)d file here', 'There are %(num)d files here',
                  n) % {'num': n}

    """
    if PY3: #pragma: no cover
        return tg.translator.ngettext(singular, plural, n)
    else:
        return tg.translator.ungettext(singular, plural, n)
lazy_ungettext = lazify(ungettext)


def _get_translator(lang, tgl=None, tg_config=None, **kwargs):
    """Utility method to get a valid translator object from a language
    name"""
    if tg_config:
        conf = tg_config
    else:
        if tgl:
            conf = tgl.config
        else: #pragma: no cover
            #backward compatibility with explicit calls without
            #specifying local context or config.
            conf = tg.config.current_conf()

    if not lang:
        return NullTranslations()

    try:
        localedir = conf['localedir']
    except KeyError: #pragma: no cover
        localedir = os.path.join(conf['paths']['root'], 'i18n')

    if not isinstance(lang, list):
        lang = [lang]

    try:
        translator = translation(conf['package'].__name__, localedir, languages=lang, **kwargs)
    except IOError as ioe:
        raise LanguageError('IOError: %s' % ioe)

    translator.tg_lang = lang
    
    return translator


def get_lang():
    """Return the current i18n language used"""
    return getattr(tg.translator, 'tg_lang', None)


def add_fallback(lang, **kwargs):
    """Add a fallback language from which words not matched in other
    languages will be translated to.

    This fallback will be associated with the currently selected
    language -- that is, resetting the language via set_lang() resets
    the current fallbacks.

    This function can be called multiple times to add multiple
    fallbacks.
    """
    tgl = tg.request_local.context._current_obj()
    return tg.translator.add_fallback(_get_translator(lang, tgl=tgl, **kwargs))

sanitized_language_cache = {}
def sanitize_language_code(lang):
    """Sanitize the language code if the spelling is slightly wrong.

    For instance, 'pt-br' and 'pt_br' should be interpreted as 'pt_BR'.

    """
    try:
        lang = sanitized_language_cache[lang]
    except:
        orig_lang = lang

        try:
            lang = '_'.join(filter(None, _parse_locale(lang)[:2]))
        except ValueError:
            if '-' in lang:
                try:
                    lang = '_'.join(filter(None, _parse_locale(lang, sep='-')[:2]))
                except ValueError:
                    pass

        sanitized_language_cache[orig_lang] = lang

    return lang


def setup_i18n(tgl=None):
    """Set languages from the request header and the session.

    The session language(s) take priority over the request languages.

    Automatically called by tg controllers to setup i18n.
    Should only be manually called if you override controllers function.

    """
    if not tgl: #pragma: no cover
        tgl = tg.request_local.context._current_obj()

    session_ = tgl.session
    if session_:
        session_existed = session_.accessed()
        # If session is available, we try to see if there are languages set
        languages = session_.get(tgl.config.get('lang_session_key', 'tg_lang'))
        if not session_existed and tgl.config.get('beaker.session.tg_avoid_touch'):
            session_.__dict__['_sess'] = None

        if languages:
            if isinstance(languages, string_type):
                languages = [languages]
        else:
            languages = []
    else: #pragma: no cover
        languages = []
    languages.extend(map(sanitize_language_code, tgl.request.plain_languages))
    set_temporary_lang(languages, tgl=tgl)


def set_temporary_lang(languages, tgl=None):
    """Set the current language(s) used for translations without touching
    the session language.

    languages should be a string or a list of strings.
    First lang will be used as main lang, others as fallbacks.

    """
    # the logging to the screen was removed because
    # the printing to the screen for every problem causes serious slow down.
    if not tgl:
        tgl = tg.request_local.context._current_obj()

    try:
        tgl.translator = _get_translator(languages, tgl=tgl)
    except LanguageError:
        pass

    try:
        set_formencode_translation(languages, tgl=tgl)
    except LanguageError:
        pass

def set_lang(languages, **kwargs):
    """Set the current language(s) used for translations
    in current call and session.

    languages should be a string or a list of strings.
    First lang will be used as main lang, others as fallbacks.

    """
    tgl = tg.request_local.context._current_obj()

    set_temporary_lang(languages, tgl)

    if tgl.session:
        tgl.session[tgl.config.get('lang_session_key', 'tg_lang')] = languages
        tgl.session.save()

FormEncodeMissing = '_MISSING_FORMENCODE'
formencode = None
_localdir = None

def set_formencode_translation(languages, tgl=None):
    """Set request specific translation of FormEncode."""
    global formencode, _localdir
    if formencode is FormEncodeMissing: #pragma: no cover
        return

    if formencode is None:
        try:
            import formencode
            _localdir = formencode.api.get_localedir()
        except ImportError: #pragma: no cover
            formencode = FormEncodeMissing
            return

    if not tgl: #pragma: no cover
        tgl = tg.request_local.context._current_obj()

    try:
        formencode_translation = translation(
            'FormEncode',languages=languages, localedir=_localdir)
    except IOError as error:
        raise LanguageError('IOError: %s' % error)
    tgl.tmpl_context.formencode_translation = formencode_translation


__all__ = [
    "setup_i18n", "set_lang", "get_lang", "add_fallback", "set_temporary_lang",
    "ugettext", "lazy_ugettext", "ungettext", "lazy_ungettext"
]

