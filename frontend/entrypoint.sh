#!/bin/sh

JS_PATH=/usr/share/nginx/html/environ.json
echo "dump CMS_* environ variables to $JS_PATH"

python3 -c 'import json; import os; import re; print(json.dumps({re.sub(r"^CMS_", "", k): v for k, v in os.environ.items() if k.startswith("CMS_")}, indent=4))' > $JS_PATH

cat $JS_PATH
echo "-----"

exec "$@"
