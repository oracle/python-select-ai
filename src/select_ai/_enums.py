import enum


class StrEnum(str, enum.Enum):

    def __str__(self):
        return self.value
