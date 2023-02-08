from abc import abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, List, Protocol

from psycopg import AsyncCursor
from psycopg.rows import class_row
from psycopg_pool import AsyncConnectionPool

from .misc.lrucache import LRUCache


@dataclass
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

    original_id: int
    original_channel: int
    mirror_id: int
    mirror_channel: int


class Database(Protocol):
    """
    Base database class

    Provides two user functions that work messages mapping data:
    - Add new `MirrorMessage` object to database
    - Get `MirrorMessage` object from database by original message ID
    """

    @abstractmethod
    async def _async__init__(self: 'Database') -> 'Database':
        """Async initializer"""
        raise NotImplementedError

    def __await__(self):
        return self._async__init__().__await__()

    @abstractmethod
    async def insert(self: 'Database', entity: MirrorMessage) -> None:
        """Inserts `MirrorMessage` object into database

        Args:
            entity (`MirrorMessage`): `MirrorMessage` object
        """
        raise NotImplementedError

    @abstractmethod
    async def insert_batch(self: 'Database', entity: List[MirrorMessage]) -> None:
        """Inserts `MirrorMessage` objects into database

        Args:
            entity (`List[MirrorMessage]`): List of `MirrorMessage` objects
        """
        raise NotImplementedError

    @abstractmethod
    async def get_messages(self: 'Database', original_id: int, original_channel: int) -> List[MirrorMessage]:
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
    async def get_messages_batch(self: 'Database', original_ids: List[int], original_channel: int) -> List[MirrorMessage]:
        """
        Finds `MirrorMessage` objects with `original_id` and `original_channel` values

        Args:
            original_ids (`List[int]`): Original message IDs
            original_channel (`int`): Source channel ID

        Returns:
            List[MirrorMessage]
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_messages(self: 'Database', original_id: int, original_channel: int) -> None:
        """
        Deletes `MirrorMessage` objects with `original_id` and `original_channel` values

        Args:
            original_id (`int`): Original message ID
            original_channel (`int`): Source channel ID
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_messages_batch(self: 'Database', original_ids: List[int], original_channel: int) -> None:
        """
        Deletes `MirrorMessage` objects with `original_id` and `original_channel` values

        Args:
            original_ids (`List[int]`): Original message IDs
            original_channel (`int`): Source channel ID
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        return self.__class__.__name__


class InMemoryDatabase(Database):
    """
    In-memory database class messages mapping implementation.

    Provides two user functions that work with 'binding_id' table:
    - Add new `MirrorMessage` object to database
    - Get `MirrorMessage` object from database by original message ID
    """

    MAX_CAPACITY = 100

    def __init__(self: 'InMemoryDatabase', max_capacity: int = MAX_CAPACITY) -> 'InMemoryDatabase':
        self.__storage = LRUCache[str, List[MirrorMessage]](
            capacity=max_capacity)

    async def _async__init__(self: 'InMemoryDatabase') -> 'InMemoryDatabase':
        return self

    async def insert(self: 'InMemoryDatabase', entity: MirrorMessage) -> None:
        """Inserts `MirrorMessage` object into database

        Args:
            entity (`MirrorMessage`): `MirrorMessage` object
        """
        self.__storage.setdefault(self.__build_message_hash(
            entity.original_id, entity.original_channel), []).append(entity)

    async def insert_batch(self: 'InMemoryDatabase', entity: List[MirrorMessage]) -> None:
        """Inserts `MirrorMessage` objects into database

        Args:
            entity (`List[MirrorMessage]`): List of `MirrorMessage` objects
        """
        for e in entity:
            await self.insert(e)

    async def get_messages(self: 'InMemoryDatabase', original_id: int, original_channel: int) -> List[MirrorMessage]:
        """
        Finds `MirrorMessage` objects with `original_id` and `original_channel` values

        Args:
            original_id (`int`): Original message ID
            original_channel (`int`): Source channel ID

        Returns:
            List[MirrorMessage]
        """
        return self.__storage.get(self.__build_message_hash(original_id, original_channel), [])

    async def get_messages_batch(self: 'InMemoryDatabase', original_ids: List[int], original_channel: int) -> List[MirrorMessage]:
        """
        Finds `MirrorMessage` objects with `original_id` and `original_channel` values

        Args:
            original_ids (`List[int]`): Original message IDs
            original_channel (`int`): Source channel ID

        Returns:
            List[MirrorMessage]
        """
        messages: List[MirrorMessage] = []
        for idx in original_ids:
            messages.extend(await self.get_messages(idx, original_channel))
        return messages

    async def delete_messages(self: 'InMemoryDatabase', original_id: int, original_channel: int) -> None:
        """
        Deletes `MirrorMessage` objects with `original_id` and `original_channel` values

        Args:
            original_id (`int`): Original message ID
            original_channel (`int`): Source channel ID
        """
        try:
            del self.__storage[self.__build_message_hash(
                original_id, original_channel)]
        except KeyError:
            pass

    async def delete_messages_batch(self: 'InMemoryDatabase', original_ids: List[int], original_channel: int) -> None:
        """
        Deletes `MirrorMessage` objects with `original_id` and `original_channel` values

        Args:
            original_ids (`List[int]`): Original message IDs
            original_channel (`int`): Source channel ID
        """
        for idx in original_ids:
            await self.delete_messages(idx, original_channel)

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
        min_conn (`int`, optional): Min amount of connections. Defaults to MIN_CONN (0).
        max_conn (`int`, optional): Max amount of connections. Defaults to MAX_CONN (10).
    """

    MIN_CONN = 0
    MAX_CONN = 10

    def __init__(
        self,
        connection_string: str,
        min_conn: int = MIN_CONN,
        max_conn: int = MAX_CONN
    ) -> 'PostgresDatabase':
        self.__conn_info = connection_string
        self.__min_conn = min_conn
        self.__max_conn = max_conn

    async def _async__init__(self: 'PostgresDatabase') -> 'PostgresDatabase':
        self.connection_pool = AsyncConnectionPool(
            conninfo=self.__conn_info, min_size=self.__min_conn, max_size=self.__max_conn)
        await self.__create_tables_if_not_exists()
        return self

    async def insert(self: 'PostgresDatabase', entity: MirrorMessage) -> None:
        """Inserts `MirrorMessage` object into database

        Args:
            entity (`MirrorMessage`): `MirrorMessage` object
        """
        async with self.__pg_cursor() as cursor:
            await cursor.execute("""
                                INSERT INTO binding_id (original_id, original_channel, mirror_id, mirror_channel)
                                VALUES (%s, %s, %s, %s)
                                """, (entity.original_id, entity.original_channel, entity.mirror_id, entity.mirror_channel,))

    async def insert_batch(self: 'PostgresDatabase', entity: List[MirrorMessage]) -> None:
        """Inserts `MirrorMessage` objects into database

        Args:
            entity (`List[MirrorMessage]`): List of `MirrorMessage` objects
        """
        async with self.__pg_cursor() as cursor:
            await cursor.executemany("""
                                INSERT INTO binding_id (original_id, original_channel, mirror_id, mirror_channel)
                                VALUES (%s, %s, %s, %s)
                                """, [(e.original_id, e.original_channel, e.mirror_id, e.mirror_channel,) for e in entity])

    async def get_messages(self: 'PostgresDatabase', original_id: int, original_channel: int) -> List[MirrorMessage]:
        """
        Finds `MirrorMessage` objects with `original_id` and `original_channel` values

        Args:
            original_id (`int`): Original message ID
            original_channel (`int`): Source channel ID

        Returns:
            List[MirrorMessage]
        """
        rows: List[MirrorMessage] = []
        async with self.__pg_cursor() as cursor:
            cursor.row_factory = class_row(MirrorMessage)
            await cursor.execute("""
                                SELECT original_id, original_channel, mirror_id, mirror_channel
                                FROM binding_id
                                WHERE original_id = %s
                                AND original_channel = %s
                                """, (original_id, original_channel,))
            rows = await cursor.fetchall()
        return rows

    async def get_messages_batch(self: 'PostgresDatabase', original_ids: List[int], original_channel: int) -> List[MirrorMessage]:
        """
        Finds `MirrorMessage` objects with `original_id` and `original_channel` values

        Args:
            original_ids (`List[int]`): Original message IDs
            original_channel (`int`): Source channel ID

        Returns:
            List[MirrorMessage]
        """
        rows: List[MirrorMessage] = []
        async with self.__pg_cursor() as cursor:
            cursor.row_factory = class_row(MirrorMessage)
            await cursor.execute("""
                                SELECT original_id, original_channel, mirror_id, mirror_channel
                                FROM binding_id
                                WHERE original_id = ANY(%s)
                                AND original_channel = %s
                                """, (original_ids, original_channel,))
            rows = await cursor.fetchall()
        return rows

    async def delete_messages(self: 'PostgresDatabase', original_id: int, original_channel: int) -> None:
        """
        Deletes `MirrorMessage` objects with `original_id` and `original_channel` values

        Args:
            original_id (`int`): Original message ID
            original_channel (`int`): Source channel ID
        """
        async with self.__pg_cursor() as cursor:
            await cursor.execute("""
                                DELETE FROM binding_id
                                WHERE original_id = %s
                                AND original_channel = %s
                                """, (original_id, original_channel,))

    async def delete_messages_batch(self: 'PostgresDatabase', original_ids: List[int], original_channel: int) -> None:
        """
        Deletes `MirrorMessage` objects with `original_id` and `original_channel` values

        Args:
            original_ids (`List[int]`): Original message IDs
            original_channel (`int`): Source channel ID
        """
        async with self.__pg_cursor() as cursor:
            await cursor.execute("""
                                DELETE FROM binding_id
                                WHERE original_id = ANY(%s)
                                AND original_channel = %s
                                """, (original_ids, original_channel,))

    async def __create_tables_if_not_exists(self: 'PostgresDatabase'):
        """Create tables if not exists"""
        async with self.__pg_cursor() as cursor:
            await cursor.execute("""
                                CREATE TABLE IF NOT EXISTS binding_id(   
                                    id serial primary key not null,
                                    original_id bigint not null,
                                    original_channel bigint not null,
                                    mirror_id bigint not null,
                                    mirror_channel bigint not null)
                                """)

    @asynccontextmanager
    async def __pg_cursor(self: 'PostgresDatabase') -> AsyncIterator[AsyncCursor[Any]]:
        """
        Gets connection from pool and yields cursor within current context

        Yields:
            (`psycopg.AsyncCursor`): Cursor
        """
        async with self.connection_pool.connection() as con:
            async with con.cursor() as cur:
                yield cur
