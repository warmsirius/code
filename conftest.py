import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, clear_mappers

from orm import metadata, start_mappers


@pytest.fixture
def in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    return engine


@pytest.fixture
def session(in_memory_db):
    start_mappers()
    yield sessionmaker(bind=in_memory_db)()
    clear_mappers() 
    # 彻底清除内存中所有已经注册/绑定的类表关系映射，将ORM的映射注册表置为空
   
    # clear_mappers 特性：
    #   - 只清理经典映射registry.map_imperatively()，不影响声明式映射DeclarativeBase
    #   - 清理的是内存中的映射关系，不是数据库/数据
    #   - 幂等安全，多次调用不会报错
    #   - 2.0五替代方案，唯一的映射清理函数
   
    # 作用1: 解决重复映射,因为fixture每次调用都会重新映射一次，如果没有clear_mappers()会重复映射会报错
    # 作用2: 保证测试用例之间的隔离性，避免测试之间的映射关系相互影响
    #   pyest核心要求: 每个测试用例必须是独立、无副作用、互不干扰

