MODULE_CODE = """
#include <boost/python.hpp>

namespace
{
  char const *greet()
  {
    return "hello world";
  }
}

BOOST_PYTHON_MODULE(module)
{
  boost::python::def("greet", &greet);
}
"""

from codepy.toolchain import guess_toolchain
toolchain = guess_toolchain()

from codepy.libraries import add_boost_python
add_boost_python(toolchain)

from codepy.jit import extension_from_string
cmod = extension_from_string(toolchain, "module", MODULE_CODE)

print cmod.greet()


