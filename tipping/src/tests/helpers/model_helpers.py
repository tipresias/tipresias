"""Test helper functions to simplify model tests."""

from collections.abc import Iterable

from tipping.models.base_model import BaseModel


def assert_deep_equal_attributes(model, other_model):
    """Assert equality of two models' attributes recursively."""
    for model_attribute, attribute_value in model.attributes.items():
        from_record_attribute_value = other_model.attributes[model_attribute]

        if isinstance(attribute_value, Iterable) and not isinstance(
            attribute_value, str
        ):
            for idx, sub_value in enumerate(attribute_value):
                from_record_sub_value = from_record_attribute_value[idx]

                if isinstance(sub_value, BaseModel):
                    assert_deep_equal_attributes(sub_value, from_record_sub_value)
                else:
                    assert sub_value == from_record_sub_value
        elif isinstance(attribute_value, BaseModel):
            # We just check IDs to avoid infinite recursion loops
            assert attribute_value.id == from_record_attribute_value.id
        else:
            assert attribute_value == from_record_attribute_value
