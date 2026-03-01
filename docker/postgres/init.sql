-- Create test database alongside the main database
SELECT 'CREATE DATABASE passtheaux_test OWNER passtheaux'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'passtheaux_test')
\gexec
