# -----------------------------------------------------------------------------
# Copyright (c) 2025, Oracle and/or its affiliates.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
# http://oss.oracle.com/licenses/upl.
# -----------------------------------------------------------------------------

import oracledb

CREATE_PEOPLE_DDL = """
    CREATE TABLE people
                (
                    id       NUMBER PRIMARY KEY,
                    name     VARCHAR2(50),
                    age      NUMBER,
                    height   NUMBER,
                    hometown VARCHAR2(100)
                )
"""

CREATE_GYMNAST_DDL = """
     CREATE TABLE gymnast
                (
                    id                    NUMBER PRIMARY KEY,
                    floor_ex_points       NUMBER,
                    rings_points          NUMBER,
                    parallel_bars_points  NUMBER,
                    horizontal_bar_points NUMBER,
                    total_points          NUMBER,
                    FOREIGN KEY (id) REFERENCES people (id)
                )
"""

CREATE_DIRECTOR_DDL = """
    CREATE TABLE Director (
     director_id     INT PRIMARY KEY,
     name            VARCHAR(10)
)
"""

CREATE_MOVIE_DDL = """
CREATE TABLE Movie (
     movie_id        INT PRIMARY KEY,
     title           VARCHAR(100),
     release_date    DATE,
     genre           VARCHAR(50),
     director_id     INT,
     FOREIGN KEY (director_id) REFERENCES Director(director_id)
)
"""

CREATE_ACTOR_DDL = """
    CREATE TABLE Actor (
     actor_id        INT PRIMARY KEY,
     name            VARCHAR(100)
)
"""

INSERT_PEOPLE_DML = """
     INSERT INTO people (id, name, age, height, hometown)
     VALUES (: 1, :2, :3, :4, :5)
"""

INSERT_GYMNAST_DML = """
    INSERT INTO gymnast
    (id, floor_ex_points, rings_points,
     parallel_bars_points, horizontal_bar_points,
     total_points)
    VALUES (: 1, :2, :3, :4, :5, :6)
"""

PEOPLE_DATA = [
    (1, "John Smith", 22, 170, "New York"),
    (2, "Emma Johnson", 20, 165, "Los Angeles"),
    (3, "Michael Brown", 24, 180, "Chicago"),
    (4, "Sophia Lee", 19, 160, "Houston"),
    (5, "William Kim", 21, 175, "San Francisco"),
]

GYMNAST_DATA = [
    (1, 9.5, 8.8, 9.2, 9.0, 36.5),
    (2, 8.7, 9.0, 8.5, 8.9, 35.1),
    (3, 9.0, 9.2, 9.1, 9.3, 36.6),
    (4, 8.5, 8.0, 8.7, 8.3, 33.5),
    (5, 9.2, 8.5, 8.9, 9.1, 35.7),
]


def test_create_schema(connection, cursor):
    for tbl in ("gymnast", "people", "director", "movie", "actor"):
        try:
            cursor.execute(f"DROP TABLE {tbl} CASCADE CONSTRAINTS")
            print(f"Dropped table {tbl}")
        except oracledb.Error:
            print(f"Table {tbl} does not exist, skipping")

    for ddl in (
        CREATE_PEOPLE_DDL,
        CREATE_GYMNAST_DDL,
        CREATE_DIRECTOR_DDL,
        CREATE_MOVIE_DDL,
        CREATE_ACTOR_DDL,
    ):
        cursor.execute(ddl)

    cursor.executemany(INSERT_PEOPLE_DML, PEOPLE_DATA)
    cursor.executemany(INSERT_GYMNAST_DML, GYMNAST_DATA)
    connection.commit()
