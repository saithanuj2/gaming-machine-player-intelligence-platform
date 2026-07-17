import pyodbc


CONNECTION_STRING = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=localhost,1433;"
    "DATABASE=GamingIntelligenceDB;"
    "UID=sa;"
    "PWD=Gaming@2026Strong;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)


def main() -> None:
    connection = None

    try:
        connection = pyodbc.connect(
            CONNECTION_STRING,
            timeout=10,
        )

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                DB_NAME() AS database_name,
                @@SERVERNAME AS server_name,
                @@VERSION AS sql_server_version;
            """
        )

        row = cursor.fetchone()

        print("SQL Server connection successful.")
        print(f"Database: {row.database_name}")
        print(f"Server: {row.server_name}")
        print(f"Version: {row.sql_server_version}")

        cursor.close()

    except pyodbc.Error as error:
        print("SQL Server connection failed.")
        print(error)
        raise

    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    main()