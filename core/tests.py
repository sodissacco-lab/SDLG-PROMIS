from types import SimpleNamespace

from django.test import TestCase

from .reg_config import cell


class CellTests(TestCase):
    def test_calls_terminal_method_without_calling_intermediate_manager(self):
        class RelatedManager:
            def __call__(self, *, manager):
                raise AssertionError("Intermediate related manager was called", manager)

            def count(self):
                return 0

        obj = SimpleNamespace(ponds=RelatedManager())

        self.assertEqual(cell(obj, "ponds.count"), 0)

    def test_calls_terminal_display_method(self):
        obj = SimpleNamespace(get_sex_display=lambda: "Female")

        self.assertEqual(cell(obj, "get_sex_display"), "Female")
