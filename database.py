import logging
from contextlib import contextmanager

import psycopg2
from psycopg2 import extras, pool
from psycopg2.extensions import AsIs, ISQLQuote, adapt

logger = logging.getLogger(__name__)

class MirrorMessage(object):
    """
    Mirror message class contains message id mapping
    original_message_id <-> mirror_message_id
    """
    def __init__(self, original_id: int, mirror_id: int, original_channel: int):
        """Ctor

        Args:
            original_id (int): Original message ID
            mirror_id (int): Mirror message ID
            original_channel (int): Source channel ID
        """
        self.original_id = original_id
        self.mirror_id = mirror_id
        self.original_channel = original_channel

    def __str__(self):
        return f'{self.__class__}: {self.__dict__}'
    
    def __repr__(self):
        return self.__str__()

    def __conform__(self, protocol):
        if protocol is ISQLQuote:
            return self.getquoted()
        return None

    def getquoted(self):
        _original_id = adapt(self.original_id).getquoted().decode('utf-8')
        _mirror_id = adapt(self.mirror_id).getquoted().decode('utf-8')
        _original_channel = adapt(self.original_channel).getquoted().decode('utf-8')
        return AsIs(f'{_original_id}, {_mirror_id}, {_original_channel}')

class Database:

    MIN_CONN = 2
    MAX_CONN = 10

    def __init__(self, connection_string):
        self.connection_string = connection_string
        self.connection_pool = pool.SimpleConnectionPool(self.MIN_CONN, self.MAX_CONN, self.connection_string)
        self.__create_table()

    @contextmanager
    def __db(self):
        con = self.connection_pool.getconn()
        cur = con.cursor()
        try:
            yield con, cur
        finally:
            cur.close()
            self.connection_pool.putconn(con)

    def __create_table(self):
        with self.__db() as (connection, cursor):
            try:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS binding_id
                    (   id serial primary key not null,
                        original_id bigint not null,
                        mirror_id bigint not null,
                        original_channel bigint not null
                    )
                    """
                )
            except Exception as e:
                logger.error(e, exc_info=True)
                connection.rollback()
            else:
                connection.commit()

    
    def insert(self, entity: MirrorMessage):
        with self.__db() as (connection, cursor):
            try:
                cursor.execute("""
                                INSERT INTO binding_id (original_id, mirror_id, original_channel)
                                VALUES (%s)
                                """, (entity,))
            except Exception as e:
                logger.error(e, exc_info=True)
                connection.rollback()
            else:
                connection.commit()

    def find_by_original_id(self, original_id: int, original_channel: int) -> MirrorMessage:
        """Getting MirrorMessage object

        Args:
            original_id (int): Original message ID
            original_channel (int): Source channel ID

        Returns:
            MirrorMessage
        """
        row = None
        with self.__db() as (connection, cursor):
            try:
                cursor.execute("""
                                SELECT original_id, mirror_id, original_channel
                                FROM binding_id
                                WHERE original_id = %s
                                AND original_channel = %s
                                """, (original_id, original_channel,))
            except Exception as e:
                logger.error(e, exc_info=True)
            else:
                row = cursor.fetchone()
        return MirrorMessage(*row) if row else None
