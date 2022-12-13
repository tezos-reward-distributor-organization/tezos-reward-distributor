from util.address_validator import (
    AddressValidator,
    IncorrectAddressError,
    IncorrectLengthError,
)
import pytest


@pytest.mark.parametrize(
    "type, input, expected",
    [
        ("baking address", "1234567", IncorrectAddressError),
        ("baking address", "tz1234567", IncorrectLengthError),
    ],
)
def test_address_validator_throws(type, input, expected):
    with pytest.raises(expected):
        validator = AddressValidator(type)
        validator.validate(input)


@pytest.mark.parametrize(
    "type, input, expected",
    [
        ("baking address", "tz1234567891011121314151617181920212", None),
        ("baking address", "KT1234567891011121314151617181920212", None),
    ],
)
def test_address_validator_passes(type, input, expected):
    validator = AddressValidator(type)
    validation = validator.validate(input)
    assert validation is expected


@pytest.mark.parametrize(
    "type, input, expected",
    [
        ("baking address", "1234567", Exception),
        ("baking address", "tz1234567", Exception),
    ],
)
def test_address_tz_validator_throws(type, input, expected):
    with pytest.raises(expected):
        validator = AddressValidator(type)
        validator.tz_validate(input)


@pytest.mark.parametrize(
    "type, input, expected",
    [
        ("baking address", "tz1234567891011121314151617181920212", None),
    ],
)
def test_address_tz_validator_passes(type, input, expected):
    validator = AddressValidator(type)
    validation = validator.tz_validate(input)
    assert validation is expected


@pytest.mark.parametrize(
    "type, input, expected",
    [
        ("baking address", "tz1234567891011121314151617181920212", True),
        ("baking address", "KT1234567891011121314151617181920212", True),
        ("baking address", "KT12345678910111213141516171819202", False),
        ("baking address", "123456789101112131415161718192021243", False),
    ],
)
def test_isaddress(type, input, expected):
    validator = AddressValidator(type)
    validation = validator.isaddress(input)
    assert validation is expected
