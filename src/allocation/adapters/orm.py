from sqlalchemy import Table, MetaData, Column, Integer, String, Date
from sqlalchemy.orm import registry, relationship

from allocation.domain import model


metadata = MetaData()

order_lines = Table(
    "order_lines",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("sku", String(255)),
    Column("qty", Integer, nullable=False),
    Column("orderid", String(255)),
)

products = Table(
    "products",
    metadata,
    Column("sku", String(255), primary_key=True),
    Column("version_number", Integer, nullable=False, server_default="0"),
)

batches = Table(
    "batches",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("reference", String(255)),
    Column("sku", String(255)), # Products的sku
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

    # 2. 映射 Product（新增）
    mapper_registry.map_imperatively(
        model.Product,
        products,
        properties={
            "batches": relationship(
                model.Batch, 
                back_populates="product",
                primaryjoin=products.c.sku == batches.c.sku,  # 连接条件
                foreign_keys=[batches.c.sku],                 # 外键列
                uselist=True,                                 # 一对多
                viewonly=False,                               # 可写
            ),
        }
    )

    # 3. 映射 Batch
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
            ),
            "product": relationship(
                model.Product,
                primaryjoin=lambda: batches.c.sku == products.c.sku,
                foreign_keys=[batches.c.sku],
                uselist=False,  # 每个Batch只对应一个Product
                back_populates="batches",  # 如果 Product 映射中定义了反向关系
            ),
        }
    )