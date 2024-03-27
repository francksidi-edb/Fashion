CREATE OR REPLACE FUNCTION py_transformers_path()
RETURNS text AS $$
import transformers
# Return the file path of the imported transformers package
return transformers.__file__
$$ LANGUAGE plpython3u;

CREATE OR REPLACE FUNCTION py_version_location()
RETURNS text AS $$
import sys
return f"Python Version: {sys.version}\nExecutable Location: {sys.executable}"
$$ LANGUAGE plpython3u;

CREATE OR REPLACE FUNCTION py_list_packages()
RETURNS text AS $$
import pkg_resources
return "\n".join([f"{i.key}=={i.version}" for i in pkg_resources.working_set])
$$ LANGUAGE plpython3u;

CREATE OR REPLACE FUNCTION py_add_path()
RETURNS text AS $$
import sys
# Path to the site-packages directory
new_path = '/Users/ton.machielsen/.local/lib/python3.11/site-packages'
if new_path not in sys.path:
    sys.path.append(new_path)
return str(sys.path)
$$ LANGUAGE plpython3u;
