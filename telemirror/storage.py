import collections
import logging
from abc import abstractmethod
from contextlib import contextmanager
from typing import List, Protocol

from psycopg2 import pool
from psycopg2.extensions import AsIs, ISQLQuote, adapt


class MirrorMessage:
    """
    Mirror message class contains id message mappings:

    `original_message_id` <-> `mirror_message_id`

    Args:
        original_id (`int`): Original message ID
        original_channel (`int`): Source channel ID
        mirror_id (`int`): Mirror message ID
        mirror_channel (`int`): Mirror channel ID
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


class Database(Protocol):
    """
    Base database class

    Provides two user functions that work messages mapping data:
    - Add new `MirrorMessage` object to database
    - Get `MirrorMessage` object from database by original message ID
    """

    @abstractmethod
    def insert(self: 'Database', entity: MirrorMessage) -> None:
        """Inserts `MirrorMessage` object into database

        Args:
            entity (`MirrorMessage`): `MirrorMessage` object
        """
        raise NotImplementedError

    @abstractmethod
    def get_messages(self: 'Database', original_id: int, original_channel: int) -> List[MirrorMessage]:
        """
        Finds `MirrorMessage` objects with `original_id` and `original_channel` values

        Args:
            original_id (`int`): Original message ID
            original_channel (`int`): Source channel ID

        Returns:
            List[MirrorMessage]
        """
        raise NotImplementedError

    @abstractmethod
    def delete_messages(self: 'Database', original_id: int, original_channel: int) -> None:
        """
        Deletes `MirrorMessage` objects with `original_id` and `original_channel` values

        Args:
            original_id (`int`): Original message ID
            original_channel (`int`): Source channel ID
        """
        raise NotImplementedError


class InMemoryDatabase(Database):
    """
    In-memory database class messages mapping implementation.

    Provides two user functions that work with 'binding_id' table:
    - Add new `MirrorMessage` object to database
    - Get `MirrorMessage` object from database by original message ID
    """

    class LimitedDict(collections.OrderedDict):
        """
        Dict with a limited length, ejecting LRUs as needed.
        """

        def __init__(self, *args, capacity, free_factor=0.5, **kwargs):
            assert capacity > 0
            assert free_factor > 0.1 and free_factor <= 1.0
            self.capacity = capacity
            self.keep_last = max(1.0, capacity * (1.0 - free_factor))

            super().__init__(*args, **kwargs)

        def __setitem__(self, key, value):
            super().__setitem__(key, value)
            super().move_to_end(key)

            if len(self) > self.capacity:
                while len(self) > self.keep_last:
                    oldkey = next(iter(self))
                    super().__delitem__(oldkey)

        def __getitem__(self, key):
            val = super().__getitem__(key)
            super().move_to_end(key)

            return val

    MAX_CAPACITY = 100

    def __init__(self: 'InMemoryDatabase', max_capacity: int = MAX_CAPACITY):
        self.__stored = self.LimitedDict[str, List[MirrorMessage]](
            capacity=max_capacity)

    def insert(self: 'InMemoryDatabase', entity: MirrorMessage) -> None:
        """Inserts `MirrorMessage` object into database

        Args:
            entity (`MirrorMessage`): `MirrorMessage` object
        """
        self.__stored.setdefault(self.__build_message_hash(
            entity.original_id, entity.original_channel), []).append(entity)

    def get_messages(self: 'InMemoryDatabase', original_id: int, original_channel: int) -> List[MirrorMessage]:
        """
        Finds `MirrorMessage` objects with `original_id` and `original_channel` values

        Args:
            original_id (`int`): Original message ID
            original_channel (`int`): Source channel ID

        Returns:
            List[MirrorMessage]
        """
        return self.__stored.get(self.__build_message_hash(original_id, original_channel), None)

    def delete_messages(self: 'InMemoryDatabase', original_id: int, original_channel: int) -> None:
        """
        Deletes `MirrorMessage` objects with `original_id` and `original_channel` values

        Args:
            original_id (`int`): Original message ID
            original_channel (`int`): Source channel ID
        """
        try:
            del self.__stored[self.__build_message_hash(original_id, original_channel)]
        except KeyError:
            pass

    def __build_message_hash(self: 'InMemoryDatabase', original_id: int, original_channel: int) -> str:
        """
        Builds message hash from `original_id` and `original_channel` values

        Args:
            original_id (`int`): Original message ID
            original_channel (`int`): Source channel ID

        Returns:
            str
        """
        return f'{original_channel}:{original_id}'


class PostgresDatabase(Database):
    """
    Postgres database messages mapping implementation.

    Binding database table:

    ```
    create table binding_id (id serial primary key not null,
                original_id bigint not null,
                original_channel bigint not null,
                mirror_id bigint not null,
                mirror_channel bigint not null)
    ```

    Provides two user functions that work with 'binding_id' table:
    - Add new `MirrorMessage` object to database
    - Get `MirrorMessage` object from database by original message ID

    Args:
        connection_string (`str`): Postgres connection URL
        min_conn (`int`, optional): Min amount of connections. Defaults to MIN_CONN (2).
        max_conn (`int`, optional): Max amount of connections. Defaults to MAX_CONN (10).
    """

    MIN_CONN = 2
    MAX_CONN = 10

    def __init__(self, connection_string: str, min_conn: int = MIN_CONN, max_conn: int = MAX_CONN, logger: logging.Logger = logging.getLogger(__name__)):
        self.__logger = logger
        self.connection_pool = pool.SimpleConnectionPool(
            min_conn, max_conn, connection_string)
        self.__init_binding_table()

    def insert(self: 'PostgresDatabase', entity: MirrorMessage) -> None:
        """Inserts `MirrorMessage` object into database

        Args:
            entity (`MirrorMessage`): `MirrorMessage` object
        """
        with self.__db() as (connection, cursor):
            try:
                cursor.execute("""
                                INSERT INTO binding_id (original_id, original_channel, mirror_id, mirror_channel)
                                VALUES (%s)
                                """, (entity,))
            except Exception as e:
                self.__logger.error(e, exc_info=True)
                connection.rollback()
            else:
                connection.commit()

    def get_messages(self: 'PostgresDatabase', original_id: int, original_channel: int) -> List[MirrorMessage]:
        """
        Finds `MirrorMessage` objects with `original_id` and `original_channel` values

        Args:
            original_id (`int`): Original message ID
            original_channel (`int`): Source channel ID

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
                self.__logger.error(e, exc_info=True)
            else:
                rows = cursor.fetchall()
        return [MirrorMessage(*row) for row in rows] if rows else None

    def delete_messages(self: 'PostgresDatabase', original_id: int, original_channel: int) -> None:
        """
        Deletes `MirrorMessage` objects with `original_id` and `original_channel` values

        Args:
            original_id (`int`): Original message ID
            original_channel (`int`): Source channel ID
        """
        with self.__db() as (connection, cursor):
            try:
                cursor.execute("""
                                DELETE FROM binding_id
                                WHERE original_id = %s
                                AND original_channel = %s
                                """, (original_id, original_channel,))
            except Exception as e:
                self.__logger.error(e, exc_info=True)
                connection.rollback()
            else:
                connection.commit()

    @contextmanager
    def __db(self: 'PostgresDatabase'):
        """
        Gets connection from pool and creates cursor within current context

        Yields:
            (`psycopg2.extensions.connection`, `psycopg2.extensions.cursor`): Connection and cursor
        """
        con = self.connection_pool.getconn()
        cur = con.cursor()
        try:
            yield con, cur
        finally:
            cur.close()
            self.connection_pool.putconn(con)

    def __init_binding_table(self: 'PostgresDatabase'):
        """
        Init binding table
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
                self.__logger.error(e, exc_info=True)
                connection.rollback()
            else:
                connection.commit()
