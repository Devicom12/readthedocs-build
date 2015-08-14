# -*- coding: utf-8 -*-
from pytest import raises

from .validation import validate_bool
from .validation import validate_choice
from .validation import validate_string
from .validation import ValidationError
from .validation import INVALID_BOOL
from .validation import INVALID_CHOICE
from .validation import INVALID_STRING


def describe_validate_bool():
    def it_accepts_true():
        assert validate_bool(True) is True

    def it_accepts_false():
        assert validate_bool(False) is False

    def it_accepts_0():
        assert validate_bool(0) is False

    def it_accepts_1():
        assert validate_bool(1) is True

    def it_fails_on_string():
        with raises(ValidationError) as excinfo:
            validate_bool('random string')
        assert excinfo.value.code == INVALID_BOOL


def describe_validate_choice():

    def it_accepts_valid_choice():
        result = validate_choice('choice', ('choice', 'another_choice'))
        assert result is 'choice'

        result = validate_choice('c', 'abc')
        assert result is 'c'

    def it_rejects_invalid_choice():
        with raises(ValidationError) as excinfo:
            validate_choice('not-a-choice', ('choice', 'another_choice'))
        assert excinfo.value.code == INVALID_CHOICE


def describe_validate_string():

    def it_accepts_unicode():
        result = validate_string(u'Unicöde')
        assert isinstance(result, unicode)

    def it_accepts_nonunicode():
        result = validate_string('Unicode')
        assert isinstance(result, unicode)

    def it_rejects_float():
        with raises(ValidationError) as excinfo:
            validate_string(123.456)
        assert excinfo.value.code == INVALID_STRING

    def it_rejects_none():
        with raises(ValidationError) as excinfo:
            validate_string(None)
        assert excinfo.value.code == INVALID_STRING
