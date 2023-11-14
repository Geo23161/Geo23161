import sqlite3
import psycopg2

# Connexion à la base de données SQLite
sqlite_conn = sqlite3.connect('db.sqlite3')
sqlite_cursor = sqlite_conn.cursor()

# Connexion à la base de données PostgreSQL
pg_conn = psycopg2.connect(
    dbname='datingp',
    user='geo',
    password='georis',
    host='localhost', 
    port='5432'  
)
pg_cursor = pg_conn.cursor()

# Récupérer la liste des tables de la base de données SQLite
sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [table[0] for table in sqlite_cursor.fetchall()]

# Parcourir toutes les tables et transférer les données
for table_name in tables:
    # Récupérer les données de la table SQLite
    sqlite_cursor.execute(f'SELECT * FROM {table_name}')
    data_to_transfer = sqlite_cursor.fetchall()

    # Récupérer la description (schéma) de la table SQLite
    sqlite_cursor.execute(f'PRAGMA table_info({table_name})')
    sqlite_table_description = sqlite_cursor.fetchall()

    # Créer la table correspondante dans PostgreSQL
    pg_table_name = table_name
    pg_cursor.execute(f"DROP TABLE IF EXISTS {pg_table_name};")  # Supprimer la table si elle existe
    pg_conn.commit()

    # Générer la requête de création de table en PostgreSQL
    create_table_query = f"CREATE TABLE {pg_table_name} ("
    for column_info in sqlite_table_description:
        column_name = column_info[1]
        column_type = column_info[2]
        create_table_query += f"{column_name} {column_type}, "
    create_table_query = create_table_query.rstrip(', ') + ")"

    # Exécuter la requête pour créer la table en PostgreSQL
    pg_cursor.execute(create_table_query)
    pg_conn.commit()

    # Générer la requête d'insertion
    columns = ','.join(column_info[1] for column_info in sqlite_table_description)
    placeholders = ','.join(['%s'] * len(data_to_transfer[0]))
    insert_query = f'INSERT INTO {pg_table_name} ({columns}) VALUES ({placeholders})'

    # Insérer les données dans la base de données PostgreSQL
    pg_cursor.executemany(insert_query, data_to_transfer)
    pg_conn.commit()

# Fermer les connexions
sqlite_cursor.close()
sqlite_conn.close()
pg_cursor.close()
pg_conn.close()
