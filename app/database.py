import logging
from contextlib import contextmanager
from typing import List
from psycopg2 import pool
from psycopg2.extensions import AsIs, ISQLQuote, adapt

logger = logging.getLogger(__name__)


class MirrorMessage:
    """
    Mirror message class contains id message mappings
    original_message_id <-> mirror_message_id

    Args:
        original_id (int): Original message ID
        original_channel (int): Source channel ID
        mirror_id (int): Mirror message ID
        mirror_channel (int): Mirror channel ID
    """

    def __init__(self, original_id: int, original_channel: int,
                 mirror_id: int, mirror_channel: int):
        self.original_id = original_id
        self.mirror_id = mirror_id
        self.original_channel = original_channel
        self.mirror_channel = mirror_channel

    def __str__(self):
        return f'{self.__class__}: {self.__dict__}'

    def __repr__(self):
        return self.__str__()

    def __conform__(self, protocol):
        if protocol is ISQLQuote:
            return self.__getquoted()
        return None

    def __getquoted(self):
        _original_id = adapt(self.original_id).getquoted().decode('utf-8')
        _original_channel = adapt(
            self.original_channel).getquoted().decode('utf-8')
        _mirror_id = adapt(self.mirror_id).getquoted().decode('utf-8')
        _mirror_channel = adapt(
            self.mirror_channel).getquoted().decode('utf-8')
        return AsIs(f'{_original_id}, {_original_channel}, {_mirror_id}, {_mirror_channel}')


class Database:
    """Postgres database connection implementation.

    Provides two user functions that work with 'binding_id' table:
    - Add new 'MirrorMessage' object to database
    - Get 'MirrorMessage' object from database by original message ID

    Args:
        connection_string (str): Postgres connection URL
        min_conn (int, optional): Min amount of connections. Defaults to MIN_CONN (2).
        max_conn (int, optional): Max amount of connections. Defaults to MAX_CONN (10).
    """

    MIN_CONN = 2
    MAX_CONN = 10

    def __init__(self, connection_string: str, min_conn: int = MIN_CONN, max_conn: int = MAX_CONN):
        self.connection_string = connection_string
        self.connection_pool = pool.SimpleConnectionPool(
            min_conn, max_conn, self.connection_string)
        self.__create_table()

    @contextmanager
    def __db(self):
        """Gets connection from pool and creates cursor within current context

        Yields:
            (psycopg2.extensions.connection, psycopg2.extensions.cursor): Connection and cursor
        """
        con = self.connection_pool.getconn()
        cur = con.cursor()
        try:
            yield con, cur
        finally:
            cur.close()
            self.connection_pool.putconn(con)

    def __create_table(self):
        """Creates 'binding_id' table
        """
        with self.__db() as (connection, cursor):
            try:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS binding_id
                    (   id serial primary key not null,
                        original_id bigint not null,
                        original_channel bigint not null,
                        mirror_id bigint not null,
                        mirror_channel bigint not null
                    )
                    """
                )
            except Exception as e:
                logger.error(e, exc_info=True)
                connection.rollback()
            else:
                connection.commit()

    def insert(self, entity: MirrorMessage):
        """Inserts into database 'MirrorMessage' object

        Args:
            entity (MirrorMessage): 'MirrorMessage' object
        """
        with self.__db() as (connection, cursor):
            try:
                cursor.execute("""
                                INSERT INTO binding_id (original_id, original_channel, mirror_id, mirror_channel)
                                VALUES (%s)
                                """, (entity,))
            except Exception as e:
                logger.error(e, exc_info=True)
                connection.rollback()
            else:
                connection.commit()

    def find_by_original_id(self, original_id: int, original_channel: int) -> List[MirrorMessage]:
        """Finds MirrorMessage objects with original_id and original_channel values

        Args:
            original_id (int): Original message ID
            original_channel (int): Source channel ID

        Returns:
            List[MirrorMessage]
        """
        rows = None
        with self.__db() as (_, cursor):
            try:
                cursor.execute("""
                                SELECT original_id, original_channel, mirror_id, mirror_channel
                                FROM binding_id
                                WHERE original_id = %s
                                AND original_channel = %s
                                """, (original_id, original_channel,))
            except Exception as e:
                logger.error(e, exc_info=True)
            else:
                rows = cursor.fetchall()
        return [MirrorMessage(*row) for row in rows] if rows else None
