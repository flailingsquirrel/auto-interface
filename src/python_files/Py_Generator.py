#!/usr/bin/env python

__author__="Brian Hone"

'''
Code Generator

Generates Python Reader/Writer classes for AutoInterface formatted data

Actual reading/writing is provided via io_support.py
'''

import json, string, pprint, sys, os
import shutil
from AutoInterface import AutoGenerator
from Templates import py_class_template

T="    "


def create_py_class_def( basetypes, structs, struct_name ):
    struct_def = structs[ struct_name ]
    ret = py_class_template.format( struct_name )

    # set defaults
    for f in struct_def['FIELDS']:
        if basetypes.has_key( f['TYPE'] ):
            basetype = basetypes[ f['TYPE'] ]
            if f.has_key('DEFAULT_VALUE'):
                def_val = f['DEFAULT_VALUE']
            else:
                def_val = basetype['DEFAULT_VALUE']

            if basetype.has_key( 'COMPLEX' ):
                # TODO: handle the case when this is set wrong by the user
                ret = ret + T + T + "self.{0} = {1} + {2}j;\n".format(f['NAME'], def_val[0],def_val[1])
            else:
                ret = ret + T + T + "self.{0} = {1};\n".format(f['NAME'], def_val)
        elif f['TYPE'] == 'STRUCT':
            ret = ret + T + T + 'self.{0} = {1}()\n'.format(f['NAME'], f['STRUCT_TYPE'])
            ret = ret + T + T + 'self.{0}.set_defaults();\n'.format(f['NAME'])
        elif f['TYPE'] == 'VECTOR':
            # If a default vaulue, try to set it
            if f.has_key( 'DEFAULT_VALUE' ):
                if basetypes.has_key(f['CONTAINED_TYPE']):
                    basetype = basetypes[f['CONTAINED_TYPE']]
                    def_val = f['DEFAULT_VALUE']
                    # COMPLEX
                    if basetype.has_key('COMPLEX'):
                        def_str = ''
                        for idx in range(0,len(def_val),2):
                            def_str = def_str + '{0} + {1}j,'.format(def_val[idx],def_val[idx+1])
                    # Not COMPLEX
                    else:
                        def_str = ''
                        for idx in range(len(def_val)):
                            def_str = def_str + '{0},'.format(def_val[idx])
                    # remove trailing whitespace and comma
                    def_str = def_str.rstrip()
                    if def_str[-1] == ',':  
                        def_str = def_str[:-1]
                    # set the value
                    ret = ret + T + T + 'self.{0} = [ {1} ]\n'.format(f['NAME'],def_str)
                elif f['CONTAINED_TYPE'] == 'STRUCT':
                    ret = ret + T + T + 'self.{0} = []\n'.format( f['NAME'] )
            # No default value, just set the element
            else:
                ret = ret + T + T + 'self.{0} = []\n'.format(f['NAME'])
                # vector of struct default setting not suppported
    ret = ret + T + "# end set_defaults\n"

    # read binary
    ret = ret + T + "def read_binary( self, r_stream ):\n"
    for f in struct_def['FIELDS']:
        if basetypes.has_key( f['TYPE'] ):
            ret = ret + T + T + 'self.{0} = io.read_{1}( r_stream )\n'.format(f['NAME'], f['TYPE'])
        elif f['TYPE'] == 'STRUCT':
            ret = ret + T + T + 'self.{0}.read_binary( r_stream );\n'.format( f['NAME'] )
        elif f['TYPE'] == 'VECTOR':
            ret = ret + T + T + "self.{0} = []\n".format( f['NAME'] )
            # TODO - this needs to be uint32_t
            ret = ret + T + T + "num_elems = io.read_INT_32( r_stream )\n"
            if basetypes.has_key( f['CONTAINED_TYPE'] ):
                ret = ret + T + T + 'self.{0} = io.read_{1}( r_stream, nElements=num_elems )\n'.format(f['NAME'], f['CONTAINED_TYPE'])
            elif f['CONTAINED_TYPE'] == 'STRUCT':
                ret = ret + T + T + 'for idx in range( num_elems ):\n'
                ret = ret + T + T + T + 'tmp = {0}()\n'.format( f['STRUCT_TYPE'] )
                ret = ret + T + T + T + 'tmp.read_binary(r_stream)\n'
                ret = ret + T + T + T + 'self.{0}.append( tmp )\n'.format( f['NAME'] )
    ret = ret + T + "# end read_binary\n\n"


    # write binary
    ret = ret + T + "def write_binary( self, r_stream ):\n"
    for f in struct_def['FIELDS']:
        if basetypes.has_key( f['TYPE'] ):
            ret = ret + T + T + 'io.write_{0}( r_stream, self.{1} )\n'.format(f['TYPE'], f['NAME'])
        elif f['TYPE'] == 'STRUCT':
            ret = ret + T + T + 'self.{0}.write_binary(r_stream);\n'.format(f['NAME'])
        elif f['TYPE'] == 'VECTOR':
            # TODO - this needs to be uint32_t
            ret = ret + T + T + "num_elems = len( self.{0} )\n".format(f['NAME'])
            ret = ret + T + T + "io.write_INT_32( r_stream, num_elems )\n"
            if basetypes.has_key( f['CONTAINED_TYPE'] ):
                ret = ret + T + T + 'io.write_{0}( r_stream, self.{1}, nElements=num_elems )\n'.format(f['CONTAINED_TYPE'],f['NAME'])
            elif f['CONTAINED_TYPE'] == 'STRUCT':
                ret = ret + T + T + 'for idx in range( num_elems ):\n'
                ret = ret + T + T + T + 'self.{0}[idx].write_binary(r_stream)\n'.format( f['NAME'] )
    ret = ret + T + "# end write_binary\n\n"
    ret = ret + "# end class {0}\n\n".format(  struct_name )


    return ret
    # end create_class_def


def generate_py( py_dir, basetypes, structs ):
    if not os.path.exists( py_dir ):
        os.mkdir( py_dir )

    python_repo_dir = os.path.dirname(os.path.realpath(__file__))
    shutil.copy( python_repo_dir + os.sep + 'io_support.py', 
                 py_dir + os.sep + 'io_support.py' )


    fOut = open( py_dir + os.sep + "interface.py", "w" )
    fOut.write( "#!/usr/bin/env python\n" )
    fOut.write( "import string\n" )
    fOut.write( "import pprint\n" )
    fOut.write( "import struct\n" )
    fOut.write( "import io_support as io\n" )

    for struct_name, struct_def in structs.items():
        ret = create_py_class_def( basetypes, structs, struct_name )
        fOut.write( ret )
        fOut.write( "\n\n" )
    fOut.close()
# end create_py_files


if __name__ == "__main__":
    import argparse 
    parser = argparse.ArgumentParser( 'AutoInterface Python Generator' )
    parser.add_argument( 'json_basetypes_file' )
    parser.add_argument( 'json_structures_file' )
    parser.add_argument( 'output_directory' )
    args = parser.parse_args()

    json_basetypes = args.json_basetypes_file
    json_file = args.json_structures_file
    out_dir = args.output_directory
    A = AutoGenerator( json_basetypes, json_file, out_dir  )
    basetypes = A.basetypes
    structs   = A.structs
    generate_py( out_dir, basetypes, structs )