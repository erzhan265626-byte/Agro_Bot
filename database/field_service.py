from dataclasses import dataclass
import json

from database.db import get_fields


@dataclass
class Field:
    id: int
    user_id: int
    name: str
    latitude: float
    longitude: float
    area: float
    crop: str
    boundary: list


def convert_field(row):

    field_id = row[0]
    user_id = row[1]
    name = row[2]
    latitude = row[3]
    longitude = row[4]
    area = row[5]
    crop = row[6]

    boundary = []

    if len(row) > 7 and row[7]:

        try:
            boundary = json.loads(row[7])

        except (json.JSONDecodeError, TypeError):
            boundary = []

    return Field(
        id=field_id,
        user_id=user_id,
        name=name,
        latitude=latitude,
        longitude=longitude,
        area=area,
        crop=crop,
        boundary=boundary
    )


def get_all_fields(user_id):

    rows = get_fields(user_id)

    return [
        convert_field(row)
        for row in rows
    ]


def get_field_by_id(field_id, user_id):

    fields = get_all_fields(user_id)

    for field in fields:

        if field.id == field_id:
            return field

    return None