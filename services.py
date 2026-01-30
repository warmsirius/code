from __future__ import annotations # 关键：延迟解析类型注解，支持直接写未定义的类型

import model
from model import OrderLine
from repository import AbstractRepository


class InvalidSku(Exception):
    pass

class InvalidOrderID(Exception):
    pass


def is_valid_sku(sku, batches):
    return sku in {b.sku for b in batches}

def is_valid_orderid(orderid, batches):
    return orderid in {line.orderid for b in batches for line in b._allocations}


def allocate(line: OrderLine, repo: AbstractRepository, session) -> str:
    batches = repo.list()
    if not is_valid_sku(line.sku, batches):
        raise InvalidSku(f"Invalid sku {line.sku}")
    batchref = model.allocate(line, batches)
    session.commit()
    return batchref


def deallocate(line: OrderLine, repo: AbstractRepository, session) -> str:
    batches = repo.list()
    if not is_valid_orderid(line.orderid, batches):
        raise InvalidOrderID(f"Invalid orderid {line.orderid}")
    batchref = model.deallocate(line, batches)
    session.commit()
    return batchref
