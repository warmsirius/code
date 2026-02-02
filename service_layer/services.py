from __future__ import annotations
from typing import Optional
from datetime import date

from domain import model
from domain.model import OrderLine
from adapters.repository import AbstractRepository


class InvalidSku(Exception):
    pass


def is_valid_sku(sku, batches):
    return sku in {b.sku for b in batches}


def add_batch(
    ref: str, sku: str, qty: int, eta: Optional[date],
    repo: AbstractRepository, session,
) -> None:
    """
    添加批次:
    如果我们有一个用于添加库存的服务，我们可以使用它，
    并使我们的服务层测试完全根据服务层的官方用例表达，从而消除对领域的所有依赖
    我们的服务层测试仅依赖于服务层本身，让我们完全自由地根据需要重构模型，如果以后会修改Batch，也无需修改大量测试代码。
    """
    repo.add(model.Batch(ref, sku, qty, eta))
    session.commit()


def allocate(
    orderid: str, sku: str, qty: int,
    repo: AbstractRepository, session
) -> str:
    line = OrderLine(orderid, sku, qty)
    batches = repo.list()
    if not is_valid_sku(line.sku, batches):
        raise InvalidSku(f"Invalid sku {line.sku}")
    batchref = model.allocate(line, batches)
    session.commit()
    return batchref
