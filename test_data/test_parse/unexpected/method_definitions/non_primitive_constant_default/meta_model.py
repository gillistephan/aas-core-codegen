class Something:
    def do_something(self, x: int = b"xyz") -> None:
        pass


class Reference:
    pass


__book_url__ = "dummy"
__book_version__ = "dummy"
associate_ref_with(Reference)
