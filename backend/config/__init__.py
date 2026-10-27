# Lets Django use PyMySQL as the MySQL driver (pure Python: no C build tools,
# works on Vercel). Harmless when PostgreSQL/SQLite is used.
try:
    import pymysql

    pymysql.install_as_MySQLdb()
except ImportError:  # pragma: no cover
    pass
