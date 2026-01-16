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
    Column("orderline_id", Integer),# 移除ForeignKey
    Column("batch_id", Integer),# 移除ForeignKey
)

# 创建全局注册表示例(1个项目创建1个即可)
mapper_registry = registry()


def start_mappers():
    # 绑定 纯Python类 和 Table对象，实现经典映射
    # 1. 映射OrderLines
    lines_mapper = mapper_registry.map_imperatively(model.OrderLine, order_lines)
    # 2. 映射 Batch
    mapper_registry.map_imperatively(
        model.Batch,
        batches,
        properties={
            "_allocations": relationship(
                lines_mapper,
                secondary=allocations, 
                
                primaryjoin=lambda: model.Batch.id == allocations.c.batch_id, 
                secondaryjoin=lambda: model.OrderLine.id == allocations.c.orderline_id,
                foreign_keys=[allocations.c.batch_id, allocations.c.orderline_id],

                collection_class=set,  # 这个集合类型保留
                # backref="batches"  # 如果需要双向关系，可以启用这行
            )
        },
    )