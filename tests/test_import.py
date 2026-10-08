import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from phrase_import import CONVERTERS, custom_collections, import_phrases, valid_name
from phrase_loader import collections, load_all, load_phrases

HEADER = '"id","level","topic","german","english","chinese","examples"\n'
BUILT_IN = HEADER + '"B1-0001","B1","Alltag","den Wecker stellen","to set the alarm","设闹钟","Satz. (Sentence.)"\n'


class ImportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        for level in ("B1", "B2", "C1"):
            (self.dir / f"phrases_{level}.csv").write_text(BUILT_IN.replace("B1", level),
                                                           encoding="utf-8-sig")

    def tearDown(self):
        self.tmp.cleanup()

    def source(self, text: str) -> Path:
        path = self.dir / "source.csv"
        path.write_text(text, encoding="utf-8")
        return path

    def test_import_creates_named_collection(self):
        src = self.source("topic,german,english,chinese,examples\n"
                          "Büro,eine E-Mail schreiben,to write an email,写邮件,"
                          "Ich schreibe eine E-Mail. (I write an email.)\n"
                          ",einen Termin machen,to make an appointment,,\n"
                          ",ohne Übersetzung,,,\n"
                          "Büro,eine E-Mail schreiben,duplicate,,\n")
        result = import_phrases(src, "Beruf", data_dir=self.dir)
        self.assertEqual((result.added, result.duplicates, result.invalid), (2, 1, [3]))
        self.assertEqual(collections(self.dir), ["B1", "B2", "C1", "Beruf"])
        self.assertEqual(custom_collections(self.dir), ["Beruf"])
        phrases = load_phrases("Beruf", self.dir)
        self.assertEqual([p.id for p in phrases], ["BERUF-0001", "BERUF-0002"])
        self.assertEqual(phrases[0].examples, [("Ich schreibe eine E-Mail.", "I write an email.")])
        self.assertEqual(phrases[1].topic, "Beruf")  # empty topic: the collection name
        self.assertEqual(phrases[1].examples, [])
        self.assertEqual(len(load_all(self.dir)), 5)

    def test_second_import_appends_and_skips_known_phrases(self):
        import_phrases(self.source("german;english\neins;one\n"), "Zahlen", data_dir=self.dir)
        result = import_phrases(self.source("german;english\nEINS;one\nzwei;two\n"), "Zahlen",
                                data_dir=self.dir)
        self.assertEqual((result.added, result.duplicates), (1, 1))
        self.assertEqual([p.id for p in load_phrases("Zahlen", self.dir)],
                         ["ZAHLEN-0001", "ZAHLEN-0002"])

    def test_missing_columns_and_bad_names(self):
        with self.assertRaises(ValueError):
            import_phrases(self.source("deutsch,englisch\na,b\n"), "Test", data_dir=self.dir)
        for name in ("B1", "all", "", "a/b", "mit Leerzeichen", "x" * 21):
            self.assertIsNotNone(valid_name(name), name)
        self.assertIsNone(valid_name("Mein_Kurs-2"))

    def test_converters_are_registered(self):
        self.assertIn("App CSV (.csv)", CONVERTERS)
        self.assertEqual(CONVERTERS["App CSV (.csv)"].extensions, (".csv",))


if __name__ == "__main__":
    unittest.main()
