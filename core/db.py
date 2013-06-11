import logging

import sqlalchemy as SA
from sqlalchemy.dialects import mysql
from sqlalchemy import Column, Integer, SmallInteger, String
from sqlalchemy.ext.declarative import declarative_base

from core.settings import Settings

engine = None
Base = declarative_base()

def UnsignedInteger():
    if Settings["db_uri"].startswith("mysql"):
        return mysql.INTEGER(unsigned=True)
    else:
        return Integer


class DatabaseError(Exception):
	def __init__(self, *args, **kwargs):
		Exception.__init__(self, 'A database error has occured')


class PushCheckList(Base):
    __tablename__ = "push_checklist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request = Column(UnsignedInteger(), nullable=False)
    type = Column(String(50), nullable=True)
    complete = Column(SmallInteger, nullable=False, default=0)
    target = Column(String(50), nullable=True)


class PushPlans(Base):
    __tablename__ = "push_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request = Column(Integer, nullable=True)
    content = Column(String)
    path = Column(String)


class PushPushContents(Base):
    __tablename__ = "push_pushcontents"

    request = Column(Integer, primary_key=True, default=0)
    push = Column(Integer, primary_key=True, default=0)


class PushPushes(Base):
    __tablename__ = "push_pushes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String)
    user = Column(String)
    branch = Column(String)
    revision = Column(String(40), nullable=True)
    state = Column(String)
    created = Column(Integer, nullable=True)
    modified = Column(Integer, nullable=True)
    pushtype = Column(String)
    extra_pings = Column(String)


class PushRemovals(Base):
    __tablename__ = "push_removals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request = Column(Integer, nullable=False)
    push = Column(Integer, nullable=False)
    reason = Column(String)
    pushmaster = Column(String)
    timestamp = Column(UnsignedInteger(), nullable=False)


class PushRequests(Base):
    __tablename__ = "push_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user = Column(String)
    state = Column(String)
    repo = Column(String)
    branch = Column(String)
    revision = Column(String(40), nullable=True)
    tags = Column(String)
    created = Column(Integer, nullable=True)
    modified = Column(Integer, nullable=True)
    title = Column(String)
    comments = Column(String)
    reviewid = Column(Integer, nullable=True)
    description = Column(String)


push_checklist = PushCheckList.__table__
push_requests = PushRequests.__table__
push_plans = PushPlans.__table__
push_pushes = PushPushes.__table__
push_pushcontents = PushPushContents.__table__
push_removals = PushRemovals.__table__


def init_db():
    global engine
    if engine is None:
        engine = SA.create_engine(Settings['db_uri'], pool_recycle=3600)

        if Settings["db_uri"].startswith("sqlite"):
            # Prepare tables when using sqlite database
            logging.info("Creating sqlite database.")
            Base.metadata.create_all(engine)

def finalize_db():
    global engine
    engine = None

def execute_cb(query, callback_fn):
    success = True
    try:
        conn = engine.connect()
        results = conn.execute(query)
    except Exception:
        results = None
        success = False
        logging.error("Error executing query: %s" % str(query.compile()))
    finally:
        callback_fn(success, results)
        conn.close()

def execute_transaction_cb(queries, callback_fn, condition=None):
    """Execute a list of queries in transaction.

    Aguments:

    queries: a list of sqlalchemy queries.

    callback_fn: a callable to call after execution. callback_fn
    should accept two arguments, a boolean (success) and a list
    (results).

    condition: a tuple of (sqlalchemy query, check function). if
    defined we'll execute the query and apply check function to the
    result. Only if check function returns true we'll move on with
    executing the querires list.
    """
    try:
        success = True
        results = []
        conn = engine.connect()
        transaction = conn.begin()
        try:
            if condition:
                select, check_fn = condition
                if not check_fn(conn.execute(select)):
                    raise Exception, "Condition failed: %s" % str(select.compile())

            for query in queries:
                results.append(conn.execute(query))
            transaction.commit()
        except Exception, e:
            logging.error(e)
            transaction.rollback()
            raise
    except Exception:
        results = None
        success = False
        logging.error(
            "Error executing transaction: %s" % "\n".join([str(q.compile()) for q in queries])
        )
    finally:
        callback_fn(success, results)
        conn.close()
