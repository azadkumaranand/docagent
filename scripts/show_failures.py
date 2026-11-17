import json

baseline = json.load(open("results/baseline.json"))

for details in baseline["details"]:
  recipt_id = details["id"]
  for field_name, field_value in details["fields"].items():
    if field_value["exact"] == False:
      print(f"{recipt_id} {field_name}: {field_value['pred'], field_value['gold']}")