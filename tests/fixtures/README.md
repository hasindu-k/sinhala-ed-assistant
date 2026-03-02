Place integration test images in this folder (or pass paths via environment variables):

- `page_with_table.jpg` (must contain at least one visible table)
- `page_without_table.jpg` (must not contain a table)

Optional environment variables for custom locations:

- `TABLE_IMAGE_PATH`
- `NO_TABLE_IMAGE_PATH`
- `TABLE_MODEL_PATH` (defaults to `utils/table_model.pt`)

Run only integration tests:

```powershell
python -m pytest -m integration -q
```
