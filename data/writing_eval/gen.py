import csv, json, sys
rows = list(csv.DictReader(open(sys.argv[1], encoding="utf-8")))
data = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
open(sys.argv[3], "w", encoding="utf-8").write(open(sys.argv[2], encoding="utf-8").read().replace("__DATA__", data))
