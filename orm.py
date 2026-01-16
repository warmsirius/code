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
    Column("orderline_id", Integer), # 移除ForeignKey
    Column("batch_id", Integer), # 移除ForeignKey
)

# 创建全局注册表示例(1个项目创建1个即可)
mapper_registry = registry()


def start_mappers():
    # 1. 映射OrderLines
    lines_mapper = mapper_registry.map_imperatively(
            model.OrderLine,
            order_lines,
            # 如果model.OrderLine类中需要定义反向关系Batch的，可以在这里添加
            # 建议: 但是建议用backref在Batch中定义，保持单向关系更清晰
            # properties={
            #     "allocations": relationship(
            #         model.Batch,
            #         secondary=allocations, # 多对多关系中间表
            #         primaryjoin="OrderLine.id == allocations.c.orderline_id", #  主表(当前的映射的类) ↔ 中间表
            #         secondaryjoin="Batch.id == allocations.c.batch_id", # 中间表 ↔ 目标类
            #         collection_class=set,
            #         viewonly=True # 设置为只读关系
            #     )
            # }
        )
    # 2. 映射 Batch(主要关系)
    mapper_registry.map_imperatively(
        model.Batch,
        batches,
        properties={
            "_allocations": relationship(
                lines_mapper, 
                secondary=allocations,
                
                # Lambda 表达式（延迟解析）
                # SQLAlchemy 会存储 lambda，在需要时才执行
                # 执行时，model.Batch 已经被映射，可以找到对应的类和属性
                primaryjoin=lambda: model.Batch.id == allocations.c.batch_id,
                secondaryjoin=lambda: model.OrderLine.id == allocations.c.orderline_id,

                # allocations是一个Table对象，不是类名，allocations.c.列名 访问列
                # allocations.c: 包含所有列明的字段或命名空间
                foreign_keys=[allocations.c.batch_id, allocations.c.orderline_id], # 明确指定外键列(逻辑上是)

                collection_class=set,  # 关系的集合类型使用set"

                # 如果只需要从 Batch 到 OrderLine 的访问，可以去掉 OrderLine 的反向关系
                backref="batches"  # 可选：创建反向引用
            )
        },
    )


# 快速判断规则：
# 1. 在 model.py 中有对应的类吗？
#    有 → 用 类名.属性名 (Batch.id, OrderLine.id)
#    没有 → 用 表名.c.列名 (allocations.c.batch_id)

# 2. 这个表作为 secondary 参数使用吗？
#    是 → 通常不映射，用 .c 访问
#    否 → 可能需要映射

# 3. 需要对这个表进行CRUD操作吗？
#    需要 → 应该映射到类
#    不需要 → 可以不映射，用 .c 访问