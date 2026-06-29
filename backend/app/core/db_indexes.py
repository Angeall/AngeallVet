"""Performance index DDL applied to every database (central + each tenant).

Defined once and applied both at startup (``_ensure_schema`` in app.main) and via
migration 009. PostgreSQL-only: trigram search needs the pg_trgm extension, and
GIN trigram indexes are Postgres-specific. On other engines (SQLite/tests) these
are skipped — correctness never depends on an index.

Rationale (see the index review): the schema already has comprehensive single
-column indexes, so these target the two real gaps:
  * `ILIKE '%term%'` global search → GIN trigram indexes (btree can't help).
  * filter + ORDER BY hot paths → composite indexes.
"""

PG_TRGM_EXTENSION = "CREATE EXTENSION IF NOT EXISTS pg_trgm"

# (table_name, CREATE INDEX statement). Each is created only if the table exists.
PERF_INDEXES = [
    # --- Trigram search (global search bar / list filters) ---
    ("clients", "CREATE INDEX IF NOT EXISTS ix_clients_last_name_trgm ON clients USING gin (last_name gin_trgm_ops)"),
    ("clients", "CREATE INDEX IF NOT EXISTS ix_clients_first_name_trgm ON clients USING gin (first_name gin_trgm_ops)"),
    ("animals", "CREATE INDEX IF NOT EXISTS ix_animals_name_trgm ON animals USING gin (name gin_trgm_ops)"),
    ("products", "CREATE INDEX IF NOT EXISTS ix_products_name_trgm ON products USING gin (name gin_trgm_ops)"),
    # --- Composite (filter + ORDER BY in one index scan) ---
    # unread-count is polled every 15s per session
    ("notifications", "CREATE INDEX IF NOT EXISTS ix_notifications_user_id_is_read ON notifications (user_id, is_read)"),
    # animal medical history
    ("medical_records", "CREATE INDEX IF NOT EXISTS ix_medical_records_animal_created ON medical_records (animal_id, created_at DESC)"),
    # weight curve
    ("weight_records", "CREATE INDEX IF NOT EXISTS ix_weight_records_animal_recorded ON weight_records (animal_id, recorded_at DESC)"),
    # agenda filtered by vet
    ("appointments", "CREATE INDEX IF NOT EXISTS ix_appointments_vet_start ON appointments (veterinarian_id, start_time)"),
    # controlled-substances register filtered by product
    ("controlled_substance_entries", "CREATE INDEX IF NOT EXISTS ix_cse_product_date ON controlled_substance_entries (product_id, date DESC)"),
]
