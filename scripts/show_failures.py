import json

baseline = json.load(open("results/baseline.json"))

failure_count = 0
field_failure_count = {}

for details in baseline["details"]:
  recipt_id = details["id"]

  for field_name, field_value in details["fields"].items():
    
    if field_value["exact"] == False:
      failure_count += 1
      field_failure_count[field_name] = field_failure_count.get(field_name, 0) + 1
      print(f"{recipt_id} {field_name}: {field_value['pred'], field_value['gold']}")

print(f"Total failures: {failure_count}")
print(f"Field failures: {field_failure_count}")