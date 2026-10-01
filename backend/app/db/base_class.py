from typing import Any
from sqlalchemy.orm import DeclarativeBase, declared_attr

class Base(DeclarativeBase):
    id: Any
    __name__: str

    # Generate __tablename__ automatically
    @declared_attr.directive
    def __tablename__(cls) -> str:
        # Convert CamelCase to snake_case table names
        name = cls.__name__
        out = []
        for i, char in enumerate(name):
            if char.isupper() and i > 0:
                out.append("_")
            out.append(char.lower())
        return "".join(out)
