# We test with this sample that the method signature is correctly translated.
@abstract
class Abstract:
    @require(lambda x: x > 0)
    def some_func(self, x: int) -> bool:
        pass
