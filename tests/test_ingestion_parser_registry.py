from __future__ import annotations

import unittest

from scripts.ingestion import build_log_corpus as corpus


class ParserRegistryTests(unittest.TestCase):
    def test_parse_raw_line_uses_registered_parser_chain(self) -> None:
        original = corpus.PARSER_REGISTRY["apache"]
        calls: list[str] = []

        def miss(raw_log: str) -> corpus.ParsedLine | None:
            calls.append("miss")
            return None

        def hit(raw_log: str) -> corpus.ParsedLine | None:
            calls.append("hit")
            return corpus.ParsedLine(message="parsed", parser_name="test_hit")

        try:
            corpus.PARSER_REGISTRY["apache"] = (miss, hit)

            parsed = corpus.parse_raw_line("apache", "raw log")
        finally:
            corpus.PARSER_REGISTRY["apache"] = original

        self.assertEqual(calls, ["miss", "hit"])
        self.assertEqual(parsed.message, "parsed")
        self.assertEqual(parsed.parser_name, "test_hit")

    def test_parse_raw_line_falls_back_to_generic_parser(self) -> None:
        original = corpus.PARSER_REGISTRY["apache"]

        try:
            corpus.PARSER_REGISTRY["apache"] = (lambda raw_log: None,)

            parsed = corpus.parse_raw_line("apache", "unstructured warning line")
        finally:
            corpus.PARSER_REGISTRY["apache"] = original

        self.assertEqual(parsed.message, "unstructured warning line")
        self.assertEqual(parsed.parser_name, "generic")
        self.assertEqual(parsed.level, "WARN")

    def test_dataset_parsers_identify_their_parser_name(self) -> None:
        cases = (
            (
                "apache",
                "[Thu Jun 09 06:07:04 2005] [error] Apache error message",
                "apache_bracket",
            ),
            (
                "openstack",
                "nova-api.log 2017-05-14 20:39:00.123 123 INFO nova.api Message",
                "openstack_standard",
            ),
            (
                "hdfs",
                "081109 203518 143 INFO dfs.DataNode$DataXceiver: Receiving block blk_1",
                "hdfs_standard",
            ),
        )

        for dataset, raw_log, parser_name in cases:
            with self.subTest(dataset=dataset):
                parsed = corpus.parse_raw_line(dataset, raw_log)

                self.assertEqual(parsed.parser_name, parser_name)


if __name__ == "__main__":
    unittest.main()
