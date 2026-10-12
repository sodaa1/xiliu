"""Export pytest JUnit evidence without treating fixture runs as live-model quality."""

import json
import xml.etree.ElementTree as ET
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    source = root / "logs/graph-v2/multi50-evidence.xml"
    cases = []
    for test in ET.parse(source).iter("testcase"):
        properties = {
            item.attrib["name"]: item.attrib.get("value", "")
            for item in test.findall("./properties/property")
        }
        if "query" not in properties:
            continue
        for key in (
            "node_path",
            "execution_result",
            "tool_receipts",
            "tool_events",
            "database_state",
        ):
            if key in properties:
                properties[key] = json.loads(properties[key])
        cases.append(
            {
                "name": test.attrib["name"],
                "passed": test.find("failure") is None and test.find("error") is None,
                **properties,
            }
        )
    result = {
        "methodology": (
            "Fixture model and search transport; real Runtime, graph, gateway, policy, "
            "SQLite and filesystem. Not live-model semantic accuracy."
        ),
        "cases": len(cases),
        "passed": sum(case["passed"] for case in cases),
        "results": cases,
    }
    target = root / "docs/architecture/graph-v2/multistep-results.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cases": result["cases"], "passed": result["passed"]}))


if __name__ == "__main__":
    main()
