# PostgreSQL with pgvector Setup

## 🐳 Docker Container Setup

### Option 1: Default Port (5432)

```bash
docker run -d \
  --name pgvector-db \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  ankane/pgvector
```

### Option 2: Custom Port (5433)

```bash
docker run -d \
  --name pgvector-db \
  -e POSTGRES_PASSWORD=password \
  -p 5433:5432 \
  ankane/pgvector
```

### Option 2: Windows Command Prompt with custom port

```cmd
docker run -d --name pgvector-db -e POSTGRES_PASSWORD=password -p 5433:5432 ankane/pgvector
```

---

## 🗄️ Database Configuration

Connect to the container and run the following SQL commands:

```sql
CREATE USER sinhala_learn_user WITH PASSWORD 'sinlearn';
CREATE DATABASE "SinhalaLearn" OWNER sinhala_learn_user;
GRANT ALL PRIVILEGES ON DATABASE "SinhalaLearn" TO sinhala_learn_user;
\c "SinhalaLearn"
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## 🔗 Accessing the Database

### As Admin (postgres user)

```bash
docker exec -it pgvector-db psql -U postgres
```

### As Application User

```bash
docker exec -it pgvector-db psql -U sinhala_learn_user -d "SinhalaLearn"
```

---

## 📝 Connection String

```
DATABASE_URL=postgresql://sinhala_learn_user:sinlearn@localhost:5432/SinhalaLearn
```

**Note:** Update the port number if using Option 2 (5433)
