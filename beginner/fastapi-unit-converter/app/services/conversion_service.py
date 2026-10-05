from decimal import ROUND_HALF_UP, Decimal

from app.core.exceptions import AppError, NotFoundError
from app.repositories.unit_repository import CategoryRecord, UnitRecord, UnitRepository
from app.schemas.conversion import ConversionRead, ConversionRequest
from app.schemas.unit import Category, CategoryUnitsRead, UnitRead

_SIX_PLACES = Decimal("0.000001")
_ABSOLUTE_ZERO_C = Decimal("-273.15")

_TEMP_FORMULAS: dict[tuple[str, str], str] = {
    ("celsius", "fahrenheit"): "°F = (°C × 9/5) + 32",
    ("fahrenheit", "celsius"): "°C = (°F − 32) × 5/9",
    ("celsius", "kelvin"): "K = °C + 273.15",
    ("kelvin", "celsius"): "°C = K − 273.15",
    ("fahrenheit", "kelvin"): "K = ((°F − 32) × 5/9) + 273.15",
    ("kelvin", "fahrenheit"): "°F = ((K − 273.15) × 9/5) + 32",
}


def _round_six(value: Decimal) -> float:
    return float(value.quantize(_SIX_PLACES, rounding=ROUND_HALF_UP))


def _to_celsius(value: Decimal, code: str) -> Decimal:
    if code == "celsius":
        return value
    if code == "fahrenheit":
        return (value - Decimal(32)) * Decimal(5) / Decimal(9)
    if code == "kelvin":
        return value - Decimal("273.15")
    raise AppError(f"Temperature unit '{code}' cannot be converted", status_code=400)


def _from_celsius(celsius: Decimal, code: str) -> Decimal:
    if code == "celsius":
        return celsius
    if code == "fahrenheit":
        return celsius * Decimal(9) / Decimal(5) + Decimal(32)
    if code == "kelvin":
        return celsius + Decimal("273.15")
    raise AppError(f"Temperature unit '{code}' cannot be converted", status_code=400)


def _to_unit(unit: UnitRecord) -> UnitRead:
    factor = None if unit.factor_to_base is None else format(unit.factor_to_base, "f")
    return UnitRead(
        code=unit.code,
        symbol=unit.symbol,
        name=unit.name,
        aliases=list(unit.aliases),
        factor_to_base=factor,
    )


def _to_category(record: CategoryRecord) -> CategoryUnitsRead:
    return CategoryUnitsRead(
        category=Category(record.code),
        description=record.description,
        base_unit=record.base_unit,
        units=[_to_unit(unit) for unit in record.units],
    )


def _read(
    category: CategoryRecord,
    source: UnitRecord,
    target: UnitRecord,
    input_value: float,
    result: float,
    formula: str,
) -> ConversionRead:
    return ConversionRead(
        category=Category(category.code),
        from_unit=source.code,
        to_unit=target.code,
        from_symbol=source.symbol,
        to_symbol=target.symbol,
        input_value=input_value,
        result=result,
        formula=formula,
    )


class ConversionService:
    def __init__(self, repository: UnitRepository) -> None:
        self._repo = repository

    def list_categories(self) -> list[CategoryUnitsRead]:
        return [_to_category(record) for record in self._repo.list_categories()]

    def get_category(self, category: Category) -> CategoryUnitsRead:
        record = self._repo.get_category(category.value)
        if record is None:
            raise NotFoundError("Category", category.value)
        return _to_category(record)

    def convert(self, payload: ConversionRequest) -> ConversionRead:
        category_code = payload.category.value
        category = self._repo.get_category(category_code)
        if category is None:
            raise NotFoundError("Category", category_code)

        source = self._require_unit(category_code, payload.from_unit)
        target = self._require_unit(category_code, payload.to_unit)
        value = Decimal(str(payload.value))

        if payload.category is Category.temperature:
            return self._convert_temperature(category, source, target, value, payload.value)
        return self._convert_linear(category, source, target, value, payload.value)

    def _require_unit(self, category: str, code: str) -> UnitRecord:
        unit = self._repo.resolve(category, code)
        if unit is None:
            supported = ", ".join(self._repo.unit_codes(category))
            raise AppError(
                f"Unknown {category} unit '{code}'. Supported codes: {supported}",
                status_code=400,
            )
        return unit

    def _convert_temperature(
        self,
        category: CategoryRecord,
        source: UnitRecord,
        target: UnitRecord,
        value: Decimal,
        original: float,
    ) -> ConversionRead:
        celsius = _to_celsius(value, source.code)
        if celsius < _ABSOLUTE_ZERO_C:
            raise AppError(
                "Temperature is below absolute zero (-273.15 °C / 0 K)",
                status_code=422,
            )
        if source.code == target.code:
            return _read(category, source, target, original, original, "result = value")

        formula = _TEMP_FORMULAS[(source.code, target.code)]
        result = _round_six(_from_celsius(celsius, target.code))
        return _read(category, source, target, original, result, formula)

    def _convert_linear(
        self,
        category: CategoryRecord,
        source: UnitRecord,
        target: UnitRecord,
        value: Decimal,
        original: float,
    ) -> ConversionRead:
        if source.code == target.code:
            return _read(category, source, target, original, original, "result = value")

        if source.factor_to_base is None or target.factor_to_base is None:
            raise AppError(f"{category.code} units are missing scale factors", status_code=500)

        raw = value * source.factor_to_base / target.factor_to_base
        formula = (
            f"result = value × {format(source.factor_to_base, 'f')} / "
            f"{format(target.factor_to_base, 'f')} (base unit: {category.base_unit})"
        )
        return _read(category, source, target, original, _round_six(raw), formula)
