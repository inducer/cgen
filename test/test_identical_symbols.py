def make_greet_mod(greeting):
    from codepy.cgen import FunctionBody, FunctionDeclaration, Block, \
            Const, Pointer, Value, Statement
    from codepy.bpl import BoostPythonModule

    mod = BoostPythonModule()

    mod.add_function(
            FunctionBody(
                FunctionDeclaration(Const(Pointer(Value("char", "greet"))), []),
                Block([Statement('return "%s"' % greeting)])
                ))

    from codepy.toolchain import guess_toolchain
    return mod.compile(guess_toolchain(), wait_on_error=True)

def test_identical_symbols():
    us = make_greet_mod("Hi there")
    aussie = make_greet_mod("G'day")

    assert us.greet() != aussie.greet()
    print us.greet(), aussie.greet()

if __name__ == '__main__':
    test_identical_symbols()
