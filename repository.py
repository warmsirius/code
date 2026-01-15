import abc
from typing import Set

from sqlalchemy import text

import model


class AbstractRepository(abc.ABC):
    @abc.abstractmethod
    def add(self, batch: model.Batch):
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, reference) -> model.Batch:
        raise NotImplementedError


class SqlRepository(AbstractRepository):
    def __init__(self, session):
        self.session = session

    def add(self, batch: model.Batch):
        """
        核心仓储方法：持久化Batch对象到数据库（含关联数据）
        逻辑：有则更新，无则新增 + 同步分配的订单行 + 同步分配关系
        """
        # 仓储层add: 将内存中的Batch(包含其所有分配的订单行),完整持久化/同步到数据库中
        # 1.如果批次不存在 → 插入批次 + 插入订单行 + 插入分配关系
        # 2.如果批次已存在 → 更新批次 + 同步订单行 + 更新分配关系

        # 1.查询批次是否存在(唯一reference)
        exisiting_batch = self.session.execute(
            text("SELECT id FROM batches WHERE reference = :ref"),
            dict(ref=batch.reference)
        ).mappings().first()

        if exisiting_batch:
            # 存在更新: 更新批次基本数据
            batch.id = exisiting_batch["id"]
        else:
            # 不存在新增: 插入批次并赋值自增ID
            res = self.session.execute(
                text(
                    "INSERT INTO batches (reference, sku, _purchased_quantity, eta)"
                    " VALUES (:ref, :sku, :qty, :eta)"
                ),
                dict(ref=batch.reference, sku=batch.sku, qty=batch._purchased_quantity, eta=batch.eta),
            )
            batch.id = res.lastrowid
        # 2.批量入库【分配的订单行】到order_lines表
        self._save_order_lines(batch._allocations)

        # 3.同步【批次-订单行】的分配关系到allocations表
        self._save_allocations(batch)


    def get(self, reference) -> model.Batch:
        # 1.查询批次主数据
        # .mappings().first()通过字段名取值, 获取字典KV格式，无需解包
        batch_row = self.session.execute(
            text('SELECT id, reference, sku, _purchased_quantity, eta FROM batches WHERE reference=:ref'),
            dict(ref=reference),
        ).mappings().first()

        if not batch_row:
            return None

        # 2.实例化Batch对象
        batch = model.Batch(
            ref=batch_row["reference"],
            sku=batch_row["sku"],
            qty=batch_row["_purchased_quantity"],
            eta=batch_row["eta"],
        )
        batch.id = batch_row["id"]
        batch._allocations = self._get_allocated_order_lines(batch_row["id"])

        return batch
    def list(self) -> list[model.Batch]:
        # 1.查询所有批次数据
        batch_rows = self.session.execute(
            text('SELECT id, reference, sku, _purchased_quantity, eta FROM batches'),
        ).mappings()

        if not batch_rows:
            return None
        
        # 2.处理每个批次
        batches = []
        for batch_row in batch_rows:
            batch = model.Batch(
                ref=batch_row["reference"],
                sku=batch_row["sku"],
                qty=batch_row["_purchased_quantity"],
                eta=batch_row["eta"],
            )
            batch.id = batch_row["id"]
            batch._allocations = self._get_allocated_order_lines(batch_row["id"])
            batches.append(batch)
        
        return batches
    
    def _get_allocated_order_lines(self, batch_id: int) -> Set[model.OrderLine]:
        """辅助方法: 根据批次ID获取其所有分配的订单行集合"""
        order_line_rows = self.session.execute(
            text(
                "SELECT ol.id, ol.sku, ol.qty, ol.orderid "
                "FROM allocations a "
                "JOIN order_lines ol ON a.orderline_id = ol.id "
                "WHERE a.batch_id = :batchid"
            ),
            dict(batchid=batch_id),
        ).mappings()

        order_lines = set()
        for ol_row in order_line_rows:
            order_line = model.OrderLine(
                orderid=ol_row["orderid"],
                sku=ol_row["sku"],
                qty=ol_row["qty"],
            )
            order_line.id = ol_row["id"]
            order_lines.add(order_line)
        
        return order_lines
    
    def _save_order_lines(self, order_lines: Set[model.OrderLine]):
        """辅助方法: 入库订单行，有则跳过，无则新增（避免重复插入）"""
        for line in order_lines:
            # 查询订单行是否存在(通过order_id+sku组合唯一定位)
            exists = self.session.execute(
                text("SELECT id FROM order_lines WHERE orderid=:orderid AND sku=:sku"),
                dict(orderid=line.orderid, sku=line.sku)
            ).first()
            if not exists:
                # 不存在则插入
                res = self.session.execute(
                    text(
                        "INSERT INTO order_lines (orderid, sku, qty)"
                        " VALUES (:orderid, :sku, :qty)"
                    ),
                    dict(orderid=line.orderid, sku=line.sku, qty=line.qty),
                )
                line.id = res.lastrowid # 给内存OrderLine赋值数据库ID

    def _save_allocations(self, batch: model.Batch):
        """辅助方法: 同步分配关系，核心逻辑：先删除旧关系，再插入新的，保证数据一致性"""
        # 重要: 先删除该批次已有的分配关系(避免重复插入)
        self.session.execute(
            text("DELETE FROM allocations WHERE batch_id=:batchid"),
            dict(batchid=batch.id),
        )

        # 插入最新的分配关系(内存中batch._allocations中所有订单行)
        for line in batch._allocations:
            self.session.execute(
                text(
                    "INSERT INTO allocations (orderline_id, batch_id)"
                    " VALUES (:orderline_id, :batch_id)"
                ),
                dict(orderline_id=line.id, batch_id=batch.id),
            )