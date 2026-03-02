Place integration test images in this folder (or pass paths via environment variables):

- `page_with_table.jpg` (must contain at least one visible table)
- `page_without_table.jpg` (must not contain a table)

Optional environment variables for custom locations:

- `TABLE_IMAGE_PATH`
- `NO_TABLE_IMAGE_PATH`
- `TABLE_MODEL_PATH` (defaults to `utils/table_model.pt`)

Resource processor integration fixtures:

- `english_text.pdf`
- `legacy_sinhala.pdf`

Resource processor integration tests require `env.test` or `.env.test` in project root with:

- `TEST_DATABASE_URL` (must point to a separate test database)

Run only integration tests:

```powershell
python -m pytest -m integration -q
```
