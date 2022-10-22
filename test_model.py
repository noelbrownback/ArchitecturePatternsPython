from datetime import date, datetime, timedelta
import pytest
from model import Batch, OrderLine, allocate, OutOfStock

today = date.today()
tomorrow = today + timedelta(days=1)
later = tomorrow + timedelta(days=10)


def test_allocating_to_a_batch_reduces_the_available_quantity():
    batch = Batch("batch-001", "SMALL-TABLE", qty=20, eta=date.today())
    line = OrderLine("order-ref", "SMALL-TABLE", 2)

    batch.allocate(line)

    assert batch.available_quantity ==18

def test_allocate_is_idempotent():
    large_batch, small_line = make_batch_and_line("ELEGANT-LAMP", 20, 2)
    large_batch.allocate(small_line)
    large_batch.allocate(small_line)
    assert large_batch.available_quantity == 18

def make_batch_and_line(sku, batch_qty, line_qty):
    return (
        Batch("batch-001", sku, batch_qty, eta=date.today()),
        OrderLine("order-123", sku, line_qty),
    )

def test_can_allocate_if_available_greater_than_required():
    large_batch, small_line = make_batch_and_line("ELEGANT-LAMP", 20, 2)
    assert large_batch.can_allocate(small_line)

def test_cannot_allocate_if_available_smaller_than_required():
    small_batch, large_line = make_batch_and_line("ELEGANT-LAMP", 2, 20)
    assert small_batch.can_allocate(large_line) is False


def test_can_allocate_if_available_equal_to_required():
    equal_batch, equal_line = make_batch_and_line("ELEGANT-LAMP", 10, 10)
    assert equal_batch.can_allocate(equal_line)

def test_cannot_allocate_if_skus_dont_match():
    batch = Batch("batch-001", "ELEGANT-LAMP", 10, eta=date.today())
    line = OrderLine("order-123", "UNELEGANT-LAMP", 1)
    assert batch.can_allocate(line) is False


def test_cannot_deallocate_unallocated():
    large_batch, small_line = make_batch_and_line("ELEGANT-LAMP", 20, 2)
    large_batch.deallocate(small_line)
    assert large_batch.available_quantity == 20

def test_deallocate_if_available():
    large_batch, small_line = make_batch_and_line("ELEGANT-LAMP", 20, 2)
    medium_line = OrderLine("order-124", "ELEGANT-LAMP", 5)
    large_batch.allocate(small_line)
    large_batch.allocate(medium_line)
    assert large_batch.available_quantity == 13
    large_batch.deallocate(small_line)
    assert large_batch.available_quantity == 15

def test_prefers_warehouse_batches_to_shipments():
    instock_batch = Batch("batch-001", "ELEGANT-LAMP", 100, eta=None)
    shipment_batch = Batch("batch-002", "ELEGANT-LAMP", 100, eta= datetime.now() + timedelta(days=1))
    line = OrderLine("order-123", "ELEGANT-LAMP", 10)

    allocate(line, [instock_batch,shipment_batch])

    assert instock_batch.available_quantity == 90
    assert shipment_batch.available_quantity == 100

def test_prefers_earlier_batches():
    first_batch = Batch("batch-001", "ELEGANT-LAMP", 100, eta= datetime.now() + timedelta(days=1))
    second_batch = Batch("batch-002", "ELEGANT-LAMP", 100, eta= datetime.now() + timedelta(days=2))
    third_batch = Batch("batch-003", "ELEGANT-LAMP", 100, eta= datetime.now() + timedelta(days=3))

    line = OrderLine("order-123", "ELEGANT-LAMP", 10)

    allocate(line, [second_batch, first_batch, third_batch])

    assert first_batch.available_quantity == 90
    assert second_batch.available_quantity == 100
    assert third_batch.available_quantity == 100

def test_raise_out_of_stock_exception_if_cannot_allocate():
    batch = Batch("batch-001", 'SMALL-FORK', 10, eta=datetime.now())
    order = OrderLine('order1', 'SMALL-FORK', 10)
    allocate(order, [batch])

    with pytest.raises(OutOfStock, match='SMALL-FORK'):
        allocate(OrderLine('order2', 'SMALL-FORK', 10), [batch])