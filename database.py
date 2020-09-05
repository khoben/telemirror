import psycopg2
from psycopg2 import extras
from psycopg2.extensions import AsIs
from settings import DB_URL


def sql_insert_dict(data):
    columns = ', '.join(data.keys())
    placeholders = ',? '.join("%s" * len(data))
    sql = 'INSERT INTO binding_id ({}) VALUES ({})'.format(
        columns, placeholders)
    # print(sql)
    return sql


def sql_update_dict(data, id):
    columns = 'SET '
    columns += ', '.join([k+'='+v for k, v in data.items()])
    where = 'id={}'.format(id_match)
    sql = 'UPDATE binding_id SET {} WHERE {}'.format(columns, where)
    # print(sql)
    return sql


def create_table():
    connection = psycopg2.connect(DB_URL)
    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS binding_id
            (   id serial primary key not null,
                original_id bigint not null,
                mirror_id bigint not null
            )
            """
        )
        connection.commit()

    except Exception as e:
        print(e)
    connection.close()


def insert(entity):
    connection = psycopg2.connect(DB_URL)
    cursor = connection.cursor()
    try:
        columns = entity.keys()
        values = entity.values()

        sql_insert = 'insert into binding_id (%s) values %s'

        cursor.execute(sql_insert, (AsIs(','.join(columns)), tuple(values)))
        # cursor.execute(sql_insert_dict(match), tuple(match.values()))
        connection.commit()
    except Exception as e:
        print(e)
    connection.close()


def read():
    connection = psycopg2.connect(DB_URL)
    cursor = connection.cursor()
    cursor.execute("""
                    SELECT * FROM binding_id
                    """)
    rows = cursor.fetchall()
    connection.close()
    return rows


def read_by_id(id_entity):
    try:
        connection = psycopg2.connect(DB_URL)
        cursor = connection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
                        SELECT * FROM binding_id
                        WHERE id = %s
                        """, (id_entity, ))
        rows = cursor.fetchone()
        connection.close()
        return rows
    except Exception as e:
        print(e)


def find_by_id(id_entity):
    try:
        connection = psycopg2.connect(DB_URL)
        cursor = connection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
                        SELECT * FROM binding_id
                        WHERE original_id = %s
                        """, (id_entity, ))
        rows = cursor.fetchone()
        connection.close()
        return rows
    except Exception as e:
        print(e)


if __name__ == "__main__":
    print(read())
