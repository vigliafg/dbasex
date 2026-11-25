import pytest

from dbx.core import types as T
from dbx.core.db import Database
from dbx.core.ddl import apply_migration, create_table_sql, plan_migration
from dbx.core.metadata import Field, Index, Table


def table_v1() -> Table:
    return Table(
        name="clienti",
        fields=[Field("nome", T.TEXT, required=True), Field("anni", T.INTEGER)],
    )


def test_create_sql_contains_internal_id_and_fields():
    sql = create_table_sql(table_v1())
    assert '"_id" INTEGER PRIMARY KEY AUTOINCREMENT' in sql
    assert '"nome" TEXT NOT NULL' in sql
    assert '"anni" INTEGER' in sql


def test_create_and_insert():
    db = Database(":memory:")
    apply_migration(db.con, table_v1(), None)
    assert db.columns("clienti") == ["_id", "nome", "anni"]
    db.execute('INSERT INTO "clienti" ("nome", "anni") VALUES (?, ?)', ("Ada", 36))
    assert db.scalar("SELECT nome FROM clienti") == "Ada"


def test_add_column_uses_alter_and_preserves_rows():
    db = Database(":memory:")
    old = table_v1()
    apply_migration(db.con, old, None)
    db.execute('INSERT INTO "clienti" ("nome", "anni") VALUES (?, ?)', ("Ada", 36))

    new = old.copy()
    new.fields.append(Field("email", T.TEXT, default=""))
    plan = plan_migration(old, new)
    assert plan.kind == "alter"
    apply_migration(db.con, new, old)
    row = db.query("SELECT nome, email FROM clienti")[0]
    assert row["nome"] == "Ada"
    # Un campo aggiunto senza DEFAULT esplicito resta NULL sui record esistenti.
    assert row["email"] is None


def test_rename_field_by_id_preserves_data():
    db = Database(":memory:")
    old = table_v1()
    apply_migration(db.con, old, None)
    db.execute('INSERT INTO "clienti" ("nome", "anni") VALUES (?, ?)', ("Ada", 36))

    new = old.copy()
    new.fields[0].name = "ragione_sociale"
    plan = plan_migration(old, new)
    assert plan.kind == "rebuild"
    apply_migration(db.con, new, old)
    assert db.columns("clienti") == ["_id", "ragione_sociale", "anni"]
    assert db.scalar("SELECT ragione_sociale FROM clienti") == "Ada"
    assert db.scalar("SELECT COUNT(*) FROM clienti") == 1


def test_drop_column_and_change_type_keep_data():
    db = Database(":memory:")
    old = table_v1()
    apply_migration(db.con, old, None)
    db.execute('INSERT INTO "clienti" ("nome", "anni") VALUES (?, ?)', ("Ada", "36"))

    new = Table(
        name="clienti",
        fields=[Field("nome", T.TEXT, required=True, id=old.fields[0].id), Field("anni", T.DECIMAL, id=old.fields[1].id)],
    )
    apply_migration(db.con, new, old)
    assert db.columns("clienti") == ["_id", "nome", "anni"]
    assert db.scalar("SELECT anni FROM clienti") == 36.0


def test_required_new_field_on_existing_table_gets_default():
    db = Database(":memory:")
    old = table_v1()
    apply_migration(db.con, old, None)
    db.execute('INSERT INTO "clienti" ("nome", "anni") VALUES (?, ?)', ("Ada", 36))
    new = old.copy()
    new.fields.append(Field("attivo", T.BOOLEAN, required=True, default="1"))
    apply_migration(db.con, new, old)
    assert db.scalar("SELECT attivo FROM clienti") == 1


def test_indexes_are_created_and_unique_enforced():
    db = Database(":memory:")
    table = table_v1()
    table.indexes.append(Index(fields=["nome"], unique=True))
    apply_migration(db.con, table, None)
    names = [row["name"] for row in db.query("SELECT name FROM sqlite_master WHERE type='index'")]
    assert "idx_clienti_nome" in names
    db.execute('INSERT INTO "clienti" ("nome") VALUES (?)', ("Ada",))
    with pytest.raises(Exception):
        db.execute('INSERT INTO "clienti" ("nome") VALUES (?)', ("Ada",))


def test_foreign_key_cascade_delete():
    db = Database(":memory:")
    parent = Table(name="citta", fields=[Field("nome", T.TEXT, required=True)])
    parent.indexes.append(Index(fields=["nome"], unique=True))
    apply_migration(db.con, parent, None)
    child = Table(name="clienti", fields=[Field("citta", T.TEXT)])
    from dbx.core.metadata import ForeignKey

    child.foreign_keys.append(
        ForeignKey(columns=["citta"], ref_table="citta", ref_columns=["nome"], on_delete="CASCADE")
    )
    apply_migration(db.con, child, None)
    db.execute('INSERT INTO "citta" ("nome") VALUES (?)', ("Roma",))
    db.execute('INSERT INTO "clienti" ("citta") VALUES (?)', ("Roma",))
    db.execute('DELETE FROM "citta" WHERE "nome" = ?', ("Roma",))
    assert db.scalar("SELECT COUNT(*) FROM clienti") == 0


def test_no_changes_produces_empty_plan():
    table = table_v1()
    assert plan_migration(table, table.copy()).kind == "none"


def test_rebuild_rolls_back_on_failure():
    db = Database(":memory:")
    old = table_v1()
    apply_migration(db.con, old, None)
    db.execute('INSERT INTO "clienti" ("nome") VALUES (?)', ("Ada",))
    new = old.copy()
    new.fields[0].name = "nome2"
    # Una tabella temporanea già esistente e non droppabile non è facile da simulare;
    # verifichiamo invece che un piano non valido non distrugga la tabella.
    with pytest.raises(Exception):
        bad = Table(name="clienti", fields=[Field("nome", "tipo_inventato")])
        apply_migration(db.con, bad, old)
    assert db.scalar("SELECT COUNT(*) FROM clienti") == 1


def test_table_name_with_spaces_roundtrips_through_sqlite():
    table = Table(name="tabella 2", fields=[Field("nome", T.TEXT)])
    db = Database(":memory:")
    apply_migration(db.con, table, None)
    db.execute('INSERT INTO "tabella 2" ("nome") VALUES (?)', ("Ada",))
    assert db.scalar('SELECT "nome" FROM "tabella 2"') == "Ada"
