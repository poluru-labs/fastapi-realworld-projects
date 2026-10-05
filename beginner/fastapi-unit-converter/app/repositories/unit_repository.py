from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class UnitRecord:
    code: str
    symbol: str
    name: str
    aliases: tuple[str, ...]
    factor_to_base: Decimal | None = None


@dataclass(frozen=True)
class CategoryRecord:
    code: str
    description: str
    base_unit: str
    units: tuple[UnitRecord, ...]


_TEMPERATURE = CategoryRecord(
    code="temperature",
    description=(
        "Thermodynamic temperature. Values convert through Celsius. "
        "Inputs below absolute zero (−273.15 °C) are rejected."
    ),
    base_unit="celsius",
    units=(
        UnitRecord("celsius", "°C", "Celsius", ("c", "degc")),
        UnitRecord("fahrenheit", "°F", "Fahrenheit", ("f", "degf")),
        UnitRecord("kelvin", "K", "Kelvin", ("k",)),
    ),
)

_DISTANCE = CategoryRecord(
    code="distance",
    description="Length. Linear conversion through meters using international (1959) definitions.",
    base_unit="meter",
    units=(
        UnitRecord("millimeter", "mm", "Millimeter", ("mm",), Decimal("0.001")),
        UnitRecord("centimeter", "cm", "Centimeter", ("cm",), Decimal("0.01")),
        UnitRecord("meter", "m", "Meter", ("m",), Decimal("1")),
        UnitRecord("kilometer", "km", "Kilometer", ("km",), Decimal("1000")),
        UnitRecord("inch", "in", "Inch", ("in",), Decimal("0.0254")),
        UnitRecord("foot", "ft", "Foot", ("ft",), Decimal("0.3048")),
        UnitRecord("yard", "yd", "Yard", ("yd",), Decimal("0.9144")),
        UnitRecord("mile", "mi", "Mile", ("mi",), Decimal("1609.344")),
    ),
)

_WEIGHT = CategoryRecord(
    code="weight",
    description="Mass. Linear conversion through grams using the international avoirdupois pound.",
    base_unit="gram",
    units=(
        UnitRecord("milligram", "mg", "Milligram", ("mg",), Decimal("0.001")),
        UnitRecord("gram", "g", "Gram", ("g",), Decimal("1")),
        UnitRecord("kilogram", "kg", "Kilogram", ("kg",), Decimal("1000")),
        UnitRecord("ounce", "oz", "Ounce", ("oz",), Decimal("28.349523125")),
        UnitRecord("pound", "lb", "Pound", ("lb",), Decimal("453.59237")),
    ),
)

_CATEGORY_ORDER: tuple[CategoryRecord, ...] = (_TEMPERATURE, _DISTANCE, _WEIGHT)
_CATEGORIES: dict[str, CategoryRecord] = {record.code: record for record in _CATEGORY_ORDER}


def _build_lookups() -> dict[str, dict[str, UnitRecord]]:
    lookups: dict[str, dict[str, UnitRecord]] = {}
    for category in _CATEGORY_ORDER:
        table: dict[str, UnitRecord] = {}
        for unit in category.units:
            for key in (unit.code, *unit.aliases):
                if key in table:
                    raise RuntimeError(f"Duplicate unit key '{key}' in {category.code}")
                table[key] = unit
        lookups[category.code] = table
    return lookups


_LOOKUPS = _build_lookups()


class UnitRepository:
    """Read-only catalog of supported units and exact scale factors."""

    def list_categories(self) -> list[CategoryRecord]:
        return list(_CATEGORY_ORDER)

    def get_category(self, category: str) -> CategoryRecord | None:
        return _CATEGORIES.get(category)

    def resolve(self, category: str, code: str) -> UnitRecord | None:
        table = _LOOKUPS.get(category)
        if table is None:
            return None
        return table.get(code)

    def unit_codes(self, category: str) -> list[str]:
        record = _CATEGORIES.get(category)
        if record is None:
            return []
        return [unit.code for unit in record.units]
