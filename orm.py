from sqlalchemy import Table, MetaData, Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import registry, relationship

import model


metadata = MetaData()

order_lines = Table(
    "order_lines",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("sku", String(255)),
    Column("qty", Integer, nullable=False),
    Column("orderid", String(255)),
)

batches = Table(
    "batches",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("reference", String(255)),
    Column("sku", String(255)),
    Column("_purchased_quantity", Integer, nullable=False),
    Column("eta", Date, nullable=True),
)

allocations = Table(
    "allocations",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("orderline_id", ForeignKey("order_lines.id")),
    Column("batch_id", ForeignKey("batches.id")),
)

# 创建全局注册表示例(1个项目创建1个即可)
mapper_registry = registry()


def start_mappers():
    # 绑定 纯Python类 和 Table对象，实现经典映射
    # 1. 映射OrderLines，替代原 mapper(model.OrderLine, order_lines)
    lines_mapper = mapper_registry.map_imperatively(model.OrderLine, order_lines)
    # 2. 映射 Batch，替代原 mapper(...)，里面的 properties 内部逻辑 完全不变！！！
    mapper_registry.map_imperatively(
        model.Batch,
        batches,
        properties={
            "_allocations": relationship(
                lines_mapper, 
                secondary=allocations, 
                collection_class=set,  # 这个集合类型保留
            )
        },
    )