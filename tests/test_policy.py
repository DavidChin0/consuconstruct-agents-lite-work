"""Tests de mcp_server/policy.py (sin DB). Correr: python -m unittest discover tests"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp_server"))
import policy  # noqa: E402


class SendTests(unittest.TestCase):
    def test_orquestador_manda_a_todos(self):
        for role in policy.ALL_ROLES - {policy.ORCHESTRATOR}:
            self.assertTrue(policy.can_send("claude_code", role), role)

    def test_managers_no_se_mandan_a_si_mismos(self):
        self.assertFalse(policy.can_send("claude_dane", "claude_dane"))
        self.assertTrue(policy.can_send("claude_dane", "claude_code"))
        self.assertTrue(policy.can_send("codex_hector", "claude_dane"))

    def test_rol_desconocido_o_destino_desconocido(self):
        self.assertFalse(policy.can_send("intruso", "claude_code"))
        self.assertFalse(policy.can_send("claude_dane", "nadie"))

    def test_reviewer_no_manda_a_workers(self):
        self.assertFalse(policy.can_send("claude_reviewer", "devops_bot"))


class AccessTests(unittest.TestCase):
    def test_solo_orquestador_escribe_pg(self):
        self.assertTrue(policy.can_write_pg("claude_code"))
        for role in ("claude_dane", "codex_hector", "claude_reviewer", "devops_bot"):
            self.assertFalse(policy.can_write_pg(role), role)

    def test_bandeja_propia(self):
        self.assertTrue(policy.can_read_inbox("claude_dane", "claude_dane"))
        self.assertFalse(policy.can_read_inbox("claude_dane", "codex_hector"))
        self.assertTrue(policy.can_read_inbox("claude_code", "codex_hector"))

    def test_veredicto_solo_reviewer(self):
        self.assertTrue(policy.can_give_verdict("claude_reviewer"))
        self.assertFalse(policy.can_give_verdict("claude_code"))
        self.assertFalse(policy.can_give_verdict("claude_dane"))


class SqlTests(unittest.TestCase):
    def test_select_simple_ok(self):
        self.assertIsNone(policy.select_is_safe("SELECT * FROM brain.goals", "claude_dane"))

    def test_cte_con_escritura_rechazado(self):
        sql = "WITH x AS (DELETE FROM brain.goals RETURNING id) SELECT * FROM x"
        self.assertIsNotNone(policy.select_is_safe(sql, "claude_code"))

    def test_multi_sentencia_rechazada(self):
        self.assertIsNotNone(policy.select_is_safe("SELECT 1; SELECT 2", "claude_code"))

    def test_tokens_solo_orquestador(self):
        sql = "SELECT * FROM brain.mcp_tokens"
        self.assertIsNotNone(policy.select_is_safe(sql, "claude_dane"))
        self.assertIsNone(policy.select_is_safe(sql, "claude_code"))


class TokenTests(unittest.TestCase):
    def test_hash_estable_y_no_reversible(self):
        h = policy.hash_token("abc")
        self.assertEqual(h, policy.hash_token("abc"))
        self.assertEqual(len(h), 64)
        self.assertNotIn("abc", h)

    def test_sha(self):
        self.assertTrue(policy.valid_sha("abc1234"))
        self.assertFalse(policy.valid_sha("zzz"))
        self.assertFalse(policy.valid_sha("; rm -rf"))


if __name__ == "__main__":
    unittest.main()
