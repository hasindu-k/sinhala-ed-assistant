---
# **Setting Up PostgreSQL + pgvector on Ubuntu (for FastAPI Project)**

This guide explains how to install PostgreSQL 16, create a user and database, install **pgvector**, and enable it for your project.
---

## ## **📌 1. Install PostgreSQL 16**

Run the following commands in your terminal:

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

---

## ## **📌 2. Create PostgreSQL User**

Switch to PostgreSQL superuser:

```bash
sudo -i -u postgres
psql
```

Create a new user:

```sql
CREATE USER saman WITH PASSWORD 'replace-your-password';
```

Give the user permission to create databases:

```sql
ALTER USER saman CREATEDB;
```

Exit PostgreSQL:

```sql
\q
exit
```

---

## ## **📌 3. Create a New Database**

Log in as your new user:

```bash
psql -U saman -h localhost
```

Create the database:

```sql
CREATE DATABASE "SinhalaLearn";
```

---

## ## **📌 4. Install pgvector Extension (Required for Embeddings)**

Run these commands **on your Ubuntu system**, NOT inside PostgreSQL:

```bash
sudo apt update
sudo apt install postgresql-16-pgvector
```

Restart PostgreSQL:

```bash
sudo service postgresql restart
```

---

## ## **📌 5. Enable pgvector in Your Database**

Open PostgreSQL again:

```bash
sudo -i -u postgres
psql
```

Connect to your DB:

```sql
\c SinhalaLearn;
```

Enable the pgvector extension:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

You should see:

```
CREATE EXTENSION
```

---

## ## **📌 6. Your DATABASE_URL for FastAPI**

In your `.env` file:

```
DATABASE_URL=postgresql+psycopg2://saman:replace-your-password@localhost:5432/SinhalaLearn
```

---

## ## ✔️ Done!

You now have:

- PostgreSQL installed
- New user created
- New database created
- pgvector installed
- pgvector enabled for embeddings
- FastAPI `DATABASE_URL` configured

---
