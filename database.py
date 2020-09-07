import logging

import psycopg2
from psycopg2 import extras
from psycopg2.extensions import AsIs

from settings import (DB_URL)

logger = logging.getLogger(__name__)

"""
# Table 'binding_id'
# id                primary key
# original_id       original message id
# mirror_id         mirror message id
# original_channel  original channel id
"""

def create_table():
    try:
        connection = psycopg2.connect(DB_URL)
    except Exception as e:
        logger.error(e)
        connection = None
    if connection:
        cursor = connection.cursor()
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
        cursor.close()
        connection.close()


def insert(entity):
    try:
        connection = psycopg2.connect(DB_URL)
    except Exception as e:
        logger.error(e, exc_info=True)
        connection = None
    if connection:
        cursor = connection.cursor()
        try:
            columns = entity.keys()
            values = entity.values()

            sql_insert = 'INSERT INTO binding_id (%s) values %s'

            try:
                cursor.execute(sql_insert, (AsIs(','.join(columns)), tuple(values)))
            except Exception as e:
                logger.error(e, exc_info=True)
                connection.rollback()
            else:
                connection.commit()

        except Exception as e:
            logger.error(e, exc_info=True)

        cursor.close()
        connection.close()


def read():
    rows = None
    try:
        connection = psycopg2.connect(DB_URL)
    except Exception as e:
        logger.error(e, exc_info=True)
        connection = None
    if connection:
        cursor = connection.cursor()
        try:
            cursor.execute("""
                            SELECT original_id, mirror_id, original_channel
                            FROM binding_id
                            """)
        except Exception as e:
            logger.error(e, exc_info=True)
        else:
            rows = cursor.fetchall()
        cursor.close()
        connection.close()
    return rows

def find_by_original_id(original_id, original_channel):
    row = None
    try:
        connection = psycopg2.connect(DB_URL)
    except Exception as e:
        logger.error(e, exc_info=True)
        connection = None

    if connection:
        cursor = connection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
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
        cursor.close()
        connection.close()
    return row

create_table()

if __name__ == "__main__":
    print(read())
