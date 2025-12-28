from typing import Any, get_type_hints

from pydantic import BaseModel


def parse_fields_param(fields: str | None) -> set[str]:
    if not fields:
        return set()

    if fields.lower() == "minimal":
        return {"minimal"}

    return {field.strip() for field in fields.split(",") if field.strip()}


def get_required_fields[T: BaseModel](model_class: type[T]) -> set[str]:
    model_fields = model_class.model_fields
    required_fields = {
        name for name, field in model_fields.items() if field.is_required()
    }
    return required_fields


def get_minimal_fields[T: BaseModel](model_class: type[T]) -> set[str]:
    required = get_required_fields(model_class)

    minimal_optional = {
        "CourseListResponse": {"price"},
        "CourseListResponseV2": {"final_price"},
        "CourseDetailResponse": {"description"},
        "CourseDetailResponseV2": {"description"},
        "ModuleResponse": set(),
        "ModuleDetailResponse": {"description"},
        "UserResponse": set(),
        "TestResponse": {"description"},
        "QuestionResponse": set(),
    }

    optional = minimal_optional.get(model_class.__name__, set())
    return required.union(optional)


def get_fields_to_return[T: BaseModel](
    requested_fields: set[str],
    model_class: type[T],
) -> set[str]:
    if not requested_fields:
        return set(get_type_hints(model_class).keys())

    if "minimal" in requested_fields:
        return get_minimal_fields(model_class)

    all_fields = set(get_type_hints(model_class).keys())

    invalid_fields = requested_fields - all_fields
    if invalid_fields:
        raise ValueError(f"Invalid fields: {', '.join(invalid_fields)}")

    required_fields = get_required_fields(model_class)

    return requested_fields.union(required_fields)


def filter_model_fields[T: BaseModel](
    model: T,
    fields: set[str],
    model_class: type[T] | None = None,
) -> dict[str, Any]:
    if not fields:
        return model.model_dump()

    if not model_class:
        model_class = type(model)

    fields_to_return = get_fields_to_return(fields, model_class)

    model_dict = model.model_dump()

    filtered_dict = {}
    for field in fields_to_return:
        if field in model_dict:
            filtered_dict[field] = model_dict[field]

    return filtered_dict


def filter_list_of_models[T: BaseModel](
    models: list[T],
    fields: set[str],
    model_class: type[T] | None = None,
) -> list[dict[str, Any]]:
    if not fields:
        return [model.model_dump() for model in models]

    return [filter_model_fields(model, fields, model_class) for model in models]


def validate_fields[T: BaseModel](
    fields: set[str],
    model_class: type[T],
) -> set[str]:
    if not fields or "minimal" in fields:
        return fields

    model_fields = set(get_type_hints(model_class).keys())
    valid_fields = fields.intersection(model_fields)

    if len(valid_fields) < len(fields):
        invalid_fields = fields - valid_fields
        raise ValueError(f"Invalid fields: {', '.join(invalid_fields)}")

    return valid_fields
