import cgen as c
import cgen.preprocessor as pp

func = c.FunctionBody(
    c.FunctionDeclaration(c.Const(c.Pointer(c.Value("char", "greet"))), []),
    c.Block([
        pp.If('(my_condition == true)',
              [
                  c.Statement('return "hello world"')
              ],
              [
                  c.Statement('return "bye world"')
              ]
              )]
    )
)

print(func)
