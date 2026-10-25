from decimal import Decimal

from app.core.exceptions import ConflictError, NotFoundError
from app.models.billing import Invoice, InvoiceLine, InvoiceStatus
from app.repositories.billing_repository import BillingRepository
from app.schemas.invoice import InvoiceLineRead, InvoicePreviewRead, InvoiceRead
from app.schemas.invoice import InvoiceStatus as InvoiceStatusSchema


def _compute_line(
    meter_code: str,
    usage: Decimal,
    included: Decimal,
    unit_price_cents: int,
) -> InvoiceLineRead:
    billable = max(Decimal("0"), usage - included)
    amount_cents = int(billable * Decimal(unit_price_cents))
    return InvoiceLineRead(
        meter_code=meter_code,
        quantity=usage,
        included_quantity=included,
        billable_quantity=billable,
        unit_price_cents=unit_price_cents,
        amount_cents=amount_cents,
    )


class InvoiceService:
    def __init__(self, repo: BillingRepository) -> None:
        self._repo = repo

    async def preview(self, customer_id: int) -> InvoicePreviewRead:
        subscription = await self._repo.get_active_subscription(customer_id)
        if subscription is None:
            raise NotFoundError("Subscription", customer_id)

        usage_rows = await self._repo.sum_usage(
            customer_id,
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
        )
        usage_map = dict(usage_rows)

        lines: list[InvoiceLineRead] = []
        total = 0
        for plan_meter in subscription.plan.plan_meters:
            usage = usage_map.get(plan_meter.meter.code, Decimal("0"))
            line = _compute_line(
                plan_meter.meter.code,
                usage,
                Decimal(str(plan_meter.included_quantity)),
                plan_meter.unit_price_cents,
            )
            lines.append(line)
            total += line.amount_cents

        return InvoicePreviewRead(
            customer_id=customer_id,
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            total_cents=total,
            lines=lines,
        )

    async def generate(self, customer_id: int) -> InvoiceRead:
        preview = await self.preview(customer_id)
        existing = await self._repo.invoice_for_period(
            customer_id,
            preview.period_start,
            preview.period_end,
        )
        if existing is not None:
            raise ConflictError("An invoice for this billing period already exists")

        invoice = Invoice(
            customer_id=customer_id,
            period_start=preview.period_start,
            period_end=preview.period_end,
            total_cents=preview.total_cents,
            status=InvoiceStatus.OPEN.value,
        )
        for line in preview.lines:
            meter = await self._repo.get_meter_by_code(line.meter_code)
            if meter is None:
                continue
            invoice.lines.append(
                InvoiceLine(
                    meter_id=meter.id,
                    quantity=line.quantity,
                    included_quantity=line.included_quantity,
                    billable_quantity=line.billable_quantity,
                    unit_price_cents=line.unit_price_cents,
                    amount_cents=line.amount_cents,
                )
            )
        created = await self._repo.add_invoice(invoice)
        return InvoiceRead(
            id=created.id,
            customer_id=created.customer_id,
            period_start=created.period_start,
            period_end=created.period_end,
            total_cents=created.total_cents,
            status=InvoiceStatusSchema(created.status),
            created_at=created.created_at,
            lines=preview.lines,
        )

    async def list_invoices(self, customer_id: int) -> list[InvoiceRead]:
        if await self._repo.get_customer(customer_id) is None:
            raise NotFoundError("Customer", customer_id)
        rows = await self._repo.list_invoices(customer_id)
        return [self._to_read(row) for row in rows]

    def _to_read(self, invoice: Invoice) -> InvoiceRead:
        lines: list[InvoiceLineRead] = []
        for line in invoice.lines:
            code = line.meter.code if line.meter is not None else "unknown"
            lines.append(
                InvoiceLineRead(
                    meter_code=code,
                    quantity=Decimal(str(line.quantity)),
                    included_quantity=Decimal(str(line.included_quantity)),
                    billable_quantity=Decimal(str(line.billable_quantity)),
                    unit_price_cents=line.unit_price_cents,
                    amount_cents=line.amount_cents,
                )
            )
        return InvoiceRead(
            id=invoice.id,
            customer_id=invoice.customer_id,
            period_start=invoice.period_start,
            period_end=invoice.period_end,
            total_cents=invoice.total_cents,
            status=InvoiceStatusSchema(invoice.status),
            created_at=invoice.created_at,
            lines=lines,
        )
